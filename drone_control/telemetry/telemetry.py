import time
import random
from PySide6.QtCore import QThread

class TelemetryThread(QThread):
    def __init__(self, control_state, simulation_mode=True, parent=None):
        super().__init__(parent)
        self.control_state = control_state
        self.simulation_mode = simulation_mode
        self.running = False

    def run(self):
        self.running = True
        
        # Start at configured battery or default 87%
        battery = 87.0
        altitude = 120.0
        
        while self.running:
            if self.simulation_mode:
                # Slowly drain battery to simulate action (0.01% per cycle)
                battery -= 0.01
                if battery < 5:
                    battery = 100.0 # reset simulation battery
                
                self.control_state.battery = round(battery, 1)
                # Volts = ~battery percentage * scale (e.g. 10.5V to 12.6V for a 3S LiPo battery)
                self.control_state.battery_voltage = round(10.5 + (battery / 100.0) * 2.1, 2)
                
                # Mock a small ping/latency
                self.control_state.latency = random.randint(5, 15)
                # Mock WiFi signal (e.g. fluctuating slightly between 95 and 100%)
                self.control_state.wifi_signal = random.randint(95, 100)
                # Drone connection status in simulation mode is simulated as True
                self.control_state.drone_connected = True
                self.control_state.pi_pixhawk_connected = True
                self.control_state.gps_status = "3D FIX"
                self.control_state.num_satellites = random.randint(10, 15)
                
                # Altitude fluctuates slightly around target / flight behavior
                if self.control_state.arm:
                    if self.control_state.flight_mode == "LAND":
                        # Landing sequence: descend to 0.0
                        altitude = max(0.0, altitude - 5.0)
                        self.control_state.ground_speed = max(0.0, self.control_state.ground_speed - 1.0)
                        if altitude <= 0.0:
                            # Auto-disarm on touchdown!
                            self.control_state.set_arm(False)
                            self.control_state.landing_success = True
                    else:
                        altitude += random.uniform(-0.5, 0.6)
                        self.control_state.ground_speed = round(random.uniform(3.0, 8.0), 1)
                        self.control_state.landing_success = False
                else:
                    altitude = max(0.0, altitude - 1.0)
                    self.control_state.ground_speed = 0.0
                    # Keep landing success visible if we just finished landing and are disarmed
                    if self.control_state.flight_mode != "LAND":
                        self.control_state.landing_success = False
                self.control_state.altitude = round(altitude, 1)
                self.control_state.failsafe_active = False
            else:
                # Check if telemetry has timed out (1.5 seconds)
                elapsed = time.time() - getattr(self.control_state, "last_telemetry_time", 0.0)
                if elapsed > 1.5:
                    self.control_state.altitude = 0.0
                    self.control_state.battery_voltage = 0.0
                    self.control_state.battery = 0.0
                    self.control_state.latency = 0
                    self.control_state.drone_connected = False
                    self.control_state.pi_pixhawk_connected = False
                    self.control_state.gps_status = "NO SIGNAL"
                    self.control_state.num_satellites = 0
                    self.control_state.ground_speed = 0.0

            time.sleep(1.0)

    def stop(self):
        self.running = False
        self.wait()
