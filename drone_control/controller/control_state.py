import threading
import time

class ControlState:
    def __init__(self):
        self._lock = threading.Lock()
        self.roll = 0.0      # -1.0 to 1.0
        self.pitch = 0.0     # -1.0 to 1.0
        self.yaw = 0.0       # -1.0 to 1.0
        self.throttle = 0.0  # 0.0 to 1.0
        self.arm = False
        self.kill_motors = False
        self.flight_mode = "STABILIZE"
        self.sequence = 0
        self.session_id = int(time.time() * 1000)
        self.gamepad_connected = False
        self.drone_connected = False
        self.video_live = False
        self.wifi_signal = 0
        self.battery = 0.0
        self.latency = 0
        self.last_telemetry_time = 0.0

        # New telemetry fields
        self.battery_voltage = 0.0          # in Volts
        self.gps_status = "NO SIGNAL"       # GPS status text
        self.num_satellites = 0             # number of satellites
        self.altitude = 0.0                 # in meters
        self.ground_speed = 0.0              # in m/s
        self.pi_pixhawk_connected = False    # Connection between Pi and Pixhawk
        self.failsafe_active = False         # Failsafe status
        self.home_position = {"lat": 0.0, "lon": 0.0, "alt": 0.0} # Home coordinates
        self.throttle_input = 0.0            # Real-time throttle stick/key deflection rate (-1.0 to 1.0)
        self.gamepad_battery = "unknown"     # Gamepad battery status
        self.ds4_battery_pct = None          # Gamepad exact battery percentage from DS4Windows
        self.landing_success = False         # Landing success banner flag

    def update_axes(self, roll, pitch, yaw, throttle, throttle_input=0.0):
        with self._lock:
            self.roll = roll
            self.pitch = pitch
            self.yaw = yaw
            
            if self.arm:
                self.throttle = max(0.14, min(1.0, throttle))
            else:
                self.throttle = max(0.0, min(1.0, throttle))
                
            self.throttle_input = throttle_input

    def toggle_arm(self):
        with self._lock:
            self.arm = not self.arm
            if self.arm:
                self.throttle = 0.14
            else:
                self.throttle = 0.0
            return self.arm

    def set_arm(self, armed):
        with self._lock:
            if self.arm != armed:
                self.arm = armed
                if self.arm:
                    self.throttle = 0.14
                    self.kill_motors = False # Reset kill flag on arm
                else:
                    self.throttle = 0.0

    def trigger_kill_motors(self):
        with self._lock:
            self.kill_motors = True
            self.arm = False
            self.throttle = 0.0

    def set_flight_mode(self, mode):
        with self._lock:
            self.flight_mode = mode

    def get_packet(self):
        with self._lock:
            self.sequence += 1
            return {
                "roll": round(self.roll, 3),
                "pitch": round(self.pitch, 3),
                "yaw": round(self.yaw, 3),
                "throttle": round(self.throttle, 3),
                "arm": self.arm,
                "kill_motors": self.kill_motors,
                "flight_mode": self.flight_mode,
                "sequence": self.sequence,
                "session_id": self.session_id,
                "timestamp": int(time.time() * 1000)
            }

    def get_ui_state(self):
        with self._lock:
            return {
                "roll": self.roll,
                "pitch": self.pitch,
                "yaw": self.yaw,
                "throttle": self.throttle,
                "throttle_input": self.throttle_input,
                "arm": self.arm,
                "kill_motors": self.kill_motors,
                "flight_mode": self.flight_mode,
                "gamepad_connected": self.gamepad_connected,
                "drone_connected": self.drone_connected,
                "video_live": self.video_live,
                "wifi_signal": self.wifi_signal,
                "battery": self.battery,
                "latency": self.latency,
                # New fields
                "battery_voltage": self.battery_voltage,
                "gps_status": self.gps_status,
                "num_satellites": self.num_satellites,
                "altitude": self.altitude,
                "ground_speed": self.ground_speed,
                "pi_pixhawk_connected": self.pi_pixhawk_connected,
                "failsafe_active": self.failsafe_active,
                "home_position": self.home_position,
                "gamepad_battery": self.gamepad_battery,
                "ds4_battery_pct": self.ds4_battery_pct,
                "landing_success": self.landing_success
            }
