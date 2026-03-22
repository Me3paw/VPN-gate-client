# VPN Gate CLI Connector

A lightweight Python script to connect to [VPN Gate](https://www.vpngate.net/) servers using NetworkManager (`nmcli`). Optimized for modern Linux systems with strict OpenSSL requirements.

**Note:** Tested on CachyOS (Arch) only, but should work in other linux distributions.

## Features

- **Protocol Preference:** Defaults to **UDP** for lower latency and better speed.
- **Legacy Support:** Automatically configures older encryption standards (`AES-128-CBC`, `SHA1`) required by most VPN Gate servers.
- **Speed Optimized:** Implements a **5-second connection timeout**—if a server doesn't connect instantly, it's skipped.
- **Easy Cleanup:** One command to disconnect and completely remove the VPN configuration from your system.
- **No Persistence:** Doesn't leave clutter in your NetworkManager list after use.

## Installation

The script is installed in `~/vpngate-cli/` and symlinked to `vpngate` in your path.

## Usage

### 1. Connect to a VPN
By default, this shows the top UDP servers:
```bash
vpngate
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
The script enforces a 5s timeout. Many VPN Gate servers are hosted by volunteers and may be offline or congested. If a connection times out:
1. Run `vpngate` again.
2. Pick a different server index (try one with a slightly higher ping but high score).
3. If UDP consistently fails, try `vpngate --tcp`.

### Technical Details
- **Connection Name:** `vpngate-active`
- **Configuration:** Uses `nmcli connection import` followed by manual `vpn.data` modification to inject `data-ciphers-fallback` and legacy providers.
- **Credentials:** Automatically sets username `vpn` and password `vpn`.
