"""
Network tools - IP, connectivity, WiFi info.
"""

import socket
import subprocess
from .tool_registry import register_tool

try:
    import psutil
except ImportError:
    psutil = None


def get_network_info() -> str:
    """Get network interface information and IP addresses."""
    if not psutil:
        return "psutil not installed. Run: pip install psutil"
    
    result = "Network Information:\n"
    
    # Get all network interfaces
    interfaces = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    
    for iface, addrs in interfaces.items():
        # Skip loopback and down interfaces
        if iface == 'lo' or (iface in stats and not stats[iface].isup):
            continue
        
        for addr in addrs:
            if addr.family == socket.AF_INET:  # IPv4
                result += f"{iface}: {addr.address}\n"
    
    # Try to get public IP (optional, requires internet)
    try:
        # Use a simple method that doesn't require external packages
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        result += f"Primary IP: {local_ip}\n"
    except:
        pass
    
    return result.strip()


def check_internet() -> str:
    """Check if internet connection is available."""
    hosts_to_check = [
        ("8.8.8.8", 53, "Google DNS"),
        ("1.1.1.1", 53, "Cloudflare DNS"),
    ]
    
    for host, port, name in hosts_to_check:
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return f"Internet is connected. Successfully reached {name}."
        except socket.error:
            continue
    
    return "No internet connection detected. Could not reach any DNS servers."


def get_wifi_info() -> str:
    """Get WiFi connection information (Linux only)."""
    try:
        # Try nmcli (NetworkManager) - common on most Linux distros
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'ACTIVE,SSID,SIGNAL,SECURITY', 'device', 'wifi'],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split(':')
                if len(parts) >= 4 and parts[0] == 'yes':
                    ssid = parts[1]
                    signal = parts[2]
                    security = parts[3]
                    return f"WiFi Connected: {ssid}\nSignal Strength: {signal}%\nSecurity: {security}"
            return "WiFi available but not connected to any network."
        
        # Fallback to iwconfig
        result = subprocess.run(['iwconfig'], capture_output=True, text=True, timeout=5)
        if "ESSID" in result.stdout:
            for line in result.stdout.split('\n'):
                if "ESSID" in line:
                    return f"WiFi: {line.strip()}"
        
        return "Could not determine WiFi status."
    
    except FileNotFoundError:
        return "WiFi tools (nmcli/iwconfig) not found. Are you on a desktop without WiFi?"
    except subprocess.TimeoutExpired:
        return "WiFi check timed out."
    except Exception as e:
        return f"Could not get WiFi info: {e}"


# ============================================================
# Register all network tools
# ============================================================

register_tool(
    name="get_network_info",
    description="Get network interfaces and IP addresses.",
    parameters={"type": "object", "properties": {}, "required": []},
    func=get_network_info
)

register_tool(
    name="check_internet",
    description="Check if internet connection is working.",
    parameters={"type": "object", "properties": {}, "required": []},
    func=check_internet
)

register_tool(
    name="get_wifi_info",
    description="Get WiFi network name, signal strength, and security type.",
    parameters={"type": "object", "properties": {}, "required": []},
    func=get_wifi_info
)
