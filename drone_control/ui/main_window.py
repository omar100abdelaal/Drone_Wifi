import math
import time
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGridLayout, QFrame, QComboBox, QMessageBox
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont, QColor, QKeyEvent

from ui.status_bar import StatusBarWidget
from ui.video_widget import VideoWidget
from ui.joystick_widget import JoystickWidget
from ui.bottom_panel import BottomPanel
from ui.drone_icon import DroneIconWidget
from ui.confirmation_dialog import ModernConfirmationDialog


class MainWindow(QMainWindow):
    def __init__(self, control_state, config, parent=None):
        super().__init__(parent)
        self.control_state = control_state
        self.config = config

        self.setWindowTitle("GRADUATION DRONE CONTROL DESKTOP")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 700)
        
        # Enable keyboard focus
        self.setFocusPolicy(Qt.StrongFocus)
        self.pressed_keys = set()
        
        # Visual joystick coordinates for smooth interpolation
        self.visual_left_x = 0.0
        self.visual_left_y = 0.0
        self.visual_right_x = 0.0
        self.visual_right_y = 0.0
        
        # Timing for smooth update calculations
        self.last_update_time = time.time()
        self.dead_zone = config.get("dead_zone", 0.1)
        
        # Takeoff sequence variables
        self.takeoff_active = False
        self.takeoff_start_time = 0.0
        
        # Pending flight mode for gamepad change/select mapping
        self.pending_flight_mode = None
        self.active_dialog = None
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #080a0f;
            }
            QFrame#BottomPanel {
                background-color: #0d1017;
                border-top: 1px solid #1a202c;
            }
            QFrame#TelemetryPanel {
                background-color: #121620;
                border: 1px solid #232a3b;
                border-radius: 8px;
                padding: 5px;
            }
            QLabel#TelTitle {
                color: #8c9ba5;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10px;
                font-weight: bold;
            }
            QLabel#TelVal {
                color: #00ff00;
                font-family: 'Consolas', monospace;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel#RightHUDTitle {
                color: #7b8893;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10px;
                font-weight: bold;
            }
            QLabel#RightHUDVal {
                color: #00ff00;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: bold;
            }
            QFrame#RightHUDCard {
                background-color: rgba(18, 22, 32, 220);
                border: 1px solid rgba(35, 42, 59, 200);
                border-radius: 8px;
                padding: 10px;
            }
            QFrame#ActionCard {
                background-color: rgba(18, 22, 32, 180);
                border: 1px solid rgba(35, 42, 59, 150);
                border-radius: 8px;
            }
            QPushButton#ArmButton {
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: bold;
                border-radius: 6px;
                min-width: 75px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton#DisarmButton {
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: bold;
                border-radius: 6px;
                min-width: 75px;
                min-height: 28px;
                max-height: 28px;
            }
            QComboBox#ModeSelect {
                background-color: #121620;
                border: 1px solid #232a3b;
                border-radius: 6px;
                padding: 4px 10px;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: bold;
                min-width: 130px;
                min-height: 28px;
            }
            QPushButton#ActionButton {
                background-color: #121620;
                border: 1px solid #232a3b;
                border-radius: 6px;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: bold;
                min-width: 70px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton#ActionButton:hover {
                background-color: #1c2333;
                border-color: #3b82f6;
            }
        """)

        self.video_thread = None

        self.init_ui()

        # Timer to update UI elements at ~60Hz
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start(16)

    def style_gamepad_btn_normal(self):
        return """
            QLabel {
                background-color: #121620;
                color: #94a3b8;
                border: 1px solid #232a3b;
                border-radius: 4px;
                padding: 3px 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 9px;
                font-weight: bold;
            }
        """

    def style_gamepad_btn_active(self, color):
        return f"""
            QLabel {{
                background-color: {color};
                color: #ffffff;
                border: 1px solid #ffffff;
                border-radius: 4px;
                padding: 3px 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 9px;
                font-weight: bold;
            }}
        """

    def flash_gamepad_button(self, button_name):
        if button_name == "triangle":
            self.btn_indicator_cycle.setStyleSheet(self.style_gamepad_btn_active("#eab308")) # Yellow for Triangle
            QTimer.singleShot(150, lambda: self.btn_indicator_cycle.setStyleSheet(self.style_gamepad_btn_normal()))
        elif button_name == "circle":
            self.btn_indicator_confirm.setStyleSheet(self.style_gamepad_btn_active("#ef4444")) # Red/Coral for Circle
            QTimer.singleShot(150, lambda: self.btn_indicator_confirm.setStyleSheet(self.style_gamepad_btn_normal()))
        elif button_name == "cross":
            self.btn_indicator_arm.setStyleSheet(self.style_gamepad_btn_active("#3b82f6")) # Blue for Cross
            QTimer.singleShot(150, lambda: self.btn_indicator_arm.setStyleSheet(self.style_gamepad_btn_normal()))
        elif button_name == "touchpad":
            self.btn_indicator_kill.setStyleSheet(self.style_gamepad_btn_active("#ef4444")) # Red for Touchpad
            QTimer.singleShot(150, lambda: self.btn_indicator_kill.setStyleSheet(self.style_gamepad_btn_normal()))

    def flash_quick_action_button(self, button_type):
        btn = None
        color = "#2563eb"
        if button_type == "takeoff":
            btn = self.btn_takeoff
            color = "#22c55e" # Green
        elif button_type == "rtl":
            btn = self.btn_rtl
            color = "#eab308" # Yellow
        elif button_type == "land":
            btn = self.btn_land
            color = "#ef4444" # Red
        elif button_type == "set_home":
            btn = self.btn_set_home
            color = "#3b82f6" # Blue
            
        if btn is not None:
            btn.setStyleSheet(f"QPushButton#ActionButton {{ background-color: {color}; border: 1.5px solid #ffffff; color: #ffffff; }}")
            QTimer.singleShot(300, lambda: btn.setStyleSheet(""))

    def set_video_thread(self, video_thread):
        self.video_thread = video_thread

    def toggle_recording(self):
        if self.video_thread:
            if self.video_thread.is_recording:
                self.video_thread.stop_recording()
            else:
                self.video_thread.start_recording()

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Status Bar
        self.status_bar = StatusBarWidget(self)
        self.status_bar.setFixedHeight(50)
        self.status_bar.btn_rec.clicked.connect(self.toggle_recording)
        main_layout.addWidget(self.status_bar)

        # 2. Video Area (16:9 aspect-ratio frame container)
        self.video_container = VideoWidget(self)
        main_layout.addWidget(self.video_container, stretch=1)

        # Toast alert notification for non-blocking notifications
        self.toast_label = QLabel(self.video_container)
        self.toast_label.setObjectName("ToastNotification")
        self.toast_label.setStyleSheet("""
            QLabel#ToastNotification {
                background-color: rgba(12, 15, 22, 235);
                border: 1.5px solid #22c55e;
                border-radius: 8px;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: bold;
                padding: 10px 18px;
            }
        """)
        self.toast_label.setAlignment(Qt.AlignCenter)
        self.toast_label.hide()

        # Setup layout inside video container to allow bottom panel to overlay
        video_layout = QVBoxLayout(self.video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(0)

        # Upper overlay area for HUD elements
        hud_overlay = QWidget(self.video_container)
        hud_layout = QGridLayout(hud_overlay)
        hud_layout.setContentsMargins(25, 25, 25, 0) # 0 bottom margin
        video_layout.addWidget(hud_overlay, stretch=1)

        # Right HUD Container
        right_hud_container = QWidget(hud_overlay)
        right_hud_layout = QVBoxLayout(right_hud_container)
        right_hud_layout.setContentsMargins(0, 0, 0, 0)
        right_hud_layout.setSpacing(10)
        
        # 1. Flight Mode Card (Top)
        self.hud_mode_card = QFrame(right_hud_container)
        self.hud_mode_card.setObjectName("RightHUDCard")
        self.hud_mode_card.setFixedWidth(160)
        self.hud_mode_card.setFixedHeight(65)
        
        mode_layout = QVBoxLayout(self.hud_mode_card)
        mode_layout.setContentsMargins(10, 8, 10, 8)
        mode_layout.setSpacing(2)
        
        mode_title = QLabel("FLIGHT MODE", self.hud_mode_card)
        mode_title.setObjectName("RightHUDTitle")
        mode_title.setAlignment(Qt.AlignCenter)
        
        self.mode_val = QLabel("STABILIZE", self.hud_mode_card)
        self.mode_val.setObjectName("RightHUDVal")
        self.mode_val.setStyleSheet("color: #00ff00;")
        self.mode_val.setAlignment(Qt.AlignCenter)
        
        mode_layout.addWidget(mode_title)
        mode_layout.addWidget(self.mode_val)
        
        # 2. Arm & Altitude Card (Bottom)
        self.hud_arm_alt_card = QFrame(right_hud_container)
        self.hud_arm_alt_card.setObjectName("RightHUDCard")
        self.hud_arm_alt_card.setFixedWidth(160)
        self.hud_arm_alt_card.setFixedHeight(125)
        
        arm_alt_layout = QVBoxLayout(self.hud_arm_alt_card)
        arm_alt_layout.setContentsMargins(10, 10, 10, 10)
        arm_alt_layout.setSpacing(6)
        
        self.arm_val = QLabel("DISARMED", self.hud_arm_alt_card)
        self.arm_val.setObjectName("RightHUDVal")
        self.arm_val.setStyleSheet("color: #ff3333; font-size: 16px;")
        self.arm_val.setAlignment(Qt.AlignCenter)
        
        alt_title = QLabel("ALTITUDE", self.hud_arm_alt_card)
        alt_title.setObjectName("RightHUDTitle")
        alt_title.setAlignment(Qt.AlignCenter)
        
        self.alt_val = QLabel("120 m", self.hud_arm_alt_card)
        self.alt_val.setObjectName("RightHUDVal")
        self.alt_val.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        self.alt_val.setAlignment(Qt.AlignCenter)
        
        arm_alt_layout.addWidget(self.arm_val)
        arm_alt_layout.addSpacing(4)
        arm_alt_layout.addWidget(alt_title)
        arm_alt_layout.addWidget(self.alt_val)
        
        # Add cards to container
        right_hud_layout.addWidget(self.hud_mode_card)
        right_hud_layout.addWidget(self.hud_arm_alt_card)
        
        hud_layout.addWidget(right_hud_container, 0, 1, Qt.AlignTop | Qt.AlignRight)
        hud_layout.setColumnStretch(0, 1)

        # 3. Bottom Dashboard Panel (overlaying bottom of video)
        bottom_panel = BottomPanel(self.video_container)
        bottom_panel.setObjectName("BottomPanel")
        bottom_panel.setFixedHeight(240)
        video_layout.addWidget(bottom_panel)

        bp_layout = QHBoxLayout(bottom_panel)
        bp_layout.setContentsMargins(15, 10, 15, 10)
        bp_layout.setSpacing(20)

        # Left Joystick Widget
        self.joystick_left = JoystickWidget("THROTTLE / YAW", is_left=True, parent=bottom_panel)
        bp_layout.addWidget(self.joystick_left)

        # Center Section (Telemetry Grid + Buttons)
        center_widget = QWidget(bottom_panel)
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 10, 0, 5)
        center_layout.setSpacing(10)
        
        # Telemetry Display Box
        tel_frame = QFrame(center_widget)
        tel_frame.setObjectName("TelemetryPanel")
        tel_layout = QGridLayout(tel_frame)
        tel_layout.setContentsMargins(15, 10, 15, 10)
        tel_layout.setSpacing(10)
        
        # Left metrics
        lbl_thr = QLabel("THROTTLE", tel_frame)
        lbl_thr.setObjectName("TelTitle")
        self.val_thr = QLabel("0.00", tel_frame)
        self.val_thr.setObjectName("TelVal")
        
        lbl_yaw = QLabel("YAW", tel_frame)
        lbl_yaw.setObjectName("TelTitle")
        self.val_yaw = QLabel("0.00", tel_frame)
        self.val_yaw.setObjectName("TelVal")

        # Center drone icon
        self.drone_icon_widget = DroneIconWidget(tel_frame)

        # Right metrics
        lbl_pit = QLabel("PITCH", tel_frame)
        lbl_pit.setObjectName("TelTitle")
        self.val_pit = QLabel("0.00", tel_frame)
        self.val_pit.setObjectName("TelVal")
        
        lbl_rol = QLabel("ROLL", tel_frame)
        lbl_rol.setObjectName("TelTitle")
        self.val_rol = QLabel("0.00", tel_frame)
        self.val_rol.setObjectName("TelVal")

        tel_layout.addWidget(lbl_thr, 0, 0, Qt.AlignLeft)
        tel_layout.addWidget(self.val_thr, 1, 0, Qt.AlignLeft)
        tel_layout.addWidget(lbl_yaw, 0, 1, Qt.AlignLeft)
        tel_layout.addWidget(self.val_yaw, 1, 1, Qt.AlignLeft)
        
        tel_layout.addWidget(self.drone_icon_widget, 0, 2, 2, 1, Qt.AlignCenter)
        
        tel_layout.addWidget(lbl_pit, 0, 3, Qt.AlignLeft)
        tel_layout.addWidget(self.val_pit, 1, 3, Qt.AlignLeft)
        tel_layout.addWidget(lbl_rol, 0, 4, Qt.AlignLeft)
        tel_layout.addWidget(self.val_rol, 1, 4, Qt.AlignLeft)
        
        center_layout.addWidget(tel_frame)

        # Bottom Button cards
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        # 1. Safety Card (ARM & DISARM)
        self.safety_card = QFrame(center_widget)
        self.safety_card.setObjectName("ActionCard")
        safety_card_layout = QVBoxLayout(self.safety_card)
        safety_card_layout.setContentsMargins(10, 8, 10, 8)
        safety_card_layout.setSpacing(6)
        
        lbl_safety_title = QLabel("SAFETY CONTROL", self.safety_card)
        lbl_safety_title.setObjectName("RightHUDTitle")
        lbl_safety_title.setAlignment(Qt.AlignCenter)
        
        arm_disarm_layout = QHBoxLayout()
        arm_disarm_layout.setSpacing(8)
        
        self.btn_arm = QPushButton("ARM", self.safety_card)
        self.btn_arm.setObjectName("ArmButton")
        self.btn_arm.setCursor(Qt.PointingHandCursor)
        self.btn_arm.clicked.connect(self.trigger_arm)
        
        self.btn_disarm = QPushButton("DISARM", self.safety_card)
        self.btn_disarm.setObjectName("DisarmButton")
        self.btn_disarm.setCursor(Qt.PointingHandCursor)
        self.btn_disarm.clicked.connect(self.trigger_disarm)
        
        self.btn_kill = QPushButton("KILL", self.safety_card)
        self.btn_kill.setObjectName("DisarmButton")
        self.btn_kill.setStyleSheet("background-color: #ef4444; color: white; border-color: #ef4444;")
        self.btn_kill.setCursor(Qt.PointingHandCursor)
        self.btn_kill.clicked.connect(self.trigger_kill_motors)
        
        arm_disarm_layout.addWidget(self.btn_arm)
        arm_disarm_layout.addWidget(self.btn_disarm)
        arm_disarm_layout.addWidget(self.btn_kill)
        
        lbl_safety_tip = QLabel("ARM (Shift+A) | DISARM (Shift+D) | KILL (Shift+K)", self.safety_card)
        lbl_safety_tip.setStyleSheet("font-size: 8px; color: #606870;")
        lbl_safety_tip.setAlignment(Qt.AlignCenter)
        
        indicators_layout = QHBoxLayout()
        indicators_layout.setSpacing(4)
        
        self.btn_indicator_arm = QLabel("✖ CROSS (ARM/DISARM)", self.safety_card)
        self.btn_indicator_arm.setObjectName("GamepadIndicator")
        self.btn_indicator_arm.setStyleSheet(self.style_gamepad_btn_normal())
        self.btn_indicator_arm.setAlignment(Qt.AlignCenter)
        
        self.btn_indicator_kill = QLabel("⬛ TOUCHPAD (KILL)", self.safety_card)
        self.btn_indicator_kill.setObjectName("GamepadIndicator")
        self.btn_indicator_kill.setStyleSheet(self.style_gamepad_btn_normal())
        self.btn_indicator_kill.setAlignment(Qt.AlignCenter)
        
        indicators_layout.addWidget(self.btn_indicator_arm)
        indicators_layout.addWidget(self.btn_indicator_kill)
        
        safety_card_layout.addWidget(lbl_safety_title)
        safety_card_layout.addLayout(arm_disarm_layout)
        safety_card_layout.addWidget(lbl_safety_tip)
        safety_card_layout.addLayout(indicators_layout)
        
        # 2. Flight Mode Card (Dropdown selection)
        self.mode_card = QFrame(center_widget)
        self.mode_card.setObjectName("ActionCard")
        mode_card_layout = QVBoxLayout(self.mode_card)
        mode_card_layout.setContentsMargins(10, 8, 10, 8)
        mode_card_layout.setSpacing(6)
        
        lbl_mode_title = QLabel("FLIGHT MODE", self.mode_card)
        lbl_mode_title.setObjectName("RightHUDTitle")
        lbl_mode_title.setAlignment(Qt.AlignCenter)
        
        self.mode_select = QComboBox(self.mode_card)
        self.mode_select.setObjectName("ModeSelect")
        self.mode_select.addItems(["STABILIZE", "ALT_HOLD", "LOITER"])
        self.mode_select.currentIndexChanged.connect(self.on_mode_select_changed)
        
        lbl_mode_tip = QLabel("F1 - F5: Select Flight Mode", self.mode_card)
        lbl_mode_tip.setStyleSheet("font-size: 8px; color: #606870;")
        lbl_mode_tip.setAlignment(Qt.AlignCenter)
        
        mode_btn_layout = QHBoxLayout()
        mode_btn_layout.setSpacing(4)
        
        self.btn_indicator_cycle = QLabel("🔺 CYCLE", self.mode_card)
        self.btn_indicator_cycle.setObjectName("GamepadIndicator")
        self.btn_indicator_cycle.setStyleSheet(self.style_gamepad_btn_normal())
        self.btn_indicator_cycle.setAlignment(Qt.AlignCenter)
        
        self.btn_indicator_confirm = QLabel("🔴 CONFIRM", self.mode_card)
        self.btn_indicator_confirm.setObjectName("GamepadIndicator")
        self.btn_indicator_confirm.setStyleSheet(self.style_gamepad_btn_normal())
        self.btn_indicator_confirm.setAlignment(Qt.AlignCenter)
        
        mode_btn_layout.addWidget(self.btn_indicator_cycle)
        mode_btn_layout.addWidget(self.btn_indicator_confirm)
        
        mode_card_layout.addWidget(lbl_mode_title)
        mode_card_layout.addWidget(self.mode_select, 0, Qt.AlignCenter)
        mode_card_layout.addWidget(lbl_mode_tip)
        mode_card_layout.addLayout(mode_btn_layout)

        # 3. Actions Card (RTL, LAND, TAKEOFF, SET HOME)
        self.actions_card = QFrame(center_widget)
        self.actions_card.setObjectName("ActionCard")
        actions_card_layout = QVBoxLayout(self.actions_card)
        actions_card_layout.setContentsMargins(10, 8, 10, 8)
        actions_card_layout.setSpacing(6)
        
        lbl_actions_title = QLabel("QUICK ACTIONS", self.actions_card)
        lbl_actions_title.setObjectName("RightHUDTitle")
        lbl_actions_title.setAlignment(Qt.AlignCenter)
        
        actions_buttons_layout = QHBoxLayout()
        actions_buttons_layout.setSpacing(6)
        
        self.btn_takeoff = QPushButton("TAKEOFF", self.actions_card)
        self.btn_takeoff.setObjectName("ActionButton")
        self.btn_takeoff.setCursor(Qt.PointingHandCursor)
        self.btn_takeoff.clicked.connect(self.trigger_takeoff)

        self.btn_rtl = QPushButton("RTL", self.actions_card)
        self.btn_rtl.setObjectName("ActionButton")
        self.btn_rtl.setCursor(Qt.PointingHandCursor)
        self.btn_rtl.clicked.connect(self.trigger_rtl)
        
        self.btn_land = QPushButton("LAND", self.actions_card)
        self.btn_land.setObjectName("ActionButton")
        self.btn_land.setCursor(Qt.PointingHandCursor)
        self.btn_land.clicked.connect(self.trigger_land)
        
        self.btn_set_home = QPushButton("SET HOME", self.actions_card)
        self.btn_set_home.setObjectName("ActionButton")
        self.btn_set_home.setCursor(Qt.PointingHandCursor)
        self.btn_set_home.clicked.connect(self.trigger_set_home)
        
        actions_buttons_layout.addWidget(self.btn_takeoff)
        actions_buttons_layout.addWidget(self.btn_rtl)
        actions_buttons_layout.addWidget(self.btn_land)
        actions_buttons_layout.addWidget(self.btn_set_home)
        
        lbl_actions_tip = QLabel("TAKEOFF (Shift+T) | RTL (F4) | LAND (F5) | HOME (Shift+H)", self.actions_card)
        lbl_actions_tip.setStyleSheet("font-size: 8px; color: #606870;")
        lbl_actions_tip.setAlignment(Qt.AlignCenter)
        
        actions_card_layout.addWidget(lbl_actions_title)
        actions_card_layout.addLayout(actions_buttons_layout)
        actions_card_layout.addWidget(lbl_actions_tip)

        btn_layout.addWidget(self.safety_card)
        btn_layout.addWidget(self.mode_card)
        btn_layout.addWidget(self.actions_card)
        center_layout.addLayout(btn_layout)
        
        bp_layout.addWidget(center_widget, stretch=1)

        # Right Joystick Widget
        self.joystick_right = JoystickWidget("PITCH / ROLL", is_left=False, parent=bottom_panel)
        bp_layout.addWidget(self.joystick_right)

    @Slot(object)
    def on_frame_received(self, qt_image):
        self.video_container.set_image(qt_image)

    def trigger_arm(self):
        if self.active_dialog is not None:
            return
        print("[GUI Click] ARM Button Clicked - Prompting for confirmation")
        dialog = ModernConfirmationDialog(
            "Confirm Arming",
            "WARNING: You are about to arm the motors. This will spin the propellers. Proceed?",
            is_warning=True,
            parent=self
        )
        self.active_dialog = dialog
        accepted = (dialog.exec() == ModernConfirmationDialog.Accepted)
        self.active_dialog = None
        
        if accepted:
            print("[GUI Click] ARM Confirmed - Setting arm state to True")
            self.control_state.set_arm(True)
        else:
            print("[GUI Click] ARM Cancelled")

    def trigger_disarm(self):
        if self.active_dialog is not None:
            return
        print("[GUI Click] DISARM Button Clicked - Prompting for confirmation")
        dialog = ModernConfirmationDialog(
            "Confirm Disarming",
            "WARNING: Disarming in flight will stop the motors and cause the drone to crash. Proceed?",
            is_warning=True,
            parent=self
        )
        self.active_dialog = dialog
        accepted = (dialog.exec() == ModernConfirmationDialog.Accepted)
        self.active_dialog = None
        
        if accepted:
            print("[GUI Click] DISARM Confirmed - Setting arm state to False")
            self.control_state.set_arm(False)
        else:
            print("[GUI Click] DISARM Cancelled")

    def trigger_kill_motors(self):
        print("[GUI Click] KILL MOTORS Triggered - No confirmation required")
        self.flash_gamepad_button("touchpad")
        self.show_toast("🚨 MOTORS KILLED 🚨")
        self.control_state.trigger_kill_motors()

    def trigger_takeoff(self):
        if self.active_dialog is not None:
            return False
        print("[GUI Click] TAKEOFF Button Clicked - Prompting for confirmation")
        dialog = ModernConfirmationDialog(
            "Confirm Takeoff",
            "Do you want to automatically arm and takeoff the drone to 0.5 meters altitude?",
            is_warning=False,
            parent=self
        )
        self.active_dialog = dialog
        accepted = (dialog.exec() == ModernConfirmationDialog.Accepted)
        self.active_dialog = None
        
        if accepted:
            self.flash_quick_action_button("takeoff")
            print("[GUI Click] Takeoff Confirmed - Setting mode to ALT_HOLD and arming")
            self.change_mode_direct("ALT_HOLD")
            self.control_state.set_arm(True)
            self.takeoff_active = True
            self.takeoff_start_time = time.time()
            return True
        print("[GUI Click] Takeoff Cancelled")
        return False

    def trigger_rtl(self):
        if self.active_dialog is not None:
            return False
        print("[GUI Click] RTL Button Clicked - Prompting for confirmation")
        dialog = ModernConfirmationDialog(
            "Confirm RTL",
            "Do you want to command the drone to return to the launch coordinates?",
            is_warning=False,
            parent=self
        )
        self.active_dialog = dialog
        accepted = (dialog.exec() == ModernConfirmationDialog.Accepted)
        self.active_dialog = None
        
        if accepted:
            self.flash_quick_action_button("rtl")
            print("[GUI Click] RTL Confirmed - Setting flight mode to RTL")
            self.control_state.set_flight_mode("RTL")
            return True
        print("[GUI Click] RTL Cancelled")
        return False

    def trigger_land(self):
        if self.active_dialog is not None:
            return False
        print("[GUI Click] LAND Button Clicked - Prompting for confirmation")
        dialog = ModernConfirmationDialog(
            "Confirm Landing",
            "Do you want to land the drone immediately at its current position?",
            is_warning=False,
            parent=self
        )
        self.active_dialog = dialog
        accepted = (dialog.exec() == ModernConfirmationDialog.Accepted)
        self.active_dialog = None
        
        if accepted:
            self.flash_quick_action_button("land")
            print("[GUI Click] LAND Confirmed - Setting flight mode to LAND")
            self.control_state.set_flight_mode("LAND")
            return True
        print("[GUI Click] LAND Cancelled")
        return False

    def show_toast(self, message):
        self.toast_label.setText(message)
        self.toast_label.adjustSize()
        # Center horizontally at the top of the video widget
        vw_width = self.video_container.width()
        lbl_width = self.toast_label.width()
        self.toast_label.move((vw_width - lbl_width) // 2, 20)
        self.toast_label.show()
        # Hide after 3 seconds
        QTimer.singleShot(3000, self.toast_label.hide)

    def trigger_set_home(self):
        if self.active_dialog is not None:
            return
        print("[GUI Click] SET HOME Button Clicked")
        self.flash_quick_action_button("set_home")
        # Optional set home position update
        alt = self.control_state.altitude
        self.control_state.home_position = {"lat": 37.7749, "lon": -122.4194, "alt": alt}
        print(f"[GUI Click] SET HOME Success - Home Altitude set to {alt}m")
        self.show_toast(f"🟢 HOME POSITION SET SUCCESSFUL\nAltitude: {alt:.1f}m")


    def on_mode_select_changed(self, index):
        mode = self.mode_select.itemText(index)
        current_mode = self.control_state.flight_mode
        if mode == current_mode:
            return

        if mode == "RTL":
            if not self.trigger_rtl():
                # Revert selection
                self.mode_select.blockSignals(True)
                self.mode_select.setCurrentText(current_mode)
                self.mode_select.blockSignals(False)
        elif mode == "LAND":
            if not self.trigger_land():
                # Revert selection
                self.mode_select.blockSignals(True)
                self.mode_select.setCurrentText(current_mode)
                self.mode_select.blockSignals(False)
        else:
            self.control_state.set_flight_mode(mode)

    def cycle_target_mode(self):
        if self.active_dialog is not None:
            return
        self.flash_gamepad_button("triangle")
        modes = ["STABILIZE", "ALT_HOLD", "LOITER"]
        if self.pending_flight_mode is None:
            self.pending_flight_mode = self.control_state.flight_mode
            
        current_index = modes.index(self.pending_flight_mode) if self.pending_flight_mode in modes else 0
        next_index = (current_index + 1) % len(modes)
        self.pending_flight_mode = modes[next_index]
        
        print(f"[Gamepad Action] Cycle target flight mode to: {self.pending_flight_mode}")
        
        self.mode_select.blockSignals(True)
        self.mode_select.setCurrentText(self.pending_flight_mode)
        self.mode_select.blockSignals(False)
        
        # Apply pending styling (dashed yellow border to show it requires confirmation)
        self.mode_select.setStyleSheet("""
            QComboBox#ModeSelect {
                background-color: #1c1c10;
                border: 1.5px dashed #eab308;
                border-radius: 6px;
                padding: 4px 10px;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: bold;
                min-width: 130px;
                min-height: 28px;
            }
        """)

    def confirm_target_mode(self):
        if self.pending_flight_mode is None:
            print("[Gamepad Action] No pending flight mode to confirm.")
            return
            
        target_mode = self.pending_flight_mode
        self.pending_flight_mode = None
        self.mode_select.setStyleSheet("")
        
        print(f"[Gamepad Action] Confirming target flight mode: {target_mode}")
        
        if target_mode == "RTL":
            if not self.trigger_rtl():
                self.change_mode_direct(self.control_state.flight_mode)
        elif target_mode == "LAND":
            if not self.trigger_land():
                self.change_mode_direct(self.control_state.flight_mode)
        else:
            self.change_mode_direct(target_mode)

    def change_mode_direct(self, mode):
        self.mode_select.blockSignals(True)
        self.mode_select.setCurrentText(mode)
        self.mode_select.blockSignals(False)
        self.control_state.set_flight_mode(mode)

    def trigger_arm_disarm_toggle(self):
        self.flash_gamepad_button("cross")
        if self.active_dialog is not None:
            return
        if self.control_state.arm:
            self.trigger_disarm()
        else:
            self.trigger_arm()

    def handle_confirm_or_proceed(self):
        if self.active_dialog is not None:
            self.active_dialog.accept()
        else:
            self.flash_gamepad_button("circle")
            self.confirm_target_mode()

    def handle_cancel(self):
        if self.active_dialog is not None:
            self.active_dialog.reject()
        else:
            if self.pending_flight_mode is not None:
                self.pending_flight_mode = None
                self.mode_select.setStyleSheet("")
                self.change_mode_direct(self.control_state.flight_mode)

    def keyPressEvent(self, event: QKeyEvent):
        # Keyboard shortcuts that require modifiers/specific keys to avoid WASD/Arrow keys conflict
        if event.modifiers() & Qt.ShiftModifier:
            if event.key() == Qt.Key_A:
                self.trigger_arm()
                return
            elif event.key() == Qt.Key_D:
                self.trigger_disarm()
                return
            elif event.key() == Qt.Key_H:
                self.trigger_set_home()
                return
            elif event.key() == Qt.Key_T:
                self.trigger_takeoff()
                return
            elif event.key() == Qt.Key_K:
                self.trigger_kill_motors()
                return
        else:
            if event.key() == Qt.Key_F1:
                self.change_mode_direct("STABILIZE")
                return
            elif event.key() == Qt.Key_F2:
                self.change_mode_direct("ALT_HOLD")
                return
            elif event.key() == Qt.Key_F3:
                self.change_mode_direct("LOITER")
                return
            elif event.key() == Qt.Key_F4:
                # Triggers RTL confirmation
                self.mode_select.setCurrentText("RTL")
                return
            elif event.key() == Qt.Key_F5:
                # Triggers LAND confirmation
                self.mode_select.setCurrentText("LAND")
                return

        self.pressed_keys.add(event.key())
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if not event.isAutoRepeat():
            self.pressed_keys.discard(event.key())
        super().keyReleaseEvent(event)

    def update_ui(self):
        now = time.time()
        dt = now - self.last_update_time
        self.last_update_time = now

        # Determine target values from keyboard
        target_roll = 0.0
        target_pitch = 0.0
        target_yaw = 0.0
        target_throttle_rate = 0.0

        if Qt.Key_Up in self.pressed_keys:
            target_pitch += 1.0
        if Qt.Key_Down in self.pressed_keys:
            target_pitch -= 1.0
        if Qt.Key_Right in self.pressed_keys:
            target_roll += 1.0
        if Qt.Key_Left in self.pressed_keys:
            target_roll -= 1.0

        if Qt.Key_D in self.pressed_keys:
            target_yaw += 1.0
        if Qt.Key_A in self.pressed_keys:
            target_yaw -= 1.0

        if Qt.Key_W in self.pressed_keys:
            target_throttle_rate += 1.0
        if Qt.Key_S in self.pressed_keys:
            target_throttle_rate -= 1.0

        # Set keyboard_active if control keys are pressed
        control_keys_pressed = self.pressed_keys.intersection({
            Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right,
            Qt.Key_W, Qt.Key_S, Qt.Key_A, Qt.Key_D
        })
        if control_keys_pressed:
            self.control_state.keyboard_active = True

        # Smooth animation (lerp) for the joysticks
        # Using exponential decay: val = val + (target - val) * (1 - e^(-lerp_speed * dt))
        lerp_speed = 10.0
        lerp_factor = 1.0 - math.exp(-lerp_speed * dt)

        self.visual_right_x += (target_roll - self.visual_right_x) * lerp_factor
        self.visual_right_y += (target_pitch - self.visual_right_y) * lerp_factor
        self.visual_left_x += (target_yaw - self.visual_left_x) * lerp_factor
        self.visual_left_y += (target_throttle_rate - self.visual_left_y) * lerp_factor

        # If keyboard was active but keys are released and visual joysticks are back to center, return control
        if getattr(self.control_state, "keyboard_active", False) and not control_keys_pressed:
            if abs(self.visual_left_x) < 0.01 and abs(self.visual_left_y) < 0.01 and \
               abs(self.visual_right_x) < 0.01 and abs(self.visual_right_y) < 0.01:
                self.visual_left_x = 0.0
                self.visual_left_y = 0.0
                self.visual_right_x = 0.0
                self.visual_right_y = 0.0
                self.control_state.keyboard_active = False

        # Update stored throttle value incrementally if W/S is held
        if getattr(self.control_state, "keyboard_active", False):
            throttle_rate = 0.4  # Throttle change per second
            new_throttle = self.control_state.throttle
            if Qt.Key_W in self.pressed_keys:
                new_throttle = min(1.0, new_throttle + throttle_rate * dt)
            if Qt.Key_S in self.pressed_keys:
                new_throttle = max(0.0, new_throttle - throttle_rate * dt)

            # Apply deadzone for control commands
            roll_cmd = 0.0 if abs(self.visual_right_x) < self.dead_zone else self.visual_right_x
            pitch_cmd = 0.0 if abs(self.visual_right_y) < self.dead_zone else self.visual_right_y
            yaw_cmd = 0.0 if abs(self.visual_left_x) < self.dead_zone else self.visual_left_x

            self.control_state.update_axes(roll_cmd, pitch_cmd, yaw_cmd, new_throttle, target_throttle_rate)

        # Takeoff sequence handling
        if self.takeoff_active:
            # Check for pilot intervention (if user presses control keys or moves gamepad sticks)
            gamepad_active = False
            state = self.control_state.get_ui_state()
            if state["gamepad_connected"]:
                if abs(state["roll"]) > self.dead_zone or abs(state["pitch"]) > self.dead_zone or \
                   abs(state["yaw"]) > self.dead_zone or abs(state["throttle_input"]) > self.dead_zone:
                    gamepad_active = True
            
            if control_keys_pressed or gamepad_active:
                print("[Takeoff] Pilot override detected! Aborting automatic takeoff.")
                self.takeoff_active = False
            else:
                elapsed = time.time() - self.takeoff_start_time
                current_alt = state.get("altitude", 0.0)
                
                # Check takeoff completion conditions (0.5m reached or 2.0s elapsed)
                if current_alt >= 0.5 or elapsed >= 2.0:
                    print(f"[Takeoff] Takeoff target reached (Alt: {current_alt}m, Time: {elapsed:.2f}s). Hovering.")
                    self.control_state.update_axes(0.0, 0.0, 0.0, 0.5, 0.0)
                    self.takeoff_active = False
                else:
                    # Climb at 65% throttle, yaw/roll/pitch centered
                    self.control_state.update_axes(0.0, 0.0, 0.0, 0.65, 0.3)

        # Get current state
        state = self.control_state.get_ui_state()

        if self.video_thread:
            state["is_recording"] = self.video_thread.is_recording
            state["recording_elapsed"] = self.video_thread.get_recording_elapsed()

        # Update status bar cards
        self.status_bar.update_status(state)

        # Update video widget live state
        self.video_container.set_video_live(state["video_live"])
        self.video_container.set_state(state)

        # Update Right HUD Overlays
        self.mode_val.setText(state["flight_mode"])
        self.alt_val.setText(f"{state.get('altitude', 0.0):.1f} m")
        
        # Update Arm HUD styling
        if state["arm"]:
            self.arm_val.setText("ARMED")
            self.arm_val.setStyleSheet("color: #22c55e; font-size: 16px; font-weight: bold;")
            
            self.btn_arm.setStyleSheet("background-color: #22c55e; border: 1.5px solid #22c55e; color: #ffffff; font-weight: bold;")
            self.btn_disarm.setStyleSheet("background-color: #121620; border: 1px solid #232a3b; color: #8c9ba5;")
        else:
            self.arm_val.setText("DISARMED")
            self.arm_val.setStyleSheet("color: #ff3333; font-size: 16px; font-weight: bold;")
            
            self.btn_arm.setStyleSheet("background-color: #121620; border: 1px solid #232a3b; color: #8c9ba5;")
            self.btn_disarm.setStyleSheet("background-color: #ff3333; border: 1.5px solid #ff3333; color: #ffffff; font-weight: bold;")

        # Update flight mode selector dropdown representation without triggering signals if no pending mode is active
        if self.pending_flight_mode is None:
            self.mode_select.blockSignals(True)
            self.mode_select.setCurrentText(state["flight_mode"])
            self.mode_select.blockSignals(False)

        # Update visual joysticks
        if getattr(self.control_state, "keyboard_active", False) or not state["gamepad_connected"]:
            if self.takeoff_active:
                self.joystick_left.set_values(0.0, 0.3)
                self.joystick_right.set_values(0.0, 0.0)
            else:
                self.joystick_left.set_values(self.visual_left_x, self.visual_left_y)
                self.joystick_right.set_values(self.visual_right_x, self.visual_right_y)
        else:
            self.joystick_left.set_values(state["yaw"], state["throttle_input"])
            self.joystick_right.set_values(state["roll"], state["pitch"])

        # Update central telemetry grid text labels
        self.val_thr.setText(f"{state['throttle']:0.2f}")
        self.val_yaw.setText(f"{state['yaw']:+0.2f}")
        self.val_pit.setText(f"{state['pitch']:+0.2f}")
        self.val_rol.setText(f"{state['roll']:+0.2f}")
