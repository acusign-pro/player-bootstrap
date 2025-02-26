import os
import hashlib
import socket
import subprocess
import netifaces as ni
import platform
import shutil
import requests
import re
from wifi import Cell, Scheme

def load_cpu_info(file_path="/proc/cpuinfo"):
    if not os.path.exists(file_path):
        print(f"Error: The file '{file_path}' does not exist.")
        return {}
    result = {"processors": [], "Revision": None, "Serial": None, "Model": None}
    current_proc = None
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                if current_proc:
                    result["processors"].append(current_proc)
                    current_proc = None
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key.lower() == "processor":
                    if current_proc is not None:
                        result["processors"].append(current_proc)
                    current_proc = {}
                if current_proc is not None:
                    current_proc[key] = value
                else:
                    if key == "Revision":
                        result["Revision"] = value
                    elif key == "Serial":
                        result["Serial"] = value
                    elif key == "Model":
                        result["Model"] = value
            else:
                continue
    if current_proc:
        result["processors"].append(current_proc)
    return result

def get_mac_address(interface_priority=('eth0', 'en0', 'Ethernet', 'ens33')):
    for iface in ni.interfaces():
        if iface in interface_priority:
            addrs = ni.ifaddresses(iface)
            if ni.AF_LINK in addrs:
                return addrs[ni.AF_LINK][0]['addr']
    for iface in ni.interfaces():
        addrs = ni.ifaddresses(iface)
        if ni.AF_LINK in addrs:
            return addrs[ni.AF_LINK][0]['addr']
    return None

def generate_player_id():
    cpu_info = load_cpu_info()
    serial = cpu_info.get("Serial")
    if serial:
        return f"{serial[0:4]}-{serial[4:8]}-{serial[8:12]}-{serial[12:16]}"
    else:
        mac = get_mac_address()
        print(f"MAC: {mac}")
        if not mac:
            mac = "00:00:00:00:00:00"
        hash_str = hashlib.sha256(mac.encode()).hexdigest()
        return f"{hash_str[0:4]}-{hash_str[4:8]}-{hash_str[8:12]}-{hash_str[12:16]}"

def get_local_ips():
    ip_list = []
    for iface in ni.interfaces():
        addrs = ni.ifaddresses(iface)
        if ni.AF_INET in addrs:
            for link in addrs[ni.AF_INET]:
                ip_addr = link.get('addr')
                if ip_addr and not ip_addr.startswith('127.'):
                    ip_list.append(ip_addr)
    return ip_list

def is_ethernet_up(interface_priority=('eth0', 'en0', 'Ethernet', 'ens33')):
    for iface in ni.interfaces():
        if iface in interface_priority:
            addrs = ni.ifaddresses(iface)
            if ni.AF_INET in addrs:
                return True
    return False

def check_dns():
    try:
        socket.gethostbyname('google.com')
        return "OK"
    except Exception:
        return "FAIL"

def check_ping(host="8.8.8.8"):
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return "OK" if result.returncode == 0 else "FAIL"
    except Exception:
        return "FAIL"

def get_dhcp_info():
    gws = ni.gateways()
    default = gws.get('default')
    if default and ni.AF_INET in default:
        return default[ni.AF_INET][0]
    return "Unknown"

def check_server_connectivity(server_url="https://acusign.pro"):
    try:
        r = requests.get(server_url, timeout=3)
        if r.status_code == 200:
            return "Connected"
        else:
            return f"HTTP {r.status_code}"
    except Exception:
        return "Not Connected"
    

def is_connected_to_wifi():
    """Check if device is connected to WiFi by checking if wlan0 has an IP address."""
    try:
        result = subprocess.run(["ifconfig", "wlan0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if "inet " in result.stdout:
            return True
    except Exception as e:
        print(f"Error checking WiFi connectivity: {e}")
    return False

def get_available_wifi_networks():
    """
    Scan for available WiFi networks on Linux, Windows, and macOS.
    Returns a list of unique SSIDs.
    """
    networks = []
    system = platform.system()
    print(f"Scanning for WiFi networks on {system}...")
    
    # For testing/development on macOS, return some sample networks
    if system == "Darwin":
        print("On macOS, returning sample networks for testing")
        return ["Home WiFi", "Guest Network", "Office WiFi"]
    
    try:
        if system == "Linux":
            # Use iwlist on Linux (this may require sudo privileges).
            result = subprocess.run(
                ["sudo", "iwlist", "wlan0", "scan"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("ESSID:"):
                    ssid = line.split("ESSID:")[1].strip().strip('"')
                    if ssid and ssid not in networks:
                        networks.append(ssid)

        elif system == "Windows":
            # Use netsh command on Windows.
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                # Windows output typically has lines like "SSID 1 : NetworkName"
                if line.startswith("SSID ") and ":" in line:
                    parts = line.split(":", 1)
                    ssid = parts[1].strip()
                    if ssid and ssid not in networks:
                        networks.append(ssid)
        else:
            print(f"Unsupported operating system: {system}")
    except Exception as e:
        print(f"Error scanning WiFi networks on {system}: {e}")
        import traceback
        traceback.print_exc()

    return networks

def update_wifi_settings(ssid, password):
    """
    Update WiFi settings in /etc/wpa_supplicant/wpa_supplicant.conf and restart WiFi.
    Note: This operation requires root privileges.
    """
    # Prepare a network block to append to the wpa_supplicant config.
    network_block = f"""
network={{
    ssid="{ssid}"
    psk="{password}"
}}
"""
    try:
        # Backup existing configuration.
        subprocess.run(["cp", "/etc/wpa_supplicant/wpa_supplicant.conf", "/etc/wpa_supplicant/wpa_supplicant.conf.bak"], check=True)
        # Append the new network block.
        with open("/etc/wpa_supplicant/wpa_supplicant.conf", "a") as f:
            f.write(network_block)
        # Reconfigure WiFi using wpa_cli.
        subprocess.run(["wpa_cli", "-i", "wlan0", "reconfigure"], check=True)
        return True, "WiFi settings updated. Reconfiguring WiFi..."
    except Exception as e:
        return False, f"Error updating WiFi settings: {e}"
    

if __name__ == "__main__":
    networks = get_available_wifi_networks()
    print(f"Available WiFi networks: {networks}")