import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QRadialGradient, QBrush, QConicalGradient
from PySide6.QtCore import Qt, QPoint, QRectF, QPointF

class JoystickWidget(QWidget):
    def __init__(self, title, is_left=True, parent=None):
        super().__init__(parent)
        self.title = title
        self.is_left = is_left
        
        # State values: x and y in range [-1.0, 1.0]
        self.stick_x = 0.0
        self.stick_y = 0.0
        
        self.setMinimumSize(215, 215)
        self.setMaximumSize(235, 235)

    def set_values(self, x, y):
        self.stick_x = max(-1.0, min(1.0, x))
        self.stick_y = max(-1.0, min(1.0, y))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        radius = min(w, h) // 2 - 25
        
        # Color schemes matching the mockup
        # Left has green accents, Right has blue accents
        accent_color = QColor(0, 220, 0) if self.is_left else QColor(0, 120, 255)
        accent_alpha_30 = QColor(0, 220, 0, 30) if self.is_left else QColor(0, 120, 255, 30)
        accent_alpha_80 = QColor(0, 220, 0, 80) if self.is_left else QColor(0, 120, 255, 80)

        # 1. Draw outer thin guide rings
        painter.setPen(QPen(QColor(40, 45, 55, 100), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(cx, cy), radius + 8, radius + 8)

        # 2. Draw circular track background with gradient
        track_grad = QRadialGradient(cx, cy, radius)
        track_grad.setColorAt(0.0, QColor(15, 18, 22, 180))
        track_grad.setColorAt(0.8, QColor(10, 12, 14, 220))
        track_grad.setColorAt(1.0, QColor(5, 6, 8, 240))
        painter.setBrush(QBrush(track_grad))
        painter.setPen(QPen(QColor(30, 35, 45), 2))
        painter.drawEllipse(QPoint(cx, cy), radius, radius)

        # 3. Draw crosshair guidelines inside the track
        painter.setPen(QPen(QColor(60, 65, 75, 80), 1, Qt.DashLine))
        painter.drawLine(cx - radius + 10, cy, cx + radius - 10, cy)
        painter.drawLine(cx, cy - radius + 10, cx, cy + radius - 10)

        # 4. Draw active level indicator arc on the outer ring
        # Lights up dynamically centered on the exact angle of stick deflection.
        # If moving in one direction (e.g. North), it lights up a 90° arc at the top.
        # If moving diagonally (e.g. North-East), it lights up a 90° arc between North and East (the northeast quarter).
        r = math.sqrt(self.stick_x**2 + self.stick_y**2)
        if r > 0.05:
            angle_rad = math.atan2(self.stick_y, self.stick_x)
            angle_deg = math.degrees(angle_rad)
            # Normalize angle to [0, 360)
            angle_deg = (angle_deg + 360) % 360
            
            # The span of the lit arc is proportional to the deflection, capped at 90 degrees
            span = 90.0 * min(1.0, r)
            start_angle = angle_deg - span / 2.0
            
            painter.setPen(QPen(accent_color, 3))
            painter.drawArc(QRectF(cx - radius - 5, cy - radius - 5, radius * 2 + 10, radius * 2 + 10), 
                            int(start_angle * 16), int(span * 16))

        # 5. Draw labels around the joysticks
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        
        if self.is_left:
            # THROTTLE label at top
            painter.setPen(accent_color)
            painter.drawText(QRectF(0, cy - radius - 25, w, 20), Qt.AlignCenter, "THROTTLE")
            # YAW label at left
            painter.drawText(QRectF(5, cy - 10, 40, 20), Qt.AlignLeft, "YAW")
        else:
            # PITCH label at top
            painter.setPen(accent_color)
            painter.drawText(QRectF(0, cy - radius - 25, w, 20), Qt.AlignCenter, "PITCH")
            # ROLL label at right
            painter.drawText(QRectF(w - 45, cy - 10, 40, 20), Qt.AlignRight, "ROLL")

        # 6. Draw 3D Matte/Metallic Thumbstick Knob
        max_travel = radius - 25
        kx = cx + int(self.stick_x * max_travel)
        ky = cy - int(self.stick_y * max_travel)

        # Drop shadow under knob
        shadow_grad = QRadialGradient(kx, ky + 2, 26)
        shadow_grad.setColorAt(0.0, QColor(0, 0, 0, 180))
        shadow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(shadow_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(kx, ky + 2), 26, 26)

        # Outer rubberized rim
        rim_grad = QRadialGradient(kx - 5, ky - 5, 22)
        rim_grad.setColorAt(0.0, QColor(65, 70, 78))
        rim_grad.setColorAt(0.6, QColor(35, 38, 44))
        rim_grad.setColorAt(1.0, QColor(15, 17, 20))
        painter.setBrush(QBrush(rim_grad))
        painter.setPen(QPen(QColor(20, 22, 26), 1.5))
        painter.drawEllipse(QPoint(kx, ky), 22, 22)

        # Inner ring groove
        painter.setPen(QPen(QColor(10, 12, 14), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(kx, ky), 16, 16)

        # Inner thumb rest cap (matte dark gradient)
        cap_grad = QRadialGradient(kx - 3, ky - 3, 16)
        cap_grad.setColorAt(0.0, QColor(50, 54, 62))
        cap_grad.setColorAt(0.7, QColor(28, 30, 35))
        cap_grad.setColorAt(1.0, QColor(18, 20, 23))
        painter.setBrush(QBrush(cap_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(kx, ky), 15, 15)
