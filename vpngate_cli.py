#!/usr/bin/env python3
import requests
import base64
import subprocess
import sys
import argparse
import os
import re
import time

API_URL = "https://www.vpngate.net/api/iphone/"
CONNECTION_NAME = "vpngate-active"
PID_FILE = "/tmp/vpngate-cli.pid"

def get_servers():
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        lines = response.text.splitlines()
        if len(lines) < 2:
            return []
        
        header = lines[1][1:].split(",")
        servers = []
        for line in lines[2:]:
            if line.startswith("*") or line.startswith("#") or not line.strip():
                continue
            parts = line.split(",")
            if len(parts) < 15:
                continue
            server = dict(zip(header, parts))
            
            try:
                config_data = base64.b64decode(server['OpenVPN_ConfigData_Base64']).decode('utf-8', errors='ignore')
                # Improved detection: A config can have both, but usually specifies a default
                # We check for explicit 'proto tcp' or if 'proto udp' is NOT present
                server['has_udp'] = "proto udp" in config_data.lower()
                server['has_tcp'] = "proto tcp" in config_data.lower() or "proto udp" not in config_data.lower()
                server['config_text'] = config_data
                servers.append(server)
            except:
                continue
        return servers
    except Exception as e:
        print(f"Error fetching servers: {e}")
        return []

def is_active():
    res = subprocess.run(["nmcli", "-t", "-f", "NAME,STATE", "connection", "show", "--active"], capture_output=True, text=True)
    return CONNECTION_NAME in res.stdout

def get_stats():
    """Returns (up_speed, down_speed, ping, loss) or None if not active"""
    if not is_active():
        return None
    
    # Get device name from nmcli
    res = subprocess.run(["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"], capture_output=True, text=True)
    device = None
    for line in res.stdout.splitlines():
        if line.startswith(CONNECTION_NAME):
            device = line.split(":")[1]
            break
    
    if not device:
        return None

    # Get speeds from /proc/net/dev (bytes)
    def get_bytes():
        with open("/proc/net/dev", "r") as f:
            for line in f:
                if device in line:
                    parts = line.split()
                    return int(parts[1]), int(parts[9]) # rx, tx
        return 0, 0

    b1_rx, b1_tx = get_bytes()
    time.sleep(1)
    b2_rx, b2_tx = get_bytes()
    
    down_speed = (b2_rx - b1_rx) / 1024 # KB/s
    up_speed = (b2_tx - b1_tx) / 1024 # KB/s

    # Get ping/loss via ping command (3 packets)
    ping_res = subprocess.run(["ping", "-c", "3", "-W", "2", "8.8.8.8"], capture_output=True, text=True)
    ping_val = "N/A"
    loss_val = "100%"
    
    if ping_res.returncode == 0:
        # Extract loss
        loss_match = re.search(r"(\d+)% packet loss", ping_res.stdout)
        if loss_match:
            loss_val = loss_match.group(1) + "%"
        
        # Extract avg ping
        avg_match = re.search(r"avg/max/mdev = [\d\.]+/([\d\.]+)/", ping_res.stdout)
        if avg_match:
            ping_val = avg_match.group(1) + " ms"

    return up_speed, down_speed, ping_val, loss_val

def connect_vpn(server, force_proto=None):
    if is_active():
        return False, "Error: A VPN connection is already active. Stop it first."

    config_data = server['config_text']
    
    # If the user explicitly requested TCP/UDP, we try to force it in the config
    if force_proto == "tcp":
        config_data = re.sub(r"proto udp", "proto tcp", config_data, flags=re.IGNORECASE)
    elif force_proto == "udp":
        config_data = re.sub(r"proto tcp", "proto udp", config_data, flags=re.IGNORECASE)

    temp_ovpn = "/tmp/vpngate-active.ovpn"
    with open(temp_ovpn, 'w') as f:
        f.write(config_data)
    
    subprocess.run(["nmcli", "connection", "delete", CONNECTION_NAME], capture_output=True)
    
    import_res = subprocess.run(["nmcli", "connection", "import", "type", "openvpn", "file", temp_ovpn], capture_output=True, text=True)
    
    if import_res.returncode != 0:
        return False, f"Failed to import: {import_res.stderr}"

    remote_match = re.search(r"^remote\s+([\d\.]+)\s+(\d+)", config_data, re.MULTILINE)
    remote_ip = remote_match.group(1) if remote_match else server['IP']
    remote_port = remote_match.group(2) if remote_match else "443"
    
    is_udp = "proto udp" in config_data.lower()
    proto_str = "no" if is_udp else "yes"

    subprocess.run(["nmcli", "connection", "modify", CONNECTION_NAME, 
                    "vpn.user-name", "vpn",
                    "vpn.secrets", "password=vpn",
                    "+vpn.data", f"auth=SHA1, cipher=AES-128-CBC, data-ciphers=AES-256-GCM:AES-128-GCM:AES-128-CBC, data-ciphers-fallback=AES-128-CBC, connection-type=password, remote={remote_ip}, port={remote_port}, proto-tcp={proto_str}"], capture_output=True)

    print(f"Activating {('UDP' if is_udp else 'TCP')} connection (10s timeout)...")
    try:
        up_res = subprocess.run(["timeout", "10s", "nmcli", "connection", "up", CONNECTION_NAME], capture_output=True, text=True)
        
        if up_res.returncode == 0:
            with open(PID_FILE, "w") as f:
                f.write(str(os.getpid()))
            return True, "Successfully connected!"
        elif up_res.returncode == 124:
            subprocess.run(["nmcli", "connection", "delete", CONNECTION_NAME], capture_output=True)
            return False, "Connection timed out (>10s)."
        else:
            subprocess.run(["nmcli", "connection", "delete", CONNECTION_NAME], capture_output=True)
            return False, f"Connection failed: {up_res.stderr}"
    except Exception as e:
        subprocess.run(["nmcli", "connection", "delete", CONNECTION_NAME], capture_output=True)
        return False, str(e)
    finally:
        if os.path.exists(temp_ovpn):
            os.remove(temp_ovpn)

def disconnect_vpn():
    if not is_active():
        subprocess.run(["nmcli", "connection", "delete", CONNECTION_NAME], capture_output=True)
        return False, "No active VPN connection found."

    subprocess.run(["nmcli", "connection", "down", CONNECTION_NAME], capture_output=True)
    subprocess.run(["nmcli", "connection", "delete", CONNECTION_NAME], capture_output=True)
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    return True, "VPN disconnected."

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VPN Gate CLI Connector")
    parser.add_argument("--status", action="store_true", help="Check if VPN is active")
    parser.add_argument("--stop", action="store_true", help="Disconnect and delete the VPN")
    parser.add_argument("--tcp", action="store_true", help="Show TCP servers only")
    parser.add_argument("--all", action="store_true", help="Show all servers")
    args = parser.parse_args()

    if args.stop:
        success, msg = disconnect_vpn()
        print(msg)
        sys.exit(0 if success else 1)
    
    if args.status:
        active = is_active()
        print(f"Status: {CONNECTION_NAME} is {'ACTIVE' if active else 'NOT active'}")
        if active:
            stats = get_stats()
            if stats:
                up, down, ping, loss = stats
                print(f"Down: {down:.1f} KB/s | Up: {up:.1f} KB/s")
                print(f"Ping: {ping} | Loss: {loss}")
        sys.exit(0 if active else 1)

    proto_pref = "all" if args.all else ("tcp" if args.tcp else "udp")
    print(f"Fetching servers (Preference: {proto_pref.upper()})...")
    servers = get_servers()
    
    filtered = []
    for s in servers:
        if proto_pref == "udp" and s['has_udp']: filtered.append(s)
        elif proto_pref == "tcp" and s['has_tcp']: filtered.append(s)
        elif proto_pref == "all": filtered.append(s)
    
    filtered.sort(key=lambda x: int(x['Score']), reverse=True)
    
    print(f"{'Idx':<4} | {'Proto':<5} | {'Country':<15} | {'IP':<15} | {'Score':<10} | {'Ping':<5}")
    print("-" * 75)
    for i, s in enumerate(filtered[:20]):
        # Determine what to display based on pref
        p = "UDP" if (proto_pref != "tcp" and s['has_udp']) else "TCP"
        print(f"{i:<4} | {p:<5} | {s['CountryShort']:<15} | {s['IP']:<15} | {s['Score']:<10} | {s['Ping']:<5}")

    try:
        choice = input("\nEnter Index to connect (or 'q' to quit): ")
        if choice.lower() == 'q': sys.exit(0)
        idx = int(choice)
        if 0 <= idx < len(filtered):
            # Pass pref to connect_vpn to force the proto in the config file
            success, msg = connect_vpn(filtered[idx], force_proto=("tcp" if proto_pref == "tcp" else None))
            print(msg)
        else:
            print("Invalid index.")
    except (ValueError, KeyboardInterrupt):
        print("\nExiting.")
