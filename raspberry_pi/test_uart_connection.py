import time
import os
import json
from pymavlink import mavutil

def load_config():
    default_config = {
        "uart_port": "/dev/ttyAMA0",
        "uart_baud": 115200
    }
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return default_config

def main():
    config = load_config()
    port = config.get("uart_port", "/dev/ttyAMA0")
    baud = config.get("uart_baud", 115200)

    print("==========================================================")
    print("    SPEEDYBEE ↔ RASPBERRY PI MAVLINK CONNECTION TESTER    ")
    print("==========================================================")
    print(f"Connecting to serial port: {port} at {baud} baud...")

    try:
        # Open MAVLink connection
        mav_connection = mavutil.mavlink_connection(port, baud=baud)
    except Exception as e:
        print(f"\n[ERROR] Could not open serial port {port}: {e}")
        print("Please check:")
        print(" 1. Serial interface is enabled in raspi-config.")
        print(" 2. Console login over serial is disabled.")
        print(" 3. Your script has permission to access the port (try running with sudo).")
        return

    print("\nWaiting for MAVLink Heartbeat from ArduPilot (Timeout: 10s)...")
    
    try:
        # Wait for heartbeat
        heartbeat = mav_connection.wait_heartbeat(timeout=10.0)
        
        if heartbeat is None:
            print("\n[TIMEOUT] No MAVLink heartbeat received from ArduPilot.")
            print("Troubleshooting steps:")
            print(" - Check if Raspberry Pi TX pin is connected to SpeedyBee RX pad.")
            print(" - Check if Raspberry Pi RX pin is connected to SpeedyBee TX pad.")
            print(" - Swap TX and RX wires if you are unsure.")
            print(" - Ensure Raspberry Pi GND and SpeedyBee GND are connected together.")
            print(" - Confirm the flight controller is powered on and ArduPilot has booted up.")
            print(" - Ensure the UART3 port on SpeedyBee is configured for MAVLink protocol (e.g. SERIAL3_PROTOCOL = 1 or 2, and SERIAL3_BAUD = 115).")
            return
            
        print("\n==========================================================")
        print("          🎉 MAVLINK CONNECTION SUCCESSFUL                ")
        print("==========================================================")
        print("Communication verified! ArduPilot is transmitting heartbeats.")
        print(f" - System ID: {mav_connection.target_system}")
        print(f" - Component ID: {mav_connection.target_component}")
        print(f" - Autopilot type: {heartbeat.autopilot}")
        print(f" - Base Mode: {heartbeat.base_mode}")
        print(f" - System Status: {heartbeat.system_status}")
        print("==========================================================")

    except Exception as e:
        print(f"\n[ERROR] Exception during heartbeat reception: {e}")
    finally:
        mav_connection.close()

if __name__ == "__main__":
    main()
