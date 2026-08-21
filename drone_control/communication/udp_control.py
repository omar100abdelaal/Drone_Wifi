import socket
import json
import time
from PySide6.QtCore import QThread, Signal

class UDPControlThread(QThread):
    packet_sent = Signal(dict)

    def __init__(self, control_state, ip, port, rate_hz=50, simulation_mode=True, parent=None):
        super().__init__(parent)
        self.control_state = control_state
        self.ip = ip
        self.port = port
        self.interval = 1.0 / rate_hz
        self.simulation_mode = simulation_mode
        self.running = False
        
        # Create UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set socket timeout for non-blocking if needed
        self.sock.settimeout(0.1)

    def run(self):
        self.running = True
        while self.running:
            start_time = time.time()
            
            # Retrieve the latest control state packet
            packet = self.control_state.get_packet()
            
            # If neither gamepad is connected nor keyboard is active, enforce safety default values for axes
            if not self.control_state.gamepad_connected and not getattr(self.control_state, "keyboard_active", False):
                packet["roll"] = 0.0
                packet["pitch"] = 0.0
                packet["yaw"] = 0.0
                packet["throttle"] = 0.0


            # JSON encode
            data = json.dumps(packet).encode('utf-8')
            
            # Send packet
            try:
                target_ip = "127.0.0.1" if self.simulation_mode else self.ip
                self.sock.sendto(data, (target_ip, self.port))
                self.packet_sent.emit(packet)
                
                # Receive telemetry reply (non-blocking)
                try:
                    self.sock.settimeout(0.015)  # 15ms timeout for telemetry response
                    reply_data, _ = self.sock.recvfrom(1024)
                    telemetry = json.loads(reply_data.decode('utf-8'))
                    
                    t_stamp = telemetry.get("timestamp", 0)
                    if t_stamp > 0:
                        latency = int(time.time() * 1000) - t_stamp
                        self.control_state.latency = max(0, latency)
                    
                    self.control_state.altitude = telemetry.get("altitude", 0.0)
                    self.control_state.battery_voltage = telemetry.get("battery_voltage", 0.0)
                    # Convert percent to battery status percentage
                    pct = telemetry.get("battery_percent", 0)
                    self.control_state.battery = float(pct) if pct is not None else 0.0
                    self.control_state.pi_pixhawk_connected = telemetry.get("pi_pixhawk_connected", False)
                    self.control_state.drone_connected = True
                    self.control_state.last_telemetry_time = time.time()
                except socket.timeout:
                    # Packet drop or Pi offline
                    pass
                except Exception as e:
                    print(f"Telemetry Receive Error: {e}")
            except Exception as e:
                print(f"UDP Send Error: {e}")

            # Sleep to maintain frequency (50Hz)
            elapsed = time.time() - start_time
            sleep_time = max(0.001, self.interval - elapsed)
            time.sleep(sleep_time)

    def stop(self):
        self.running = False
        self.wait()
        try:
            self.sock.close()
        except:
            pass
