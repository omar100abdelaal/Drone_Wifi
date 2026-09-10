import time
import threading
from pymavlink import mavutil

class SpeedyBeeUART:
    def __init__(self, port="/dev/ttyAMA0", baudrate=115200, verbose=True):
        self.port = port
        self.baudrate = baudrate
        self.verbose = verbose
        self.mav_connection = None
        self.current_armed = False
        self.current_kill_motors = False
        self.current_flight_mode = "STABILIZE"
        self.latest_battery_voltage = 0.0
        self.latest_battery_percent = 0
        self.latest_altitude = 0.0
        self._heartbeat_thread = None
        self._heartbeat_running = False
        
        # Retry loop: keep trying until we get a heartbeat.
        # This handles the case where the Pi boots faster than the SpeedyBee
        # (e.g. after a power cycle), which would previously cause a 3-second
        # timeout and then fall into "DRY-RUN mode" permanently.
        max_attempts = 30  # 30 × 5 seconds = up to 2.5 minutes
        attempt = 0
        connected = False
        while attempt < max_attempts and not connected:
            try:
                attempt += 1
                print(f"[MAVLink] Attempt {attempt}/{max_attempts}: Connecting on {self.port} at {self.baudrate} baud...")
                self.mav_connection = mavutil.mavlink_connection(self.port, baud=self.baudrate)
                hb = self.mav_connection.wait_heartbeat(timeout=5.0)
                if hb is not None:
                    print("[MAVLink] Heartbeat received! Flight controller connected.")
                    self._start_heartbeat()
                    connected = True
                else:
                    print("[MAVLink] No heartbeat yet — retrying in 2 seconds...")
                    import time as _time
                    _time.sleep(2.0)
            except Exception as e:
                print(f"[MAVLink] Connection error (attempt {attempt}): {e} — retrying in 2 seconds...")
                import time as _time
                _time.sleep(2.0)
        if not connected:
            print(f"[MAVLink] WARNING: Could not connect after {max_attempts} attempts. Running in DRY-RUN mode.")

    def _start_heartbeat(self):
        """Start a background thread that sends MAVLink HEARTBEAT at 1Hz.
        ArduPilot requires periodic heartbeats from companion computers
        to recognize them as valid GCS sources for RC overrides."""
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        print("[MAVLink] Heartbeat sender started (1Hz)")

    def _heartbeat_loop(self):
        while self._heartbeat_running and self.mav_connection:
            try:
                self.mav_connection.mav.heartbeat_send(
                    mavutil.mavlink.MAV_TYPE_GCS,            # We are a ground control station
                    mavutil.mavlink.MAV_AUTOPILOT_INVALID,   # No autopilot on our side
                    0, 0, 0
                )
            except Exception:
                pass
            time.sleep(1.0)

    def update_telemetry(self):
        if not self.mav_connection:
            return {
                "battery_voltage": 0.0,
                "battery_percent": 0,
                "altitude": 0.0,
                "pi_pixhawk_connected": False
            }
        
        try:
            while True:
                msg = self.mav_connection.recv_match(blocking=False)
                if not msg:
                    break
                
                msg_type = msg.get_type()
                if msg_type == 'SYS_STATUS':
                    self.latest_battery_voltage = round(msg.voltage_battery / 1000.0, 2)
                    self.latest_battery_percent = msg.battery_remaining if msg.battery_remaining != -1 else 0
                elif msg_type == 'VFR_HUD':
                    self.latest_altitude = round(msg.alt, 1)
                elif msg_type == 'GLOBAL_POSITION_INT':
                    self.latest_altitude = round(msg.relative_alt / 1000.0, 1)
                elif msg_type == 'STATUSTEXT':
                    print(f"[ArduPilot Message] {msg.text}")
        except Exception as e:
            print(f"Error reading MAVLink telemetry: {e}")
            
        return {
            "battery_voltage": self.latest_battery_voltage,
            "battery_percent": self.latest_battery_percent,
            "altitude": self.latest_altitude,
            "pi_pixhawk_connected": True
        }


    def send_controls(self, roll, pitch, yaw, throttle, armed, flight_mode, kill_motors=False):
        # Map values from normalized [-1.0, 1.0] or [0.0, 1.0] to RC channel values [1000, 2000]
        # (1500 is midpoint)
        rc_roll = int(1500 + (roll * 500))
        rc_pitch = int(1500 + (pitch * 500))
        rc_yaw = int(1500 + (yaw * 500))
        rc_throttle = int(1000 + (throttle * 1000))
        
        # 0. Handle Kill Motors (Force Disarm)
        if kill_motors and not self.current_kill_motors:
            self.current_kill_motors = True
            self.current_armed = False # Ensure armed state reflects disarm
            if self.mav_connection:
                try:
                    self.mav_connection.mav.command_long_send(
                        self.mav_connection.target_system,
                        self.mav_connection.target_component,
                        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                        0,
                        0,      # parameter 1: 0=disarm
                        21196,  # parameter 2: force
                        0, 0, 0, 0, 0
                    )
                    print("[MAVLink Command] Sent FORCE DISARM (KILL MOTORS) command to ArduPilot")
                except Exception as e:
                    print(f"MAVLink Kill Motors Error: {e}")
            else:
                print("[DRY-RUN MAVLink] FORCE DISARM (KILL MOTORS) command sent")
        elif not kill_motors and self.current_kill_motors:
            self.current_kill_motors = False

        # 1. Handle Arming/Disarming (Only send command on state change)
        if armed != self.current_armed and not kill_motors:
            self.current_armed = armed
            if self.mav_connection:
                try:
                    # MAVLink arm/disarm command
                    self.mav_connection.mav.command_long_send(
                        self.mav_connection.target_system,
                        self.mav_connection.target_component,
                        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                        0,
                        1 if armed else 0, # parameter 1: 1=arm, 0=disarm
                        0, 0, 0, 0, 0, 0
                    )
                    action = "ARM" if armed else "DISARM"
                    print(f"[MAVLink Command] Sent {action} command to ArduPilot")
                except Exception as e:
                    print(f"MAVLink Arm/Disarm Error: {e}")
            else:
                action = "ARM" if armed else "DISARM"
                print(f"[DRY-RUN MAVLink] {action} command sent")

        # 2. Handle Flight Mode changes (Only send command on state change)
        if flight_mode != self.current_flight_mode:
            self.current_flight_mode = flight_mode
            if self.mav_connection:
                try:
                    # Map standard flight modes to ArduPilot Copter mode IDs
                    # STABILIZE = 0, ALT_HOLD = 2, LOITER = 5, RTL = 6, LAND = 9
                    mode_mapping = {
                        "STABILIZE": 0,
                        "ALT_HOLD": 2,
                        "LOITER": 5,
                        "RTL": 6,
                        "LAND": 9
                    }
                    mode_id = mode_mapping.get(flight_mode, 0)
                    
                    self.mav_connection.mav.set_mode_send(
                        self.mav_connection.target_system,
                        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                        mode_id
                    )
                    print(f"[MAVLink Command] Set flight mode to {flight_mode} (ID: {mode_id})")
                except Exception as e:
                    print(f"MAVLink Set Mode Error: {e}")
            else:
                print(f"[DRY-RUN MAVLink] Set flight mode to {flight_mode}")

        # 3. Send RC overrides (Roll, Pitch, Throttle, Yaw overridden on CH1, CH2, CH3, CH4)
        if self.mav_connection:
            try:
                # 65535 means ignore/no override for unused channels in MAVLink spec
                self.mav_connection.mav.rc_channels_override_send(
                    self.mav_connection.target_system,
                    self.mav_connection.target_component,
                    rc_roll,      # CH1: Roll
                    rc_pitch,     # CH2: Pitch
                    rc_throttle,  # CH3: Throttle
                    rc_yaw,       # CH4: Yaw
                    65535, 65535, 65535, 65535  # CH5-CH8: No override
                )
                if self.verbose:
                    print(f"[MAVLink RC OVERRIDE] ROL:{rc_roll} | PIT:{rc_pitch} | THR:{rc_throttle} | YAW:{rc_yaw}")
            except Exception as e:
                print(f"MAVLink RC Override Error: {e}")
        else:
            # Dry-run logging for verification
            print(f"[DRY-RUN MAVLink RC] ROL:{rc_roll} | PIT:{rc_pitch} | THR:{rc_throttle} | YAW:{rc_yaw}")

    def release_overrides(self):
        if self.mav_connection:
            try:
                self.mav_connection.mav.rc_channels_override_send(
                    self.mav_connection.target_system,
                    self.mav_connection.target_component,
                    65535, 65535, 65535, 65535, 65535, 65535, 65535, 65535 # 65535 releases override control
                )
                if self.verbose:
                    print("[MAVLink Failsafe] Released all RC overrides to flight controller.")
            except Exception as e:
                print(f"MAVLink Release Overrides Error: {e}")

    def close(self):
        # Stop heartbeat thread first
        self._heartbeat_running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2.0)
        if self.mav_connection:
            try:
                # Release all RC overrides before closing
                self.release_overrides()
                self.mav_connection.close()
                print("MAVLink connection closed.")
            except:
                pass
            
    def send_disarm_failsafe(self):
        # Force all RC overrides back to center/idle and disarm
        self.send_controls(0.0, 0.0, 0.0, 0.0, False, "STABILIZE")
