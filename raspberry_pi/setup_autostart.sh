#!/bin/bash
# Autostart Setup Script for Raspberry Pi

echo "========================================="
echo " Setting up Drone Autostart Service..."
echo "========================================="

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Make start_all.sh executable
chmod +x "$DIR/start_all.sh"

# Copy systemd service file to /etc/systemd/system/
sudo cp "$DIR/drone_pi.service" /etc/systemd/system/

# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service so it automatically runs on boot/power-on
sudo systemctl enable drone_pi.service

# Start the service now
sudo systemctl start drone_pi.service

echo "========================================="
echo " Success! Drone service will now start automatically on power-on."
echo " Status check command: sudo systemctl status drone_pi.service"
echo "========================================="
