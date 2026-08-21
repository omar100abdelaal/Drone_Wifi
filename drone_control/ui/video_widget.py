import os
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QImage, QColor, QFont, QPen, QBrush
from PySide6.QtCore import Qt, QRect, QPoint

class VideoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.video_live = False
        self.state = {}
        
        # Load landing/offline image
        self.landing_image = None
        img_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "image.png")
        if os.path.exists(img_path):
            self.landing_image = QImage(img_path)

    def set_image(self, qt_image):
        self.image = qt_image
        self.update()

    def set_video_live(self, live):
        self.video_live = live
        self.update()

    def set_state(self, state):
        self.state = state
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        
        # Manually paint background color to avoid stylesheet override issues
        painter.fillRect(0, 0, w, h, QColor(5, 5, 5))
        
        # Calculate aspect ratio 16:9 bounding box
        target_ratio = 16.0 / 9.0
        current_ratio = w / h

        if current_ratio > target_ratio:
            # Widget is wider than 16:9, scale by width to fill height/width (cropping top/bottom)
            new_w = w
            new_h = int(w / target_ratio)
        else:
            # Widget is taller than 16:9, scale by height to fill height/width (cropping sides)
            new_h = h
            new_w = int(h * target_ratio)

        # Center target rect (will extend beyond bounds to crop)
        x = (w - new_w) // 2
        y = (h - new_h) // 2
        target_rect = QRect(x, y, new_w, new_h)

        if self.video_live and self.image and not self.image.isNull():
            # Scale and draw the received video QImage preserving exact aspect ratio (no stretching)
            scaled_img = self.image.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_x = (w - scaled_img.width()) // 2
            img_y = (h - scaled_img.height()) // 2
            painter.drawImage(img_x, img_y, scaled_img)
        elif self.landing_image and not self.landing_image.isNull():
            # Scale and draw the landing/offline image to fill the target rect
            scaled_img = self.landing_image.scaled(target_rect.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawImage(target_rect.topLeft(), scaled_img)
            
            # Draw HUD overlays on top of the landing image (using visible viewport bounds)
            self.draw_hud(painter, QRect(0, 0, w, h))
        else:
            # Draw standard FPV statics/placeholder filling the widget
            painter.fillRect(QRect(0, 0, w, h), QColor(10, 12, 15))
            
            # Draw retro framing
            painter.setPen(QColor(240, 240, 240, 100))
            painter.drawRect(0, 0, w - 1, h - 1)
            
            # Centered Text
            painter.setPen(QColor(255, 51, 51))
            painter.setFont(QFont("Consolas", 18, QFont.Bold))
            painter.drawText(QRect(0, 0, w, h), Qt.AlignCenter, "NO VIDEO SIGNAL\n[SIMULATION / OFFLINE]")

        # Draw landing success overlay if active
        if self.state.get("landing_success", False):
            self.draw_landing_success_banner(painter, w, h)

    def draw_hud(self, painter, rect):
        w, h = rect.width(), rect.height()
        rx, ry = rect.x(), rect.y()
        cx, cy = rx + w // 2, ry + h // 2
        
        hud_green = QColor(0, 220, 0)
        hud_white = QColor(240, 240, 240, 220)
        hud_gray = QColor(180, 180, 180, 150)
        
        # 2. Top-Left Circular Radar/Compass
        rcx, rcy, rr = rx + 90, ry + 90, 45
        painter.setPen(QPen(hud_green, 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(rcx - rr, rcy - rr, rr * 2, rr * 2)
        painter.setPen(QPen(QColor(0, 100, 0, 120), 1))
        painter.drawEllipse(rcx - int(rr * 0.7), rcy - int(rr * 0.7), int(rr * 0.7 * 2), int(rr * 0.7 * 2))
        
        # Labels N, E, S, W
        painter.setPen(hud_white)
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(rcx - 10, rcy - rr - 15, 20, 12, Qt.AlignCenter, "N")
        painter.drawText(rcx - 10, rcy + rr + 3, 20, 12, Qt.AlignCenter, "S")
        painter.drawText(rcx - rr - 18, rcy - 6, 15, 12, Qt.AlignCenter, "W")
        painter.drawText(rcx + rr + 3, rcy - 6, 15, 12, Qt.AlignCenter, "E")
        
        # Draw simulated pointing arrow pointing North-West (simulating live drone direction)
        import math
        heading_angle = math.radians(315 - 90)
        ax = int(rcx + rr * 0.75 * math.cos(heading_angle))
        ay = int(rcy + rr * 0.75 * math.sin(heading_angle))
        painter.setPen(QPen(hud_green, 2))
        painter.drawLine(rcx, rcy, ax, ay)
        painter.setBrush(QBrush(hud_green))
        painter.drawEllipse(ax - 3, ay - 3, 6, 6)

        # 3. Top-Center Compass Heading Scale
        painter.setPen(QPen(hud_white, 1))
        scale_y = ry + 40
        painter.drawLine(cx - 200, scale_y, cx + 200, scale_y)
        
        # labels: [255, W, 285, 300, NW, 330, 345, N, 15]
        labels = [("255", -160), ("W", -120), ("285", -80), ("300", -40), 
                  ("NW", 0), ("330", 40), ("345", 80), ("N", 120), ("15", 160)]
                  
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        for text, offset_x in labels:
            tx = cx + offset_x
            if text in ["N", "S", "E", "W", "NW", "NE", "SW", "SE"]:
                painter.setPen(QPen(hud_white, 2))
                painter.drawLine(tx, scale_y, tx, scale_y + 12)
                painter.drawText(tx - 15, scale_y - 15, 30, 12, Qt.AlignCenter, text)
            else:
                painter.setPen(QPen(hud_gray, 1))
                painter.drawLine(tx, scale_y, tx, scale_y + 8)
                painter.drawText(tx - 15, scale_y - 15, 30, 12, Qt.AlignCenter, text)
                
        # Draw center indicator triangle pointing down
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(hud_green))
        triangle = [QPoint(cx - 6, scale_y - 8), QPoint(cx + 6, scale_y - 8), QPoint(cx, scale_y)]
        painter.drawPolygon(triangle)

        # 4. Left Altitude Scale Ladder
        lx = rx + 60
        painter.setPen(QPen(hud_white, 1))
        painter.drawLine(lx, cy - 100, lx, cy + 100)
        
        painter.setFont(QFont("Segoe UI", 8))
        for alt_val in [0, 25, 50, 75, 100]:
            y_pos = cy + 80 - int(alt_val * 1.6)
            painter.setPen(QPen(hud_white, 1))
            painter.drawLine(lx, y_pos, lx + 8, y_pos)
            painter.setPen(hud_white)
            painter.drawText(lx + 12, y_pos - 6, 25, 12, Qt.AlignLeft | Qt.AlignVCenter, str(alt_val))
            
        # Draw moving pointer at 50
        target_alt_y = cy
        painter.setPen(QPen(hud_green, 1.5))
        painter.setBrush(QBrush(QColor(0, 220, 0, 40)))
        painter.drawRoundedRect(lx - 25, target_alt_y - 8, 22, 16, 3, 3)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(hud_green))
        ptr = [QPoint(lx - 4, target_alt_y - 4), QPoint(lx - 4, target_alt_y + 4), QPoint(lx + 1, target_alt_y)]
        painter.drawPolygon(ptr)

    def draw_landing_success_banner(self, painter, w, h):
        bw, bh = 300, 110
        bx = (w - bw) // 2
        by = (h - bh) // 2
        
        # Draw glassmorphic dark overlay with glowing green border
        painter.setPen(QPen(QColor(34, 197, 94, 200), 2))
        painter.setBrush(QBrush(QColor(10, 15, 24, 230)))
        painter.drawRoundedRect(bx, by, bw, bh, 10, 10)
        
        # Draw glowing green circle for checkmark
        cx, cy, cr = bx + 40, by + bh // 2, 20
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(34, 197, 94, 40)))
        painter.drawEllipse(cx - cr, cy - cr, cr * 2, cr * 2)
        
        painter.setPen(QPen(QColor(34, 197, 94), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(cx - 15, cy - 15, 30, 30)
        
        # Draw checkmark symbol inside the circle
        painter.setFont(QFont("Segoe UI", 12, QFont.Bold))
        painter.setPen(QColor(34, 197, 94))
        painter.drawText(cx - 15, cy - 15, 30, 30, Qt.AlignCenter, "✓")
        
        # Draw landing text
        tx = bx + 80
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", 12, QFont.Bold))
        painter.drawText(tx, by + 25, 200, 20, Qt.AlignLeft, "LANDING SUCCESSFUL")
        
        painter.setPen(QColor(148, 163, 184)) # Slate gray
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(tx, by + 50, 200, 20, Qt.AlignLeft, "Altitude: 0.0m | Disarmed")
        painter.drawText(tx, by + 70, 200, 20, Qt.AlignLeft, "Motors Safe. Secure area.")
