#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting bootstrap installation..."

# Ensure the script is run as root.
if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root. Try using sudo."
  exit 1
fi

# Update package lists.
echo "Updating package lists..."
apt-get update

# Install Git, Python3, and pip if they are not already installed.
echo "Installing Git, Python3, and pip..."
apt-get install -y git python3 python3-pip

# Set the installation directory and repository URL.
INSTALL_DIR="/opt/player-bootstrap"
REPO_URL="https://github.com/acusign-pro/player-bootstrap.git"

# Clone or update the repository.
if [ -d "$INSTALL_DIR" ]; then
  echo "Directory $INSTALL_DIR already exists. Pulling latest changes..."
  cd "$INSTALL_DIR"
  git pull origin master
else
  echo "Cloning repository to $INSTALL_DIR..."
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

echo "Bootstrap installation completed successfully!"