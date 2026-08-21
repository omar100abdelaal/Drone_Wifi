from PySide6.QtWidgets import QFrame, QHBoxLayout
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath, QLinearGradient, QBrush
from PySide6.QtCore import Qt, QPointF

class BottomPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BottomPanel")
        self.setFixedHeight(240)
        
        # Ensure transparent widget background so custom shape renders correctly
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        
        # Build custom path matching ________/      \____________ arch structure over joysticks
        path = QPainterPath()
        path.moveTo(0, 50)
        path.lineTo(35, 50)
        
        # Slanted entrance UP into Left Joystick arch
        path.cubicTo(QPointF(48, 50), QPointF(58, 30), QPointF(72, 15))
        
        # Flat/rounded roof over Left Joystick
        path.lineTo(208, 15)
        
        # Slanted exit DOWN from Left Joystick arch
        path.cubicTo(QPointF(222, 30), QPointF(232, 50), QPointF(245, 50))
        
        # Flat middle baseline
        path.lineTo(w - 245, 50)
        
        # Slanted entrance UP into Right Joystick arch
        path.cubicTo(QPointF(w - 232, 50), QPointF(w - 222, 30), QPointF(w - 208, 15))
        
        # Flat/rounded roof over Right Joystick
        path.lineTo(w - 72, 15)
        
        # Slanted exit DOWN from Right Joystick arch
        path.cubicTo(QPointF(w - 58, 30), QPointF(w - 48, 50), QPointF(w - 35, 50))
        path.lineTo(w, 50)
        
        # Enclose the shape to fill background
        path.lineTo(w, h)
        path.lineTo(0, h)
        path.closeSubpath()

        # Fill background
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0.0, QColor(13, 16, 23, 245))
        bg_grad.setColorAt(1.0, QColor(7, 9, 13, 255))
        painter.setBrush(QBrush(bg_grad))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

        # Draw top glow/gradient border line along the path (split green left, blue right)
        line_path = QPainterPath()
        line_path.moveTo(0, 50)
        line_path.lineTo(35, 50)
        line_path.cubicTo(QPointF(48, 50), QPointF(58, 30), QPointF(72, 15))
        line_path.lineTo(208, 15)
        line_path.cubicTo(QPointF(222, 30), QPointF(232, 50), QPointF(245, 50))
        line_path.lineTo(w - 245, 50)
        line_path.cubicTo(QPointF(w - 232, 50), QPointF(w - 222, 30), QPointF(w - 208, 15))
        line_path.lineTo(w - 72, 15)
        line_path.cubicTo(QPointF(w - 58, 30), QPointF(w - 48, 50), QPointF(w - 35, 50))
        line_path.lineTo(w, 50)

        # Color gradient for top border line (Green on left -> Dark Gray in middle -> Blue on right)
        border_grad = QLinearGradient(0, 0, w, 0)
        border_grad.setColorAt(0.0, QColor(0, 220, 0, 220))       # Glowing Green
        border_grad.setColorAt(0.2, QColor(0, 220, 0, 100))
        border_grad.setColorAt(0.5, QColor(40, 45, 55, 120))      # Dark Slate/Gray
        border_grad.setColorAt(0.8, QColor(0, 120, 255, 100))
        border_grad.setColorAt(1.0, QColor(0, 120, 255, 220))     # Glowing Blue

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border_grad, 2))
        painter.drawPath(line_path)
