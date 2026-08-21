import cv2
import numpy as np
import time
import math
import queue
import threading
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

class VideoReceiverThread(QThread):
    frame_ready = Signal(QImage)

    def __init__(self, control_state, ip, port, simulation_mode=True, parent=None):
        super().__init__(parent)
        self.control_state = control_state
        self.ip = ip
        self.port = port
        self.simulation_mode = simulation_mode
        self.running = False
        self.cap = None
        self.is_recording = False
        self.record_queue = None
        self.record_thread = None
        self.record_filename = ""
        self.record_start_time = 0.0

    def start_recording(self):
        if self.is_recording:
            return
        
        import os
        videos_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "videos")
        os.makedirs(videos_dir, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.record_filename = os.path.join(videos_dir, f"video_{timestamp}.avi")
        self.record_queue = queue.Queue(maxsize=150)
        self.is_recording = True
        self.record_start_time = time.time()
        
        # Start dedicated non-blocking background writer thread
        self.record_thread = threading.Thread(
            target=self._record_worker, 
            args=(self.record_filename, self.record_queue), 
            daemon=True
        )
        self.record_thread.start()
        print(f"[VideoRecorder] Started background recording thread: {self.record_filename}")

    def _record_worker(self, filename, record_queue):
        writer = None
        try:
            while True:
                item = record_queue.get()
                if item is None:
                    record_queue.task_done()
                    break
                
                if writer is None:
                    h, w = item.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*'XVID')
                    writer = cv2.VideoWriter(filename, fourcc, 25.0, (w, h))
                
                if writer is not None:
                    writer.write(item)
                record_queue.task_done()
        except Exception as e:
            print(f"[VideoRecorder] Error in background worker: {e}")
        finally:
            if writer is not None:
                writer.release()
                print(f"[VideoRecorder] Saved video file: {filename}")

    def stop_recording(self):
        if not self.is_recording:
            return
        self.is_recording = False
        if self.record_queue is not None:
            self.record_queue.put(None)
            self.record_queue = None
        print(f"[VideoRecorder] Stop recording signal sent.")

    def get_recording_elapsed(self):
        if self.is_recording:
            return int(time.time() - self.record_start_time)
        return 0

    def run(self):
        self.running = True
        sim_frame_count = 0
        failed_reads = 0
        stream_url = f"http://{self.ip}:{self.port}/video_feed"
        
        while self.running:
            if not self.simulation_mode:
                if self.cap is None or not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(stream_url)
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if not self.cap.isOpened():
                        self.control_state.video_live = False
                        frame = self.generate_sim_frame(sim_frame_count, no_signal=True)
                        sim_frame_count += 1
                        self.emit_frame(frame)
                        time.sleep(0.04)
                        continue
                
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    failed_reads = 0
                    self.control_state.video_live = True
                    self.emit_frame(frame)
                else:
                    failed_reads += 1
                    if failed_reads > 50: # Only release after 50 consecutive missed frames (>2 sec)
                        self.control_state.video_live = False
                        if self.cap is not None:
                            self.cap.release()
                            self.cap = None
                        frame = self.generate_sim_frame(sim_frame_count, no_signal=True)
                        sim_frame_count += 1
                        self.emit_frame(frame)
                    time.sleep(0.02)
            else:
                self.control_state.video_live = True
                frame = self.generate_sim_frame(sim_frame_count)
                sim_frame_count += 1
                self.emit_frame(frame)
                time.sleep(0.04)

        if self.cap is not None:
            self.cap.release()
            
        if self.record_queue is not None:
            self.record_queue.put(None)

    def emit_frame(self, frame):
        if self.is_recording and self.record_queue is not None:
            try:
                self.record_queue.put_nowait(frame.copy())
            except Exception:
                pass

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.frame_ready.emit(qt_img.copy())

    def generate_sim_frame(self, frame_num, no_signal=False):
        h, w = 1080, 1920
        frame = np.zeros((h, w, 3), dtype=np.uint8)

        if no_signal:
            noise = np.random.randint(20, 40, (h, w, 3), dtype=np.uint8)
            frame = cv2.addWeighted(frame, 0.0, noise, 1.0, 0)
        else:
            # 1. Sky Gradient (blue to light cyan)
            for y in range(0, 360):
                r = int(50 + (y / 360) * 110)
                g = int(100 + (y / 360) * 100)
                b = int(200 + (y / 360) * 45)
                frame[y, :] = (b, g, r)

            # 2. Water body (bottom half)
            for y in range(360, h):
                ratio = (y - 360) / (h - 360)
                r = int(20 + ratio * 20)
                g = int(80 - ratio * 30)
                b = int(120 - ratio * 40)
                frame[y, :] = (b, g, r)

            # 3. Draw mountains (overlapping filled polygons)
            # Far mountains
            pts1 = np.array([[0, 360], [150, 220], [350, 310], [500, 180], [700, 330], [900, 240], [1100, 320], [1280, 250], [1280, 360], [0, 360]], np.int32)
            cv2.fillPoly(frame, [pts1], (75, 90, 70))
            
            # Near mountains
            pts2 = np.array([[0, 360], [250, 280], [450, 340], [680, 260], [850, 350], [1050, 290], [1280, 360], [0, 360]], np.int32)
            cv2.fillPoly(frame, [pts2], (45, 65, 50))
            
            # Draw thin techgrid overlay
            grid_spacing = 60
            grid_mask = np.zeros_like(frame)
            for x in range(0, w, grid_spacing):
                cv2.line(grid_mask, (x, 0), (x, h), (100, 120, 140), 1)
            for y in range(0, h, grid_spacing):
                cv2.line(grid_mask, (0, y), (w, y), (100, 120, 140), 1)
            frame = cv2.addWeighted(frame, 0.94, grid_mask, 0.06, 0)

        cx, cy = w // 2, h // 2
        hud_green = (0, 220, 0)
        hud_white = (240, 240, 240)

        if no_signal:
            cv2.putText(frame, "VIDEO SIGNAL LOST", (cx - 160, cy - 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
            cv2.putText(frame, "CHECK WIFI & TRANSMITTER", (cx - 180, cy + 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            # 1. Top-Center Compass Heading Scale
            heading = int((frame_num * 0.1) % 360)
            cv2.line(frame, (cx - 300, 30), (cx + 300, 30), hud_white, 1)
            
            # Draw ticks
            for offset in range(-150, 151, 15):
                tick_heading = (heading + offset // 2) % 360
                tx = cx + offset
                
                # Big ticks for major headings, small ticks for others
                if tick_heading % 45 == 0:
                    cv2.line(frame, (tx, 30), (tx, 45), hud_white, 2)
                    labels = {0: "N", 45: "NE", 90: "E", 135: "SE", 180: "S", 225: "SW", 270: "W", 315: "NW"}
                    lbl = labels[tick_heading]
                    cv2.putText(frame, lbl, (tx - 10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.4, hud_white, 1)
                elif tick_heading % 15 == 0:
                    cv2.line(frame, (tx, 30), (tx, 38), hud_white, 1)
                    cv2.putText(frame, str(tick_heading), (tx - 10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)

            # Center compass marker arrow
            cv2.drawMarker(frame, (cx, 32), hud_green, cv2.MARKER_TILTED_CROSS, 8, 2)

            # 2. Top-Left Circular Radar/Heading Indicator
            rcx, rcy, rr = 100, 120, 50
            cv2.circle(frame, (rcx, rcy), rr, hud_green, 1)
            cv2.circle(frame, (rcx, rcy), int(rr*0.7), (0, 80, 0), 1)
            cv2.putText(frame, "N", (rcx - 5, rcy - rr - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, hud_white, 1)
            cv2.putText(frame, "S", (rcx - 5, rcy + rr + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, hud_white, 1)
            cv2.putText(frame, "W", (rcx - rr - 15, rcy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, hud_white, 1)
            cv2.putText(frame, "E", (rcx + rr + 5, rcy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, hud_white, 1)
            
            # Simulated heading indicator arrow
            heading_rad = math.radians(heading - 90)
            ax = int(rcx + rr * 0.8 * math.cos(heading_rad))
            ay = int(rcy + rr * 0.8 * math.sin(heading_rad))
            cv2.line(frame, (rcx, rcy), (ax, ay), hud_green, 2)
            cv2.drawMarker(frame, (ax, ay), hud_green, cv2.MARKER_TRIANGLE_UP, 6, 2)

            # 3. Left Altitude Scale Ladder
            lx = 50
            cv2.line(frame, (lx, cy - 150), (lx, cy + 150), hud_white, 1)
            for alt_val in range(0, 101, 25):
                # Map 0-100 to y position (cy+100 to cy-100)
                y_pos = cy + 100 - int(alt_val * 2)
                cv2.line(frame, (lx, y_pos), (lx + 8, y_pos), hud_white, 1)
                cv2.putText(frame, str(alt_val), (lx + 12, y_pos + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, hud_white, 1)
            
            # Moving level indicator (right-pointing triangle)
            sim_alt = 50 + int(math.sin(frame_num * 0.05) * 20)
            indicator_y = cy + 100 - int(sim_alt * 2)
            pt1 = (lx - 8, indicator_y - 6)
            pt2 = (lx - 8, indicator_y + 6)
            pt3 = (lx + 2, indicator_y)
            cv2.fillPoly(frame, [np.array([pt1, pt2, pt3], np.int32)], hud_green)

            # 4. Center Crosshair Reticle
            cv2.line(frame, (cx - 20, cy), (cx - 5, cy), hud_white, 1)
            cv2.line(frame, (cx + 5, cy), (cx + 20, cy), hud_white, 1)
            cv2.line(frame, (cx, cy - 20), (cx, cy - 5), hud_white, 1)
            cv2.line(frame, (cx, cy + 5), (cx, cy + 20), hud_white, 1)

        # Subtle CRT scanline effect
        scanline_gap = 4
        for y in range(0, h, scanline_gap):
            cv2.line(frame, (0, y), (w, y), (0, 0, 0), 1)

        return frame

    def stop(self):
        self.running = False
        self.wait()
