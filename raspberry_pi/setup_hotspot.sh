#!/bin/bash
# Script to configure Raspberry Pi as a Wi-Fi Access Point (Hotspot)
# SSID: Drone_AP
# Password: dronepassword / 12345678
# Pi IP: 192.168.50.1

SSID="Drone_AP"
PASSWORD="12345678"
IP_ADDR="192.168.50.1/24"

echo "========================================="
echo "   CONFIGURING DRONE WI-FI HOTSPOT       "
echo "========================================="
echo "SSID:      $SSID"
echo "Password:  $PASSWORD"
echo "Pi IP:     192.168.50.1"
echo "========================================="

# Ensure wifi is not blocked
sudo rfkill unblock wifi

# Remove existing Drone_AP connection if present
sudo nmcli connection delete "$SSID" 2>/dev/null || true

# Create the Wi-Fi hotspot connection
sudo nmcli connection add type wifi ifname wlan0 con-name "$SSID" autoconnect yes ssid "$SSID"

# Configure AP mode (2.4GHz band)
sudo nmcli connection modify "$SSID" 802-11-wireless.mode ap 802-11-wireless.band bg

# Configure WPA2-PSK security
sudo nmcli connection modify "$SSID" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PASSWORD"

# Set static IP 192.168.50.1 and enable DHCP server for connected devices
sudo nmcli connection modify "$SSID" ipv4.addresses "$IP_ADDR" ipv4.method shared

# Ensure it starts automatically on every boot with top priority
sudo nmcli connection modify "$SSID" connection.autoconnect-priority 100

echo "Starting hotspot..."
sudo nmcli connection up "$SSID"

echo "========================================="
echo " Hotspot active! Broadcast SSID: $SSID"
echo "========================================="
