#!/bin/bash
# Raspberry Pi Drone Autostart Launcher Script

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "========================================="
echo "   DRONE RASPBERRY PI AUTOSTART LAUNCHER"
echo "========================================="

# Start control_receiver.py in background
"$DIR/.venv/bin/python3" control_receiver.py &
PID_CONTROL=$!

# Start video_streamer.py in background
"$DIR/.venv/bin/python3" video_streamer.py &
PID_VIDEO=$!

echo "Control Receiver running (PID: $PID_CONTROL)"
echo "Video Streamer running (PID: $PID_VIDEO)"

# Keep launcher active and wait for both processes
wait $PID_CONTROL $PID_VIDEO
