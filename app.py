import subprocess
import time
from flask import Flask, render_template, request, redirect, url_for, flash
from player_utils import PlayerUtils
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

player_utils = PlayerUtils()

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong secret key

def is_wifi_connected_with_polling(max_retries=10, retry_delay=1):
    """Checks for WiFi connectivity by polling.

    Args:
        max_retries (int): The maximum number of times to check for connection.
        retry_delay (int): The number of seconds to wait between checks.

    Returns:
        bool: True if connected, False otherwise.
    """
    for attempt in range(max_retries):
        if player_utils.is_connected_to_wifi():
            return True
        logging.info(f"WiFi not yet connected. Attempt {attempt + 1}/{max_retries}")
        time.sleep(retry_delay)
    return False

@app.route('/', methods=['GET'])
def landing_page():
    """Landing page – accessible only if WiFi is connected."""
    if not player_utils.is_connected_to_wifi():
        return redirect(url_for('wifi_setup'))
    
    # Get all the information needed for the index.html template
    player_id = player_utils.generate_player_id()
    local_ips_with_loopback = player_utils.get_local_ips()
    ethernet_status = "UP" if player_utils.is_ethernet_up() else "DOWN"
    dns_status = player_utils.check_dns()
    ping_status = player_utils.check_ping()
    dhcp_info = player_utils.get_dhcp_info()
    server_status = player_utils.check_server_connectivity()
    qr_code_data = player_utils.generate_qr_code(f"https://acusign.pro/player/register/{player_id}")

    # Update config on app start
    player_utils.config_manager.update_config({
        "device_id": player_id,
        "connection": {
            "ethernet": ethernet_status,
            "dns": dns_status,
            "ping": ping_status,
            "dhcp": dhcp_info,
            "server": server_status
        }
    })

    return render_template(
        'index.html',
        player_id=player_id,
        local_ips_with_loopback=local_ips_with_loopback,
        ethernet_status=ethernet_status,
        dns_status=dns_status,
        ping_status=ping_status,
        dhcp_info=dhcp_info,
        server_status=server_status,
        qr_code_data=qr_code_data,
        port=80,
    )

@app.route('/wifi-setup', methods=['GET', 'POST'])
def wifi_setup():
    """WiFi setup wizard page."""
    config = player_utils.get_config()
    if request.method == 'POST':
        ssid = request.form.get('ssid')
        password = request.form.get('password')
        flash("Updating WiFi settings. Please wait...")
        success, message = player_utils.update_wifi_settings(ssid, password)
        if success:
            # Update config on wifi update
            player_utils.get_config().update_config({
                "wifi": {
                    "ssid": ssid,
                    "password": password
                }
            })

        flash(message)
        if success:
            # Give the system some time to reconfigure the interface.
            if is_wifi_connected_with_polling():
                flash("Connected to WiFi successfully!")
                return redirect(url_for('landing_page'))
            else:
                flash("Failed to connect to WiFi. Please verify your credentials and try again.")
        else:
            flash("An error occurred while updating WiFi settings.")
        # Redirect to prevent form resubmission on refresh
        return redirect(url_for('wifi_setup')) 

    wifi_list = player_utils.get_available_wifi_networks()
    return render_template('wifi_setup.html', wifi_list=wifi_list, config = config)


if __name__ == '__main__':
    # if not player_utils.is_connected_to_wifi():
    #     logging.info("WiFi not connected. Launching WiFi setup wizard.")
    # else:
    #     logging.info("WiFi connected. Launching landing page.")
    app.run(host='0.0.0.0', port=80, debug=True)
