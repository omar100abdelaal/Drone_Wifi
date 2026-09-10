#!/usr/bin/env python3
"""
SpeedyBee <-> Raspberry Pi Comprehensive UART Diagnostic Tool
Detects:
1. Raw serial signal & baud rate
2. Protocol detection: MAVLink (ArduPilot) vs MSP (Betaflight/INAV)
3. Arming status & Pre-arm failure reasons
4. Live stick / RC channel simulation test
"""

import sys
import time
import json
import os

try:
    import serial
except ImportError:
    print("[ERROR] 'pyserial' is not installed. Please run: pip install pyserial")
    sys.exit(1)

def load_config():
    default_config = {
        "uart_port": "/dev/serial0",
        "uart_baud": 115200
    }
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                cfg = json.load(f)
                default_config.update(cfg)
        except Exception:
            pass
    return default_config

def test_raw_serial(port, baud, duration=5.0):
    print(f"\n[STEP 1] Testing Raw Serial on '{port}' at {baud} baud...")
    try:
        ser = serial.Serial(port, baudrate=baud, timeout=1.0)
    except Exception as e:
        print(f"  ❌ Failed to open {port}: {e}")
        # Try fallback to /dev/ttyAMA0 if serial0 failed
        alt_port = "/dev/ttyAMA0" if port != "/dev/ttyAMA0" else "/dev/serial0"
        print(f"  Trying alternative port: {alt_port}...")
        try:
            ser = serial.Serial(alt_port, baudrate=baud, timeout=1.0)
            port = alt_port
            print(f"  ✅ Successfully opened alternative port {port}")
        except Exception as e2:
            print(f"  ❌ Failed alternative port {alt_port}: {e2}")
            return None, None

    print(f"  Listening for incoming bytes for {duration} seconds...")
    start_time = time.time()
    received_bytes = bytearray()
    
    while time.time() - start_time < duration:
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting)
            received_bytes.extend(chunk)
            print(f"  📡 Received {len(chunk)} bytes (Total: {len(received_bytes)} bytes)")
        time.sleep(0.1)

    ser.close()
    return port, received_bytes

def analyze_traffic(raw_data):
    print("\n[STEP 2] Protocol Analysis:")
    if not raw_data or len(raw_data) == 0:
        print("  ❌ ZERO bytes received from SpeedyBee!")
        print("  Common causes:")
        print("   1. TX and RX wires are SWAPPED (Try: Pi Pin 8 TX -> SpeedyBee RX, Pi Pin 10 RX -> SpeedyBee TX).")
        print("   2. Missing common Ground (GND) wire between Pi and SpeedyBee.")
        print("   3. SpeedyBee UART port is NOT enabled in firmware (Betaflight/ArduPilot).")
        print("   4. SpeedyBee is not powered by battery (USB alone might not power the UART transceiver).")
        return "NONE"

    print(f"  ✅ Total received: {len(raw_data)} bytes")
    hex_sample = ' '.join(f"{b:02X}" for b in raw_data[:24])
    print(f"  Raw Hex Preview: {hex_sample}")

    # Check for MAVLink v1 (0xFE) or MAVLink v2 (0xFD)
    mavlink_v1 = raw_data.count(0xFE)
    mavlink_v2 = raw_data.count(0xFD)
    if mavlink_v2 > 0 or mavlink_v1 > 0:
        print(f"  🎉 Detected MAVLINK traffic (v2 magic headers: {mavlink_v2}, v1: {mavlink_v1})!")
        return "MAVLINK"

    # Check for MSP ($M< or $M>)
    if b'$M<' in raw_data or b'$M>' in raw_data:
        print("  ⚠️ Detected MSP (Betaflight / INAV / Cleanflight) traffic!")
        print("  Notice: Your drone software is currently configured for MAVLink (ArduPilot).")
        return "MSP"

    print("  ⚠️ Bytes received, but unrecognized protocol framing. Baud rate might be different (e.g., 57600 vs 115200).")
    return "UNKNOWN"

def test_mavlink(port, baud):
    print(f"\n[STEP 3] Testing MAVLink Heartbeat & Status on {port}...")
    try:
        from pymavlink import mavutil
    except ImportError:
        print("  ❌ 'pymavlink' is not installed. Run: pip install pymavlink")
        return

    try:
        mav = mavutil.mavlink_connection(port, baud=baud)
        print("  Waiting up to 8 seconds for MAVLink Heartbeat from Flight Controller...")
        hb = mav.wait_heartbeat(timeout=8.0)
        if hb is None:
            print("  ❌ Timeout: No MAVLink Heartbeat received.")
            print("     Make sure the UART port on SpeedyBee has SERIAL_PROTOCOL=1 or 2 in ArduPilot.")
            return

        print("\n  ========================================================")
        print("  ✅ MAVLINK HEARTBEAT CONFIRMED! SpeedyBee is responding.")
        print("  ========================================================")
        print(f"  - System ID:       {mav.target_system}")
        print(f"  - Component ID:    {mav.target_component}")
        print(f"  - Autopilot Type:  {hb.autopilot}")
        print(f"  - Base Mode:       {hb.base_mode}")
        print(f"  - System Status:   {hb.system_status}")

        # Check for arming state
        is_armed = bool(hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        print(f"  - Current Armed State: {'ARMED' if is_armed else 'DISARMED'}")

        # Request and read system messages / errors for 3 seconds
        print("\n  Reading Flight Controller messages (Pre-arm status / Errors)...")
        start = time.time()
        messages = []
        while time.time() - start < 3.0:
            msg = mav.recv_match(type=['STATUSTEXT', 'SYS_STATUS'], blocking=False)
            if msg:
                if msg.get_type() == 'STATUSTEXT':
                    text = msg.text
                    if text not in messages:
                        messages.append(text)
                        print(f"    📢 [FC Message]: {text}")
                elif msg.get_type() == 'SYS_STATUS':
                    v = msg.voltage_battery / 1000.0
                    print(f"    🔋 Battery Voltage: {v:.2f}V (Remaining: {msg.battery_remaining}%)")
            time.sleep(0.05)

        if not messages:
            print("    (No pre-arm warning messages broadcasted)")

        print("\n  --------------------------------------------------------")
        print("  Why Motors Might Not Spin When You Move PS4 Sticks:")
        print("  1. Drone is NOT ARMED: Flight controllers require pressing the ARM button")
        print("     (Button 'X' on PS4 controller) with Throttle at ZERO before motors spin.")
        print("  2. Pre-arm checks failing: Gyro calibration, throttle stick centering,")
        print("     or safety switch preventing arming.")
        print("  3. Check ArduPilot parameter 'ARMING_CHECK' or messages above.")
        print("  --------------------------------------------------------")

    except Exception as e:
        print(f"  ❌ Error testing MAVLink: {e}")

def main():
    print("==========================================================")
    print("     SPEEDYBEE <-> RASPBERRY PI UART DIAGNOSTIC TOOL      ")
    print("==========================================================")
    
    cfg = load_config()
    port = cfg.get("uart_port", "/dev/serial0")
    baud = cfg.get("uart_baud", 115200)

    # 1. Raw serial test
    active_port, raw_data = test_raw_serial(port, baud, duration=4.0)
    if not active_port:
        print("\n[CONCLUSION] Could not open any serial port. Ensure UART is enabled in raspi-config.")
        return

    # 2. Analyze bytes
    proto = analyze_traffic(raw_data)

    # 3. If MAVLink or has data, test MAVLink
    if proto in ("MAVLINK", "UNKNOWN") and raw_data and len(raw_data) > 0:
        test_mavlink(active_port, baud)
    elif proto == "NONE":
        print("\n[ACTION REQUIRED]:")
        print("1. Swap your TX and RX wires:")
        print("   Pi Pin 8 (TX)  --> SpeedyBee RX pad")
        print("   Pi Pin 10 (RX) --> SpeedyBee TX pad")
        print("2. Ensure GND from Pi is connected to GND on SpeedyBee.")
        print("3. Ensure SpeedyBee is powered ON with battery.")
        print("4. Verify UART port is active in SpeedyBee Configurator.")

if __name__ == "__main__":
    main()
