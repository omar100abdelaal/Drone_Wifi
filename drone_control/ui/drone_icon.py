from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, QPoint

class DroneIconWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 50)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        
        # Draw quadcopter arms (diagonal lines)
        painter.setPen(QPen(QColor(240, 240, 240, 220), 3))
        arm_len = 16
        painter.drawLine(cx - arm_len, cy - arm_len, cx + arm_len, cy + arm_len)
        painter.drawLine(cx - arm_len, cy + arm_len, cx + arm_len, cy - arm_len)

        # Draw center fuselage circle
        painter.setBrush(QColor(15, 18, 24))
        painter.setPen(QPen(QColor(240, 240, 240, 220), 2))
        painter.drawEllipse(QPoint(cx, cy), 8, 8)
        
        # Draw 4 rotor rings at the end of the arms
        r_radius = 6
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(240, 240, 240, 180), 1.5))
        painter.drawEllipse(QPoint(cx - arm_len, cy - arm_len), r_radius, r_radius)
        painter.drawEllipse(QPoint(cx + arm_len, cy - arm_len), r_radius, r_radius)
        painter.drawEllipse(QPoint(cx - arm_len, cy + arm_len), r_radius, r_radius)
        painter.drawEllipse(QPoint(cx + arm_len, cy + arm_len), r_radius, r_radius)
