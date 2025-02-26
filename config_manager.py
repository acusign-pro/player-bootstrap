import json
import os
import logging
from datetime import datetime

class ConfigManager:
    """
    Manages the configuration file for the application.
    """

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config_data = self.load_config()

    def load_config(self):
        """
        Loads the configuration from the JSON file.
        If the file doesn't exist, it creates a default configuration.
        """
        if not os.path.exists(self.config_file):
            logging.info(f"Config file '{self.config_file}' not found. Creating a new one.")
            default_config = {
                "player_id": "",
                "wifi": {
                    "ssid": "",
                    "password": ""
                },
                "connection": {
                    "ethernet": "DOWN",
                    "dns": "FAIL",
                    "ping": "FAIL",
                    "dhcp": "Unknown",
                    "server": "Not Connected"
                }
            }
            self.save_config(default_config)
            return default_config
        else:
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logging.error(f"Error decoding JSON from '{self.config_file}'.")
                return {}

    def save_config(self, config_data):
        """
        Saves the configuration to the JSON file, but only if the file is not empty
        """
        if config_data:
            try:
                with open(self.config_file, "w") as f:
                    json.dump(config_data, f, indent=4)
                logging.info(f"Config saved to '{self.config_file}'.")
            except Exception as e:
                logging.error(f"Error saving config to '{self.config_file}': {e}")
        else:
            logging.info("not saving config, the config data is empty")

    def get_config(self):
        """
        Returns the current configuration data.
        """
        return self.config_data

    def update_config(self, new_data):
        """
        Updates the existing configuration with new data, without overwriting the entire file.
        """
        if not new_data:
            logging.warning("No new data provided for update.")
            return
        logging.info(f"Updating config with new data: {new_data}")

        config_changed = False

        if not self.config_data:
          self.config_data = {}

        if "player_id" in new_data and new_data["player_id"] != self.config_data.get("player_id"):
            self.config_data["player_id"] = new_data["player_id"]
            config_changed = True

        if "wifi" in new_data:
            if "ssid" in new_data["wifi"] and new_data["wifi"]["ssid"] != self.config_data.get("wifi", {}).get("ssid"):
                self.config_data.setdefault("wifi", {})["ssid"] = new_data["wifi"]["ssid"]
                config_changed = True
            if "password" in new_data["wifi"] and new_data["wifi"]["password"] != self.config_data.get("wifi", {}).get("password"):
                self.config_data.setdefault("wifi", {})["password"] = new_data["wifi"]["password"]
                config_changed = True

        if "connection" in new_data:
            for key, value in new_data["connection"].items():
                if self.config_data.get("connection", {}).get(key) != value:
                    self.config_data.setdefault("connection", {})[key] = value
                    config_changed = True

        self.config_data["updated_at"] = datetime.now().isoformat()

        if config_changed:
            self.save_config(self.config_data)
        else:
            logging.info("No changes detected in config data.")

    def touch(self):
        """
        Updates the 'updated_at' timestamp in the configuration file.
        """
        self.config_data["updated_at"] = datetime.now().isoformat()
        self.save_config(self.config_data)

# Example usage (you can place this in your app.py or a test file):
if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  config_manager = ConfigManager()

  # Initial load
  current_config = config_manager.get_config()
  logging.info(f"Initial config: {current_config}")

  new_config_data = {
  }
  config_manager.update_config(new_config_data)

  config_manager.touch()

  #check if connection was updated
  current_config = config_manager.get_config()
  logging.info(f"Updated config: {current_config}")
