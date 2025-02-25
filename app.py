import subprocess
import time
from flask import Flask, render_template, request, redirect, url_for, flash
import utils

app = Flask(__name__)


@app.route('/', methods=['GET'])
def landing_page():
    """Landing page – accessible only if WiFi is connected."""
    if not utils.is_connected_to_wifi():
        return redirect(url_for('wifi_setup'))
    return render_template('landing.html')

@app.route('/wifi-setup', methods=['GET', 'POST'])
def wifi_setup():
    """WiFi setup wizard page."""
    if request.method == 'POST':
        ssid = request.form.get('ssid')
        password = request.form.get('password')
        flash("Updating WiFi settings. Please wait...")
        success, message = utils.update_wifi_settings(ssid, password)
        flash(message)
        if success:
            # Give the system some time to reconfigure the interface.
            time.sleep(10)
            if utils.is_connected_to_wifi():
                flash("Connected to WiFi successfully!")
                return redirect(url_for('landing_page'))
            else:
                flash("Failed to connect to WiFi. Please verify your credentials and try again.")
        else:
            flash("An error occurred while updating WiFi settings.")
    wifi_list = utils.get_available_wifi_networks()
    return render_template('wifi_setup.html', wifi_list=wifi_list)

if __name__ == '__main__':
    if not utils.is_connected_to_wifi():
        print("WiFi not connected. Launching WiFi setup wizard.")
    else:
        print("WiFi connected. Launching landing page.")
    app.run(host='0.0.0.0', port=80, debug=True)