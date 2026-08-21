from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

class ModernConfirmationDialog(QDialog):
    def __init__(self, title, message, is_warning=False, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setWindowTitle(title)
        self.resize(360, 180)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Style colors
        bg_color = "#0c0f16"
        border_color = "#e11d48" if is_warning else "#2563eb" # Red for danger/arm, Blue for actions
        accent_color = "#f43f5e" if is_warning else "#60a5fa"
        
        # Main container with border and background
        container = QFrame(self)
        container.setObjectName("Container")
        container.setStyleSheet(f"""
            QFrame#Container {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 12px;
            }}
        """)
        
        # Layouts
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header Title
        self.lbl_title = QLabel(title.upper(), container)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet(f"""
            color: {accent_color};
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 1px;
        """)
        main_layout.addWidget(self.lbl_title)

        # Message Body
        self.lbl_msg = QLabel(message, container)
        self.lbl_msg.setAlignment(Qt.AlignCenter)
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setStyleSheet("""
            color: #94a3b8;
            font-family: 'Segoe UI', sans-serif;
            font-size: 12px;
            line-height: 18px;
        """)
        main_layout.addWidget(self.lbl_msg)

        # Button Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_cancel = QPushButton("CANCEL", container)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #94a3b8;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: bold;
                padding: 8px;
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f1f5f9;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_proceed = QPushButton("PROCEED", container)
        self.btn_proceed.setCursor(Qt.PointingHandCursor)
        proceed_bg = "#e11d48" if is_warning else "#2563eb"
        proceed_hover = "#be123c" if is_warning else "#1d4ed8"
        self.btn_proceed.setStyleSheet(f"""
            QPushButton {{
                background-color: {proceed_bg};
                border: none;
                border-radius: 6px;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: bold;
                padding: 8px;
                min-width: 90px;
            }}
            QPushButton:hover {{
                background-color: {proceed_hover};
            }}
        """)
        self.btn_proceed.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_proceed)
        main_layout.addLayout(btn_layout)

        # Main window layout containing the container
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(container)

    # Allow dragging frameless window
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
