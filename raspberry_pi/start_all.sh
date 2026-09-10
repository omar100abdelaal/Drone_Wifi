#!/bin/bash
# Raspberry Pi Drone Autostart Launcher Script

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "========================================="
echo "   DRONE RASPBERRY PI AUTOSTART LAUNCHER"
echo "========================================="

# Determine Python binary (.venv if present, otherwise system python3)
if [ -f "$DIR/.venv/bin/python3" ]; then
    PY_BIN="$DIR/.venv/bin/python3"
else
    PY_BIN="python3"
fi

# Start control_receiver.py in background
"$PY_BIN" control_receiver.py &
PID_CONTROL=$!

# Start video_streamer.py in background
"$PY_BIN" video_streamer.py &
PID_VIDEO=$!

echo "Control Receiver running (PID: $PID_CONTROL)"
echo "Video Streamer running (PID: $PID_VIDEO)"

# Keep launcher active and wait for both processes
wait $PID_CONTROL $PID_VIDEO
