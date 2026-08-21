from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

class StatusBarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setObjectName("StatusBar")
        self.setStyleSheet("""
            QWidget#StatusBar {
                background-color: rgba(12, 14, 18, 160);
                border-bottom: 1px solid rgba(26, 30, 38, 100);
            }
            QFrame#StatusCard {
                background-color: #12161f;
                border: 1px solid #222a38;
                border-radius: 6px;
            }
            QLabel {
                color: #8c9ba5;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10px;
                font-weight: bold;
                padding: 0px;
                background: transparent;
            }
            QLabel#ValueLabel {
                font-size: 12px;
                font-weight: 900;
                font-family: 'Consolas', monospace;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(10)

        # Helper to build status cards
        def create_card(title, icon_char, is_large=False):
            frame = QFrame(self)
            frame.setObjectName("StatusCard")
            frame.setFixedHeight(45 if is_large else 40)
            
            card_layout = QHBoxLayout(frame)
            card_layout.setContentsMargins(15 if is_large else 10, 2, 15 if is_large else 10, 2)
            card_layout.setSpacing(8)
            
            icon_lbl = QLabel(icon_char, frame)
            icon_lbl.setStyleSheet(f"font-size: {'20px' if is_large else '16px'}; color: #ffffff;")
            
            info_widget = QWidget(frame)
            info_layout = QHBoxLayout(info_widget)
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(2)
            
            title_lbl = QLabel(title.upper(), info_widget)
            title_lbl.setStyleSheet(f"color: #7b8893; font-size: {'11px' if is_large else '9px'};")
            
            val_lbl = QLabel("--", info_widget)
            val_lbl.setObjectName("ValueLabel")
            if is_large:
                val_lbl.setStyleSheet("font-size: 18px; color: #00ff00;")
            
            info_layout.addWidget(title_lbl)
            info_layout.addWidget(val_lbl)
            
            card_layout.addWidget(icon_lbl)
            card_layout.addWidget(info_widget)
            
            return frame, val_lbl

        # Left side
        frame_batt, self.lbl_battery = create_card("Battery", "🔋")
        frame_pipx, self.lbl_pi_px = create_card("Pi ↔ PX", "🔌")
        frame_fs, self.lbl_failsafe = create_card("Failsafe", "🚨")
        
        layout.addWidget(frame_batt)
        layout.addWidget(frame_pipx)
        layout.addWidget(frame_fs)

        layout.addStretch(1)

        # Center (Speed)
        frame_speed, self.lbl_speed = create_card("Speed", "🚀", is_large=True)
        layout.addWidget(frame_speed)

        layout.addStretch(1)

        # Right side
        frame_ctrl_batt, self.lbl_gamepad_battery = create_card("Ctrl Battery", "🎮")
        frame_lat, self.lbl_latency = create_card("Latency", "⏱️")
        
        layout.addWidget(frame_ctrl_batt)
        layout.addWidget(frame_lat)

        # Record Video Button Card
        from PySide6.QtWidgets import QPushButton
        self.btn_rec = QPushButton("🔴  REC [SHARE]", self)
        self.btn_rec.setObjectName("RecButton")
        self.btn_rec.setCheckable(True)
        self.btn_rec.setCursor(Qt.PointingHandCursor)
        self.btn_rec.setFixedHeight(40)
        self.btn_rec.setStyleSheet("""
            QPushButton#RecButton {
                background-color: #12161f;
                border: 1px solid #222a38;
                border-radius: 6px;
                color: #8c9ba5;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: bold;
                padding: 0px 14px;
            }
            QPushButton#RecButton:hover {
                border-color: #ff3333;
                color: #ffff;
            }
            QPushButton#RecButton:checked {
                background-color: rgba(220, 50, 50, 40);
                border: 1.5px solid #ff3333;
                color: #ff3333;
            }
        """)
        layout.addWidget(self.btn_rec)

        self.update_status(None)

    def update_status(self, ui_state):
        if not ui_state:
            self.lbl_battery.setText("<span style='color:#7b8893;'>--% (--V)</span>")
            self.lbl_speed.setText("<span style='color:#7b8893;'>0.0 m/s</span>")
            self.lbl_pi_px.setText("<span style='color:#ff3333;'>OFFLINE</span>")
            self.lbl_failsafe.setText("<span style='color:#7b8893;'>INACTIVE</span>")
            self.lbl_gamepad_battery.setText("<span style='color:#ff3333;'>Unavailable</span>")
            self.lbl_latency.setText("<span style='color:#ffffff;'>-- ms</span>")
            return

        # Update record button timer text if recording
        if ui_state.get("is_recording", False):
            elapsed = ui_state.get("recording_elapsed", 0)
            mins, secs = divmod(elapsed, 60)
            self.btn_rec.setText(f"🔴  REC {mins:02d}:{secs:02d}")
            if not self.btn_rec.isChecked():
                self.btn_rec.setChecked(True)
        else:
            if not ui_state.get("is_recording", False):
                self.btn_rec.setText("🔴  REC [SHARE]")

        # Battery Status (Percentage & Voltage)
        bat = ui_state.get("battery", 0.0)
        volt = ui_state.get("battery_voltage", 0.0)
        bat_color = "#00ff00" if bat > 30 else "#ffcc00" if bat > 15 else "#ff3333"
        self.lbl_battery.setText(f"<span style='color:{bat_color};'>{bat}% ({volt:.1f}V)</span>")

        # Speed
        speed = ui_state.get("ground_speed", 0.0)
        self.lbl_speed.setText(f"<span style='color:#00ff00;'>{speed:.1f} m/s</span>")

        # Pi-Pixhawk connection status
        if ui_state.get("pi_pixhawk_connected", False):
            self.lbl_pi_px.setText("<span style='color:#00ff00;'>CONNECTED</span>")
        else:
            self.lbl_pi_px.setText("<span style='color:#ff3333;'>DISCONNECTED</span>")

        # Failsafe Status
        if ui_state.get("failsafe_active", False):
            self.lbl_failsafe.setText("<span style='color:#ff3333; font-weight:900;'>🚨 ACTIVE</span>")
        else:
            self.lbl_failsafe.setText("<span style='color:#8c9ba5;'>INACTIVE</span>")

        # Controller Status
        if ui_state.get("gamepad_connected", False):
            # Read exact battery percentage from DS4Windows OSC telemetry
            bat_pct = ui_state.get("ds4_battery_pct", None)
            if bat_pct is not None:
                color = "#00ff00" if bat_pct > 50 else "#ffcc00" if bat_pct > 20 else "#ff3333"
                self.lbl_gamepad_battery.setText(f"<span style='color:{color};'>{bat_pct}%</span>")
            else:
                self.lbl_gamepad_battery.setText("<span style='color:#7b8893;'>Unavailable</span>")
        else:
            self.lbl_gamepad_battery.setText("<span style='color:#ff3333;'>Disconnected</span>")

        # Latency Status
        lat = ui_state.get("latency", 0)
        self.lbl_latency.setText(f"<span style='color:#ffffff;'>{lat} ms</span>")
