# Drone Wi-Fi Range Test Procedure

Use this document to log the range performance of the Raspberry Pi 4's built-in Wi-Fi and determine if external high-power USB antennas are required for outdoor flight.

---

## 📋 Test Setup
1. Place the Raspberry Pi 4 (powered on, broadcasting `Drone_AP`) on a table or elevated stand.
2. Connect your Windows laptop to the `Drone_AP` network.
3. Walk away in straight-line increments.

---

## 🛠️ Commands to Run at Each Distance

Run these commands in the **Windows Command Prompt / PowerShell**:

1. **Check Signal Strength (%)**:
   ```cmd
   netsh wlan show interfaces | findstr Signal
   ```

2. **Measure Latency & Packet Loss**:
   ```cmd
   ping -n 10 192.168.50.1
   ```

---

## 📊 Range Test Log Table

Edit this file and fill in your recorded measurements:

| Distance | Signal Strength (%) | Avg Ping (ms) | Max Ping (ms) | Packet Loss (%) | Link Status (Stable/Dropped) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **5 m** | | | | | |
| **10 m** | | | | | |
| **20 m** | | | | | |
| **30 m** | | | | | |
| **40 m** | | | | | |
| **50 m** | | | | | |
| **75 m** | | | | | |
| **100 m** | | | | | |

---

## 🧠 Decision Thresholds
- **If Signal is > 30% and packet loss is 0% at 75m**: The built-in Wi-Fi is sufficient for close-range testing.
- **If packet loss exceeds 5% or connection drops under 50m**: An external USB Wi-Fi adapter with an RP-SMA antenna connector is required for safety.
