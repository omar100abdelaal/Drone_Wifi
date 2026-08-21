import socket
import json
import time
import os
from failsafe import RPiFailsafe
from uart_interface import SpeedyBeeUART

def load_config():
    default_config = {
        "control_port": 5000,
        "uart_port": "/dev/ttyAMA0",
        "uart_baud": 115200,
        "failsafe_timeout_ms": 300
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
    
    port = config.get("control_port", 5000)
    uart_port = config.get("uart_port", "/dev/ttyAMA0")
    uart_baud = config.get("uart_baud", 115200)
    failsafe_ms = config.get("failsafe_timeout_ms", 300)

    # Initialize components
    failsafe = RPiFailsafe(timeout_ms=failsafe_ms)
    uart = SpeedyBeeUART(port=uart_port, baudrate=uart_baud)

    # Create UDP Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    sock.settimeout(0.05) # Small timeout so we can run failsafe checks frequently

    print(f"UDP Control Receiver Listening on Port {port}...")
    
    last_seq = -1
    failsafe_triggered = False

    try:
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                packet = json.loads(data.decode('utf-8'))
                
                # Check sequence number to ignore late/out-of-order packets
                seq = packet.get("sequence", 0)
                if seq > last_seq:
                    last_seq = seq
                    
                    # Reset failsafe timer
                    failsafe.update_heartbeat()
                    failsafe_triggered = False
                    
                    # Read values
                    roll = packet.get("roll", 0.0)
                    pitch = packet.get("pitch", 0.0)
                    yaw = packet.get("yaw", 0.0)
                    throttle = packet.get("throttle", 0.0)
                    arm = packet.get("arm", False)
                    kill_motors = packet.get("kill_motors", False)
                    flight_mode = packet.get("flight_mode", "STABILIZE")
                    
                    # Forward controls to SpeedyBee only if failsafe is not active
                    if not failsafe.check_failsafe():
                        uart.send_controls(roll, pitch, yaw, throttle, arm, flight_mode, kill_motors)
                        
                    # Fetch real-time telemetry from UART and reply to sender
                    telemetry = uart.update_telemetry()
                    telemetry["timestamp"] = packet.get("timestamp", 0)
                    try:
                        resp_data = json.dumps(telemetry).encode('utf-8')
                        sock.sendto(resp_data, addr)
                    except Exception as e:
                        pass
                    
            except socket.timeout:
                # No packet received in the timeout window, proceed to check failsafe
                pass
            except Exception as e:
                print(f"Packet Processing Error: {e}")

            # Check failsafe timeout: if failsafe is active, release overrides to let Pixhawk trigger its internal failsafe
            if failsafe.check_failsafe():
                if not failsafe_triggered:
                    failsafe_triggered = True
                    uart.release_overrides()

            time.sleep(0.005) # Small yield

    except KeyboardInterrupt:
        print("\nStopping Control Receiver...")
    finally:
        sock.close()
        uart.close()

if __name__ == "__main__":
    main()
