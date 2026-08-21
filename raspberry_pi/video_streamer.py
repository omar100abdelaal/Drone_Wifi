import cv2
import time
import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# Global camera frame variable
lock = threading.Lock()
latest_frame = None

def load_config():
    default_config = {
        "video_port": 5001,
        "video_width": 1920,
        "video_height": 1080,
        "video_quality": 85
    }
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return default_config

class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global latest_frame
        if self.path == '/video_feed':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    with lock:
                        if latest_frame is None:
                            time.sleep(0.01)
                            continue
                        img_bytes = latest_frame
                    
                    self.wfile.write(b'--frame\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(img_bytes))
                    self.end_headers()
                    self.wfile.write(img_bytes)
                    self.wfile.write(b'\r\n')
                    time.sleep(0.03) # High FPS stream (~30 FPS)
            except Exception as e:
                print(f"Client disconnected: {self.client_address} ({e})")
        else:
            self.send_error(404)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    allow_reuse_address = True

def camera_capture_loop(config):
    global latest_frame
    width = config.get("video_width", 1920)
    height = config.get("video_height", 1080)
    quality = config.get("video_quality", 75)

    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    
    # Configure camera for 1080p HD capture with MJPEG hardware decoding for max FPS and sharpness
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap.isOpened():
        print("Error: Could not open camera. Video stream will serve test pattern.")
        # Create a mock test pattern
        h, w = 1080, 1920
        while True:
            frame = cv2.putText(
                cv2.rectangle(cv2.merge([cv2.merge([
                    # dummy static
                    cv2.randu(cv2.UMat(h, w, cv2.CV_8UC1), 0, 255).get()
                ]*3)]), (10, 10), (w-10, h-10), (0, 255, 0), 2),
                "RASPBERRY PI VIDEO STREAMER [1080p HD]", (50, 180),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2
            )
            ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            if ret:
                with lock:
                    latest_frame = jpeg.tobytes()
            time.sleep(0.03)

    print(f"Camera opened successfully: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} @ {int(cap.get(cv2.CAP_PROP_FPS))} FPS (Quality: {quality})")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            
            # Encode frame to high quality JPEG
            ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            if ret:
                with lock:
                    latest_frame = jpeg.tobytes()
            time.sleep(0.005) # Small yield
    finally:
        cap.release()

def main():
    config = load_config()
    port = config.get("video_port", 5001)

    # Start camera capture thread
    cap_thread = threading.Thread(target=camera_capture_loop, args=(config,), daemon=True)
    cap_thread.start()

    server_address = ('', port)
    try:
        server = ThreadedHTTPServer(server_address, StreamingHandler)
        print(f"Video Stream Server started on port {port}...")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Video Server...")
        server.server_close()

if __name__ == "__main__":
    main()
