# Drone Control Center - Graduation Project

A high-performance, low-latency, native Python desktop control interface for flight management, controller visualization, and real-time FPV video stream decoding.

---

## 📂 Project Structure

```
drone_wifi/
├── drone_control/             # Laptop Application (Windows)
│   ├── main.py                # Entrypoint
│   ├── config.json            # Configuration file
│   ├── requirements.txt       # GUI, Gamepad & Video Dependencies
│   ├── ui/                    # Qt UI Widgets
│   │   ├── main_window.py     # HUD overlay & layouts
│   │   ├── video_widget.py    # 16:9 aspect-ratio video renderer
│   │   ├── joystick_widget.py # Semi-transparent visual joysticks
│   │   └── status_bar.py      # Top metrics bar
│   ├── controller/            # Gamepad handling
│   │   ├── gamepad.py         # Pygame joystick interface
│   │   └── control_state.py   # Thread-safe telemetry state
│   ├── communication/         # Networks
│   │   ├── udp_control.py     # 50Hz control sender
│   │   └── video_receiver.py  # OpenCV MJPEG downloader
│   ├── safety/
│   │   └── failsafe.py        # Disarm & timeout check
│   └── telemetry/
│       └── telemetry.py       # Battery & latency simulation
│
├── raspberry_pi/              # Companion Drone software
│   ├── control_receiver.py    # 50Hz UDP listener -> UART Writer
│   ├── video_streamer.py      # Independent Camera server
│   ├── uart_interface.py      # MSP (MultiWii Serial Protocol)
│   ├── failsafe.py            # 300ms network timeout failsafe
│   ├── config.json            # Pi Port configurations
│   └── requirements.txt       # Pi system libraries
│
└── run_app.bat                # Double-click launcher for Windows
```

---

## 🚀 Laptop Launch Instructions (Windows)

1. Connect your USB game controller to the laptop.
2. Double-click `run_app.bat` in the project root.
   - The batch script automatically updates `pip`, checks and installs all dependencies (`PySide6`, `opencv-python`, `pygame`, `pyserial`), and starts the application.
3. The UI will start directly into **Simulation Mode** (configured by default in `config.json`).

---

## 🎮 Gamepad Mapping & Controls

- **Left Joystick**:
  - Up / Down ➡️ **Throttle** (0% to 100%)
  - Left / Right ➡️ **Yaw** (Left/Right rotation)
- **Right Joystick**:
  - Up / Down ➡️ **Pitch** (Forward/Backward tilt)
  - Left / Right ➡️ **Roll** (Left/Right tilt)
- **Arm / Disarm Toggle**: Button A (Xbox) / Cross (PlayStation)
- **Flight Mode Cycle**: Button B (Xbox) / Circle (PlayStation)

---

## 💻 Simulation Mode Testing

When `"simulation_mode": true` is set in `drone_control/config.json`:
1. The app renders a fully simulated telemetry stream.
2. An FPV flight horizon overlays a simulated background to test responsiveness.
3. The virtual joysticks smoothly mimic physical USB joystick adjustments.
4. Active control packets are dispatched over UDP to `127.0.0.1` so you can verify outputs using any local UDP socket listener.

To change configuration properties, open `drone_control/config.json` and adjust:
- `raspberry_pi_ip`: Target Wi-Fi IP of the drone.
- `simulation_mode`: Set to `false` for real flight control over Wi-Fi.

---

## 🍓 Raspberry Pi 4 Setup & Launch

1. Clone or copy the `raspberry_pi` folder to the Raspberry Pi.
2. Connect your USB Web camera to one of the Pi USB ports.
3. Connect the Pi UART TX/RX pins (Pins 8/10 - GPIO 14/15) to a spare UART on the SpeedyBee F405 flight controller.
4. SSH into the Pi and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the video streamer (ideally inside a `tmux` or as a background service):
   ```bash
   python video_streamer.py
   ```
6. Run the control receiver:
   ```bash
   python control_receiver.py
   ```

---

## 📡 Communication Protocols

### 1. Control Protocol (UDP Port 5000)
Small, fast JSON telemetry packets are transmitted at **50Hz** (every 20ms) from the laptop to the Raspberry Pi.

```json
{
  "roll": 0.05,
  "pitch": -0.12,
  "yaw": 0.0,
  "throttle": 0.45,
  "arm": false,
  "flight_mode": "STABILIZE",
  "sequence": 1054,
  "timestamp": 1691684362125
}
```

### 2. Video Protocol (HTTP Port 5001)
Video is streamed as a low-latency MJPEG stream over HTTP (`http://<pi_ip>:5001/video_feed`). This method is handled on a dedicated connection path in the desktop application using OpenCV, preventing high-bandwidth video packets from causing latency jitter on the UDP control commands channel.

---

## ⚠️ Safety Measures & Failsafe

- **Default State**: Application launches with state forced to **DISARMED**.
- **Gamepad Loss**: If the physical gamepad becomes unplugged, the laptop immediately disarms and stops sending commands.
- **Connection Timeout**: If the Raspberry Pi receiver detects no incoming UDP packets for **300ms**, it triggers an emergency failsafe, forcing disarming values to the SpeedyBee UART.
- **Flight Stabilization**: SpeedyBee remains fully responsible for safety-critical IMU processing, motor mixing, and sensor management.
