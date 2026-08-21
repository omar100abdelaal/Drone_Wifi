import sys
import os
import json
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui.main_window import MainWindow
from controller.control_state import ControlState
from controller.gamepad import GamepadThread
from controller.ds4_battery import DS4WindowsBatteryThread
from communication.udp_control import UDPControlThread
from communication.video_receiver import VideoReceiverThread
from telemetry.telemetry import TelemetryThread
from safety.failsafe import FailsafeHandler

def load_config():
    default_config = {
        "raspberry_pi_ip": "192.168.50.1",
        "control_port": 5000,
        "control_rate": 50,
        "simulation_mode": True,
        "dead_zone": 0.1,
        "video_port": 5001,
        "gamepad_index": 0
    }
    
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=4)
        return default_config
        
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config.json, using defaults. Error: {e}")
        return default_config

import subprocess

def configure_ds4windows():
    # Helper to pre-configure DS4Windows settings (start minimized & set correct OSC ports)
    import xml.etree.ElementTree as ET
    appdata = os.getenv("APPDATA")
    if not appdata:
        return
    profiles_path = os.path.join(appdata, "DS4Windows", "Profiles.xml")
    if os.path.exists(profiles_path):
        try:
            tree = ET.parse(profiles_path)
            root = tree.getroot()
            changed = False
            
            # Helper to find or create an element
            def set_element(name, val):
                nonlocal changed
                elem = root.find(name)
                if elem is None:
                    elem = ET.SubElement(root, name)
                    elem.text = val
                    changed = True
                elif elem.text != val:
                    elem.text = val
                    changed = True

            set_element("startMinimized", "True")
            set_element("UseOSCServer", "True")
            set_element("OSCServerPort", "9001")
            set_element("UseOSCSender", "True")
            set_element("OSCSenderPort", "9002")
            
            if changed:
                tree.write(profiles_path, encoding="utf-8", xml_declaration=True)
                print("[Launcher] Auto-configured DS4Windows to start minimized and set OSC ports (9001/9002).")
        except Exception as e:
            print(f"[Launcher] Error configuring Profiles.xml: {e}")

def launch_ds4windows():
    # Locate DS4Windows.exe relative to main.py
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ds4_path = os.path.join(base_dir, "DS4Windows.3.5.x64.DS4-Windows.com", "win-x64", "DS4Windows.exe")
    
    if not os.path.exists(ds4_path):
        print(f"[Launcher] DS4Windows not found at {ds4_path}")
        return

    # Pre-configure settings (minimized, ports)
    configure_ds4windows()
        
    # Check if already running using tasklist
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        output = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq DS4Windows.exe"],
            startupinfo=startupinfo,
            text=True
        )
        if "DS4Windows.exe" in output:
            print("[Launcher] DS4Windows is already running.")
            return
    except Exception as e:
        print(f"[Launcher] Error checking running processes: {e}")
        
    # Launch DS4Windows in background
    try:
        print(f"[Launcher] Starting DS4Windows from {ds4_path}...")
        creationflags = 0
        if os.name == 'nt':
            creationflags = subprocess.DETACHED_PROCESS
        subprocess.Popen([ds4_path], creationflags=creationflags)
    except Exception as e:
        print(f"[Launcher] Failed to start DS4Windows: {e}")

def main():
    # Automatically start DS4Windows if needed
    launch_ds4windows()

    # Load configuration
    config = load_config()

    # Create Qt App
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Core Thread-Safe State Model
    control_state = ControlState()
    
    # Configure simulation mode from config
    control_state.drone_connected = not config.get("simulation_mode", True)

    # Initialize HUD Window
    main_window = MainWindow(control_state, config)
    main_window.show()

    # 1. Start Gamepad Polling Thread
    gamepad_thread = GamepadThread(
        control_state=control_state, 
        dead_zone=config.get("dead_zone", 0.1)
    )
    gamepad_thread.takeoff_triggered.connect(main_window.trigger_takeoff)
    gamepad_thread.rtl_triggered.connect(main_window.trigger_rtl)
    gamepad_thread.land_triggered.connect(main_window.trigger_land)
    gamepad_thread.set_home_triggered.connect(main_window.trigger_set_home)
    gamepad_thread.record_toggled.connect(main_window.toggle_recording)
    gamepad_thread.change_mode_triggered.connect(main_window.cycle_target_mode)
    gamepad_thread.confirm_mode_triggered.connect(main_window.handle_confirm_or_proceed)
    gamepad_thread.arm_disarm_triggered.connect(main_window.trigger_arm_disarm_toggle)
    gamepad_thread.cancel_triggered.connect(main_window.handle_cancel)
    gamepad_thread.kill_motors_triggered.connect(main_window.trigger_kill_motors)
    gamepad_thread.start()

    # 1b. Start DS4Windows Battery Telemetry Listener Thread
    ds4_battery_thread = DS4WindowsBatteryThread(
        control_state=control_state,
        port=config.get("ds4windows_osc_port", 9001)
    )
    ds4_battery_thread.start()

    # 2. Start UDP Control Command Sender Thread (50Hz)
    udp_thread = UDPControlThread(
        control_state=control_state,
        ip=config.get("raspberry_pi_ip", "192.168.50.1"),
        port=config.get("control_port", 5000),
        rate_hz=config.get("control_rate", 50),
        simulation_mode=config.get("simulation_mode", True)
    )
    udp_thread.start()

    # 3. Start Video Stream Receiver Thread
    video_thread = VideoReceiverThread(
        control_state=control_state,
        ip=config.get("raspberry_pi_ip", "192.168.50.1"),
        port=config.get("video_port", 5001),
        simulation_mode=config.get("simulation_mode", True)
    )
    video_thread.frame_ready.connect(main_window.on_frame_received)
    main_window.set_video_thread(video_thread)
    video_thread.start()

    # 4. Start Telemetry Processing/Simulation Thread
    telemetry_thread = TelemetryThread(
        control_state=control_state,
        simulation_mode=config.get("simulation_mode", True)
    )
    telemetry_thread.start()

    # Failsafe Handler check (can be periodically called or run in main timer)
    failsafe = FailsafeHandler(control_state)
    
    def periodic_safety_check():
        failsafe.check_failsafe()

    safety_timer = main_window.ui_timer
    safety_timer.timeout.connect(periodic_safety_check)

    # Execute Qt Application Loop
    exit_code = app.exec()

    # Safe stop of all threads on close
    print("Shutting down background services...")
    gamepad_thread.stop()
    ds4_battery_thread.stop()
    udp_thread.stop()
    video_thread.stop()
    telemetry_thread.stop()
    
    # Gracefully shut down DS4Windows
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ds4_path = os.path.join(base_dir, "DS4Windows.3.5.x64.DS4-Windows.com", "win-x64", "DS4Windows.exe")
    if os.path.exists(ds4_path):
        try:
            print("[Launcher] Shutting down DS4Windows...")
            # We run this using subprocess.Popen so the app exit is not blocked
            subprocess.Popen([ds4_path, "-command", "shutdown"])
        except Exception as e:
            print(f"[Launcher] Error shutting down DS4Windows: {e}")
            
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
