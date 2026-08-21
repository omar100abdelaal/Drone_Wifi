import socket
import struct
import time
from PySide6.QtCore import QThread

class DS4WindowsBatteryThread(QThread):
    def __init__(self, control_state, port=9002, parent=None):
        super().__init__(parent)
        self.control_state = control_state
        self.port = port
        self.running = False
        self.last_update_time = 0.0

    def run(self):
        self.running = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            sock.bind(("127.0.0.1", self.port))
            print(f"[OSC Battery Reader] Listening for DS4Windows telemetry on UDP port {self.port}...")
        except Exception as e:
            print(f"[OSC Battery Reader] Error binding to port {self.port}: {e}")
            self.control_state.ds4_battery_pct = None
            sock.close()
            return

        sock.settimeout(1.0) # 1 second timeout for socket checks

        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                address, val = self.parse_osc_message(data)
                if address and "/ds4windows/monitor/" in address and "/battery" in address:
                    if isinstance(val, (int, float)):
                        # DS4Windows sends battery level as an integer or float between 0 and 100
                        self.control_state.ds4_battery_pct = int(val)
                        self.last_update_time = time.time()
            except socket.timeout:
                pass
            except Exception as e:
                print(f"[OSC Battery Reader] Error: {e}")

            # If no telemetry received for 1 hour, mark as unavailable
            if time.time() - self.last_update_time > 3600.0:
                self.control_state.ds4_battery_pct = None

        sock.close()

    def stop(self):
        self.running = False
        self.wait()

    def parse_osc_message(self, data):
        """
        Parses a basic OSC message without external library dependency.
        Format: [Address (null-padded string)][Type Tag (null-padded string beginning with ',')][Arguments]
        """
        try:
            # Address is null-terminated
            null_idx = data.find(b'\x00')
            if null_idx == -1:
                return None, None
            address = data[:null_idx].decode('utf-8')
            
            # Align address boundary to 4-byte index
            idx = (null_idx + 4) & ~3
            
            if idx >= len(data):
                return address, None
                
            # Type tag must start with a comma
            if data[idx:idx+1] != b',':
                return address, None
                
            null_idx2 = data.find(b'\x00', idx)
            if null_idx2 == -1:
                return address, None
            type_tag = data[idx:null_idx2].decode('utf-8')
            
            # Align type tag boundary to 4-byte index
            idx = (null_idx2 + 4) & ~3
            
            if idx >= len(data):
                return address, None
                
            # Parse argument based on type tag: ',i' is a 32-bit big-endian integer
            if ",i" in type_tag:
                if idx + 4 <= len(data):
                    val = struct.unpack(">i", data[idx:idx+4])[0]
                    return address, val
            elif ",f" in type_tag:
                if idx + 4 <= len(data):
                    val = struct.unpack(">f", data[idx:idx+4])[0]
                    return address, val
        except Exception:
            pass
        return None, None
