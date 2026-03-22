# VPN Gate CLI Connector

A lightweight Python script to connect to [VPN Gate](https://www.vpngate.net/) servers using NetworkManager (`nmcli`). Optimized for modern Linux systems with strict OpenSSL requirements.

**Note:** Tested on CachyOS (Arch) only, fully vibe coded, without an ounce of networking knowledge, so YMMV. Good luck 

## Features

- **Protocol Preference:** Defaults to **UDP** for lower latency and better speed.
- **Legacy Support:** Automatically configures older encryption standards (`AES-128-CBC`, `SHA1`) required by most VPN Gate servers.
- **Speed Optimized:** Implements a **10-second connection timeout**—if a server doesn't connect instantly, it's skipped, because I'm ADHD ish
- **Easy Cleanup:** One command to disconnect and completely remove the VPN configuration from your system.
- **No Persistence:** Doesn't leave clutter in your NetworkManager list after use.

## Installation

### 1. AUR (Arch Linux) - WIP
The project is currently being submitted to the AUR. You can try installing it with:
```bash
yay -S vpn-gate-client
```

### 2. Manual Installation
Clone the repository and run the scripts directly:
```bash
git clone https://github.com/Me3paw/vpn-gate-client.git
cd vpn-gate-client
```

Dependencies will be automatically installed from `requirements.txt` the first time you run either script.

## Usage

### 1. GUI Mode (Recommended)
Launch the graphical interface:
```bash
./vpngate-gui.py
```

### 2. CLI Mode
Connect to a VPN using the command line:
```bash
./vpngate_cli.py
```

### 2. Connection Options
- **Filter for TCP:** Use if UDP is blocked on your network.
  ```bash
  vpngate --tcp
  ```
- **Show All Protocols:**
  ```bash
  vpngate --all
  ```

### 3. Management
- **Check Status:** See if the VPN is currently active.
  ```bash
  vpngate --status
  ```
- **Disconnect & Delete:** Stops the connection and removes it from NetworkManager.
  ```bash
  vpngate --stop
  ```

## Troubleshooting

### Connection Timeouts
The script enforces a 10s timeout. Many VPN Gate servers are hosted by volunteers and may be offline or congested. If a connection times out:
1. Run `vpngate` again.
2. Pick a different server index (try one with a slightly higher ping but high score).
3. If UDP consistently fails, try `vpngate --tcp`.
4. If network slow, increase timeout to whatever u want in the code

### Technical Details
- **Connection Name:** `vpngate-active`
- **Configuration:** Uses `nmcli connection import` followed by manual `vpn.data` modification to inject `data-ciphers-fallback` and legacy providers.
- **Credentials:** Automatically sets username `vpn` and password `vpn`.
