"""
Network tools - IP, connectivity, WiFi info.
"""

import logging
import socket
import subprocess
from typing import Optional
from .tool_registry import register_tool

logger = logging.getLogger("tools.network")

# Standard network timeout
NETWORK_TIMEOUT = 3

try:
    import psutil
except ImportError:
    psutil = None
    logger.warning("psutil not installed - network interface info limited")


def get_network_info() -> str:
    """Get network interface information and IP addresses."""
    if not psutil:
        return "Network interface info unavailable. Install psutil: pip install psutil"
    
    try:
        result = "Network Information:\n"
        
        # Get all network interfaces
        interfaces = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        
        active_interfaces = []
        for iface, addrs in interfaces.items():
            # Skip loopback and down interfaces
            if iface == 'lo':
                continue
            if iface in stats and not stats[iface].isup:
                continue
            
            for addr in addrs:
                if addr.family == socket.AF_INET:  # IPv4
                    active_interfaces.append(f"{iface}: {addr.address}")
        
        if active_interfaces:
            for iface_info in active_interfaces:
                result += f"{iface_info}\n"
        else:
            result += "No active network interfaces found.\n"
        
        # Try to get primary IP (the one used for internet)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(NETWORK_TIMEOUT)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                result += f"Primary IP: {local_ip}"
        except (socket.error, OSError) as e:
            logger.debug(f"Could not determine primary IP: {e}")
        
        return result.strip()
        
    except Exception as e:
        logger.error(f"get_network_info failed: {e}")
        return f"Could not get network info: {e}"


def check_internet() -> str:
    """Check if internet connection is available."""
    hosts_to_check = [
        ("8.8.8.8", 53, "Google DNS"),
        ("1.1.1.1", 53, "Cloudflare DNS"),
        ("208.67.222.222", 53, "OpenDNS"),
    ]
    
    for host, port, name in hosts_to_check:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(NETWORK_TIMEOUT)
            sock.connect((host, port))
            return f"Internet is connected. Successfully reached {name}."
        except socket.error as e:
            logger.debug(f"Could not reach {name}: {e}")
            continue
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
    
    return "No internet connection detected. Could not reach any DNS servers."


def get_wifi_info() -> str:
    """Get WiFi connection information (Linux only)."""
    # Try nmcli first (NetworkManager) - most common on desktop Linux
    wifi_info = _get_wifi_via_nmcli()
    if wifi_info:
        return wifi_info
    
    # Try iw/iwconfig as fallback (for minimal systems)
    wifi_info = _get_wifi_via_iw()
    if wifi_info:
        return wifi_info
    
    return "Could not determine WiFi status. NetworkManager or iw tools not available."


def _get_wifi_via_nmcli() -> Optional[str]:
    """Get WiFi info using NetworkManager's nmcli."""
    try:
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'ACTIVE,SSID,SIGNAL,SECURITY', 'device', 'wifi'],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split(':')
                if len(parts) >= 4 and parts[0] == 'yes':
                    ssid = parts[1] or "Hidden Network"
                    signal = parts[2] or "Unknown"
                    security = parts[3] or "Open"
                    return f"WiFi Connected: {ssid}\nSignal Strength: {signal}%\nSecurity: {security}"
            return "WiFi available but not connected to any network."
            
    except FileNotFoundError:
        logger.debug("nmcli not found")
    except subprocess.TimeoutExpired:
        logger.debug("nmcli timed out")
    except Exception as e:
        logger.debug(f"nmcli error: {e}")
    
    return None


def _get_wifi_via_iw() -> Optional[str]:
    """Get WiFi info using iw/iwconfig (fallback)."""
    try:
        # Try iwconfig first
        result = subprocess.run(
            ['iwconfig'],
            capture_output=True, text=True, timeout=5,
            stderr=subprocess.DEVNULL
        )
        if result.returncode == 0 and "ESSID" in result.stdout:
            for line in result.stdout.split('\n'):
                if "ESSID" in line:
                    return f"WiFi: {line.strip()}"
                    
    except FileNotFoundError:
        logger.debug("iwconfig not found")
    except subprocess.TimeoutExpired:
        logger.debug("iwconfig timed out")
    except Exception as e:
        logger.debug(f"iwconfig error: {e}")
    
    return None


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

