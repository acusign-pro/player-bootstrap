import os
import random
import string
import hashlib
import socket
import subprocess
import requests
import os
import netifaces as ni
from flask import Flask, render_template_string, request

app = Flask(__name__)


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



# -------------------------
# 1. Generate Player ID
# -------------------------
def get_mac_address(interface_priority=('eth0', 'en0', 'Ethernet', 'ens33')):
    """
    Attempt to retrieve the MAC address from a list of possible interfaces.
    Adjust interface_priority for your environment if needed.
    """
    for iface in ni.interfaces():
        if iface in interface_priority:
            addrs = ni.ifaddresses(iface)
            if ni.AF_LINK in addrs:
                return addrs[ni.AF_LINK][0]['addr']
    # Fallback: pick the first interface that has a MAC address
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
        # Generate a hash based solely on the MAC address to ensure consistency
        hash_str = hashlib.sha256(mac.encode()).hexdigest()
        # Format the player ID to look like "XXXX-XXXX-XXXX-XXXX"
        return f"{hash_str[0:4]}-{hash_str[4:8]}-{hash_str[8:12]}-{hash_str[12:16]}"

# -------------------------
# 2. Detect Local IP + 127.0.0.1
# -------------------------
def get_local_ips():
    """
    Return a list of all IPv4 addresses (excluding loopback).
    """
    ip_list = []
    for iface in ni.interfaces():
        addrs = ni.ifaddresses(iface)
        if ni.AF_INET in addrs:
            for link in addrs[ni.AF_INET]:
                ip_addr = link.get('addr')
                if ip_addr and not ip_addr.startswith('127.'):
                    ip_list.append(ip_addr)
    return ip_list

# -------------------------
# 3. Network Status
# -------------------------
def is_ethernet_up(interface_priority=('eth0', 'en0', 'Ethernet', 'ens33')):
    """
    Checks if one of the prioritized interfaces is 'UP' by verifying it has an IPv4.
    """
    for iface in ni.interfaces():
        if iface in interface_priority:
            addrs = ni.ifaddresses(iface)
            if ni.AF_INET in addrs:
                return True
    return False

def check_dns():
    """
    Simple DNS check by attempting to resolve 'google.com'.
    """
    try:
        socket.gethostbyname('google.com')
        return "OK"
    except Exception:
        return "FAIL"

def check_ping(host="8.8.8.8"):
    """
    Ping a host (default: 8.8.8.8) once. Returns "OK" if successful, else "FAIL".
    """
    try:
        # '-c 1' = 1 ping, '-W 1' = 1 second timeout (Unix/Linux)
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return "OK" if result.returncode == 0 else "FAIL"
    except Exception:
        return "FAIL"

def get_dhcp_info():
    """
    Get the default gateway IP (DHCP server) from netifaces.gateways().
    """
    gws = ni.gateways()
    default = gws.get('default')
    if default and ni.AF_INET in default:
        return default[ni.AF_INET][0]  # IP address of the default gateway
    return "Unknown"

def check_server_connectivity(server_url="https://acusign.pro"):
    """
    Check connectivity to the server (acusign.pro) via an HTTP GET.
    """
    try:
        r = requests.get(server_url, timeout=3)
        if r.status_code == 200:
            return "Connected"
        else:
            return f"HTTP {r.status_code}"
    except Exception:
        return "Not Connected"

# -------------------------
# Flask Routes
# -------------------------
@app.route('/')
def index():
    # Generate the player ID
    player_id = generate_player_id()

    # Get local IP addresses (excluding loopback)
    local_ips = get_local_ips()

    # Always include 127.0.0.1
    local_ips_with_loopback = local_ips

    # Detect the port from the request host (if behind a proxy, adjust accordingly)
    port = request.host.split(':')[-1] if ':' in request.host else '5000'

    # Gather network statuses
    ethernet_status = "UP" if is_ethernet_up() else "DOWN"
    dns_status = check_dns()
    ping_status = check_ping()
    dhcp_info = get_dhcp_info()
    server_status = check_server_connectivity()

    # Render everything in a single template string for brevity.
    # Google Font links are added to load Nunito and Roboto.
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Welcome!</title>
        <!-- Google Fonts -->
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Nunito:ital,wght@0,200..1000;1,200..1000&family=Roboto:ital,wght@0,100;0,300;0,400;0,500;0,700;0,900;1,100;1,300;1,400;1,500;1,700;1,900&display=swap" rel="stylesheet">
        <style>
            /* Base styles using Roboto for body text */
            body {
                font-family: "Nunito", serif;
                margin: 40px;
                background-color: #f9f9f9;
                color: #333;
                margin: 0;
                padding: 0;
            }
            /* Unique Nunito class for headings */
            .nunito-header {
                font-family: "Nunito", serif;
                font-optical-sizing: auto;
                font-weight: 700;
                font-style: normal;
                background-color: #FFBF00;
                padding: 5px;
            }
            .header {
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 2.5em;
            }
            .player {
                text-align: center;
                font-size: 1.2em;
                margin: 10px 0;
            }
            .player-id {
                text-align: center;
                font-size: 1.2em;
                margin: 10px 0;
                font-family: "Courier New", Courier, monospace;
                font-weight: bold;
            }
            .content {
                padding: 20px;
                align-items: center;
            }
            .section {
                margin-top: 20px;
            }
            .network-status, .connectivity-status {
                margin-top: 20px;
                border: 1px solid #aaa;
                padding: 0;
                border-radius: 5px;
                max-width: 600px;
            }
            .network-status h3, .connectivity-status h3 {
                margin-top: 0;
            }
            .info-list {
                list-style-type: none;
                padding-left: 5px;
            }
            .info-list li {
                margin: 5px 0;
            }
            a {
                color: #007BFF;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1 class="nunito-header">Welcome!</h1>
        </div>

        <div class="player">
            Player id:  <span class="player-id">{{ player_id }}</span>
        </div>

        <div class="content">
          <div class="section">
              <p>Register your player id at <a href="https://acusign.pro" target="_blank">acusign.pro</a> to manage.</p>
              <p>
                  To connect from browser use:
                  {% for ip in local_ips_with_loopback %}
                    <a href="http://{{ ip }}:{{ port }}" target="_blank">http://{{ ip }}:{{ port }}</a>
                  {% endfor %}
              </p>
              <p>
                  To locally change settings, connect a keyboard and press <strong>Ctrl N</strong> or <strong>F6</strong>.
              </p>
          </div>

          <div class="network-status">
              <h3 class="nunito-header">Status of Network</h3>
              <ul class="info-list">
                  <li>Ethernet: {{ ethernet_status }}</li>
                  <li>DNS: {{ dns_status }}</li>
                  <li>PING: {{ ping_status }}</li>
                  <li>DHCP: {{ dhcp_info }}</li>
              </ul>
          </div>

          <div class="connectivity-status">
              <h3 class="nunito-header">Connectivity Status</h3>
              <ul class="info-list">
                  <li>Server: acusign.pro</li>
                  <li>Status: {{ server_status }}</li>
              </ul>
          </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(
        html_template,
        player_id=player_id,
        local_ips_with_loopback=local_ips_with_loopback,
        port=port,
        ethernet_status=ethernet_status,
        dns_status=dns_status,
        ping_status=ping_status,
        dhcp_info=dhcp_info,
        server_status=server_status
    )

if __name__ == '__main__':
    # Run the Flask app on all interfaces at port 5000.
    app.run(debug=True, host='0.0.0.0', port=5001)