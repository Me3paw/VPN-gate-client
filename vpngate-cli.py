#!/usr/bin/env python3
import requests
import base64
import subprocess
import sys
import argparse
import os
import re

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
            
            # Extract config to check available protocols
            config_data = base64.b64decode(server['OpenVPN_ConfigData_Base64']).decode('utf-8', errors='ignore')
            server['is_udp'] = "proto udp" in config_data.lower()
            server['config_text'] = config_data
            
            servers.append(server)
        return servers
    except Exception as e:
        print(f"Error fetching servers: {e}")
        return []

def list_servers(servers, proto_pref="udp", limit=20):
    print(f"{'Idx':<4} | {'Proto':<5} | {'Country':<15} | {'IP':<15} | {'Score':<10} | {'Ping':<5}")
    print("-" * 75)
    
    filtered = []
    for s in servers:
        if proto_pref == "udp" and s['is_udp']:
            filtered.append(s)
        elif proto_pref == "tcp" and not s['is_udp']:
            filtered.append(s)
        elif proto_pref == "all":
            filtered.append(s)
            
    filtered.sort(key=lambda x: int(x['Score']), reverse=True)
    
    for i, s in enumerate(filtered[:limit]):
        proto = "UDP" if s['is_udp'] else "TCP"
        print(f"{i:<4} | {proto:<5} | {s['CountryShort']:<15} | {s['IP']:<15} | {s['Score']:<10} | {s['Ping']:<5}")
    return filtered

def connect_vpn(server):
    config_data = server['config_text']
    temp_ovpn = "/tmp/vpngate-active.ovpn"
    
    with open(temp_ovpn, 'w') as f:
        f.write(config_data)
    
    # Clean cleanup
    subprocess.run(["nmcli", "connection", "delete", CONNECTION_NAME], capture_output=True)
    
    proto_label = "UDP" if server['is_udp'] else "TCP"
    print(f"Importing {proto_label} connection to {server['IP']} ({server['CountryLong']})...")
    
    import_res = subprocess.run(["nmcli", "connection", "import", "type", "openvpn", "file", temp_ovpn], capture_output=True, text=True)
    
    if import_res.returncode != 0:
        print(f"Failed to import: {import_res.stderr}")
        return

    # Detection for manual override
    remote_match = re.search(r"^remote\s+([\d\.]+)\s+(\d+)", config_data, re.MULTILINE)
    remote_ip = remote_match.group(1) if remote_match else server['IP']
    remote_port = remote_match.group(2) if remote_match else "443"

    print(f"Configuring legacy support and secrets...")
    subprocess.run(["nmcli", "connection", "modify", CONNECTION_NAME, 
                    "vpn.user-name", "vpn",
                    "vpn.secrets", "password=vpn",
                    "+vpn.data", f"auth=SHA1, cipher=AES-128-CBC, data-ciphers=AES-256-GCM:AES-128-GCM:AES-128-CBC, data-ciphers-fallback=AES-128-CBC, connection-type=password, remote={remote_ip}, port={remote_port}"], capture_output=True)

    print("Activating connection (5s timeout)...")
    try:
        up_res = subprocess.run(["timeout", "5s", "nmcli", "connection", "up", CONNECTION_NAME], capture_output=True, text=True)
        
        if up_res.returncode == 0:
            print("Successfully connected!")
            with open(PID_FILE, "w") as f:
                f.write(str(os.getpid()))
        elif up_res.returncode == 124:
            print("Connection timed out (>5s). Server might be slow or blocked.")
            subprocess.run(["nmcli", "connection", "delete", CONNECTION_NAME], capture_output=True)
        else:
            print(f"Connection failed: {up_res.stderr}")
            subprocess.run(["nmcli", "connection", "delete", CONNECTION_NAME], capture_output=True)
    except Exception as e:
        print(f"An error occurred: {e}")
        subprocess.run(["nmcli", "connection", "delete", CONNECTION_NAME], capture_output=True)

    if os.path.exists(temp_ovpn):
        os.remove(temp_ovpn)

def disconnect_vpn():
    print("Disconnecting and deleting VPN connection...")
    subprocess.run(["nmcli", "connection", "down", CONNECTION_NAME], capture_output=True)
    res = subprocess.run(["nmcli", "connection", "delete", CONNECTION_NAME], capture_output=True, text=True)
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    if res.returncode == 0:
        print("VPN removed successfully.")
    else:
        print("No active vpngate connection found to delete.")

def status_vpn():
    res = subprocess.run(["nmcli", "-t", "-f", "NAME,STATE", "connection", "show", "--active"], capture_output=True, text=True)
    is_active = CONNECTION_NAME in res.stdout
    print(f"Status: {CONNECTION_NAME} is {'ACTIVE' if is_active else 'NOT active'}")
    if os.path.exists(PID_FILE):
        print(f"Script state: Active (PID file exists)")
    else:
        print(f"Script state: Inactive")
    return is_active

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VPN Gate CLI Connector")
    parser.add_argument("--status", action="store_true", help="Check if VPN is active")
    parser.add_argument("--stop", action="store_true", help="Disconnect and delete the VPN")
    parser.add_argument("--scan", action="store_true", help="Alias for status")
    parser.add_argument("--tcp", action="store_true", help="Show TCP servers only")
    parser.add_argument("--all", action="store_true", help="Show all servers")
    args = parser.parse_args()

    if args.stop:
        disconnect_vpn()
        sys.exit(0)
    
    if args.status or args.scan:
        status_vpn()
        sys.exit(0)

    proto_pref = "all" if args.all else ("tcp" if args.tcp else "udp")
    print(f"Fetching servers (Preference: {proto_pref.upper()})...")
    all_servers = get_servers()
    if not all_servers:
        print("No servers found.")
        sys.exit(1)

    display_list = list_servers(all_servers, proto_pref=proto_pref)

    try:
        choice = input("\nEnter Index to connect (or 'q' to quit): ")
        if choice.lower() == 'q':
            sys.exit(0)
        idx = int(choice)
        if 0 <= idx < len(display_list):
            connect_vpn(display_list[idx])
        else:
            print("Invalid index.")
    except ValueError:
        print("Please enter a valid number.")
    except KeyboardInterrupt:
        print("\nExiting.")
