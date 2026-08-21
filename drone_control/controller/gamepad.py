import os
# Prevent pygame from printing banner on import
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import threading
import time
from PySide6.QtCore import QThread, Signal

class GamepadThread(QThread):
    status_changed = Signal(bool, str) # connected status, controller name
    takeoff_triggered = Signal()
    rtl_triggered = Signal()
    land_triggered = Signal()
    set_home_triggered = Signal()
    record_toggled = Signal()
    change_mode_triggered = Signal()
    confirm_mode_triggered = Signal()
    arm_disarm_triggered = Signal()
    cancel_triggered = Signal()
    kill_motors_triggered = Signal()

    def __init__(self, control_state, dead_zone=0.1, parent=None):
        super().__init__(parent)
        self.control_state = control_state
        self.dead_zone = dead_zone
        self.running = False
        
        # Default layouts (will be adjusted dynamically on connect)
        self.axis_yaw = 0         # Left Stick X
        self.axis_throttle = 1    # Left Stick Y (inverted)
        self.axis_roll = 2        # Right Stick X
        self.axis_pitch = 3       # Right Stick Y

    def run(self):
        pygame.init()
        pygame.joystick.init()
        self.running = True

        joystick = None
        
        # State tracking for edge-triggering
        last_buttons = {}
        last_l2_pressed = False
        last_r2_pressed = False
        last_time = time.time()
        loop_counter = 0

        while self.running:
            pygame.event.pump()
            count = pygame.joystick.get_count()

            if count == 0:
                if joystick is not None:
                    joystick = None
                    self.control_state.gamepad_connected = False
                    self.control_state.gamepad_battery = "unknown"
                    self.control_state.set_arm(False) # Safety Failsafe: disarm on disconnect
                    self.status_changed.emit(False, "Disconnected")
                time.sleep(1.0)
                last_time = time.time()
                continue

            now = time.time()
            dt = now - last_time
            last_time = now

            if joystick is None:
                joystick = pygame.joystick.Joystick(0)
                joystick.init()
                name = joystick.get_name()
                self.control_state.gamepad_connected = True
                self.status_changed.emit(True, name)
                
                # Layout setup
                name_lower = name.lower()
                is_playstation = any(x in name_lower for x in ["playstation", "ps5", "dualsense"])
                is_wireless = any(x in name_lower for x in ["wireless controller", "dualshock", "sony", "ps4"])
                
                # Bindings configuration
                self.axis_yaw = 0
                self.axis_throttle = 1
                self.axis_roll = 2
                self.axis_pitch = 3
                
                num_buttons = joystick.get_numbuttons()
                is_ps4_raw = num_buttons >= 14
                
                if is_ps4_raw:
                    # Bluetooth Raw / PS4 Controller Layout (Pygame 2 SDL)
                    self.btn_arm = 0           # Cross
                    self.btn_confirm = 1       # Circle
                    self.btn_cancel = 2        # Square
                    self.btn_change_mode = 3   # Triangle
                    self.btn_set_home = 9      # L1 (Set Home)
                    self.btn_takeoff = 10      # R1 (Takeoff)
                    self.btn_rtl = None        # L2 is Analog Axis 4
                    self.btn_land = None       # R2 is Analog Axis 5
                    self.btn_rec = 4           # Share (REC)
                    self.btn_options = 6       # Options (does nothing)
                    self.btn_kill = 15         # Touchpad click
                else:
                    # Xbox 360 Controller / DS4Windows Emulation Mapping (XInput)
                    self.btn_arm = 0           # A (Cross)
                    self.btn_confirm = 1       # B (Circle)
                    self.btn_cancel = 2        # X (Square)
                    self.btn_change_mode = 3   # Y (Triangle)
                    self.btn_set_home = 4      # LB (L1 - Set Home)
                    self.btn_takeoff = 5       # RB (R1 - Takeoff)
                    self.btn_rtl = None        # L2 is Analog Axis (LT, triggers RTL)
                    self.btn_land = None       # R2 is Analog Axis (RT, triggers Land)
                    self.btn_rec = 6           # Back (Share - REC)
                    self.btn_options = 7       # Start (Options - does nothing)
                    self.btn_kill = 13         # Touchpad click mapping in emulation

            # Read Axes
            raw_yaw = joystick.get_axis(self.axis_yaw) if joystick.get_numaxes() > self.axis_yaw else 0.0
            raw_throttle = joystick.get_axis(self.axis_throttle) if joystick.get_numaxes() > self.axis_throttle else 0.0
            raw_roll = joystick.get_axis(self.axis_roll) if joystick.get_numaxes() > self.axis_roll else 0.0
            raw_pitch = joystick.get_axis(self.axis_pitch) if joystick.get_numaxes() > self.axis_pitch else 0.0

            # Process dead-zones
            yaw = 0.0 if abs(raw_yaw) < self.dead_zone else raw_yaw
            roll = 0.0 if abs(raw_roll) < self.dead_zone else raw_roll
            pitch = 0.0 if abs(raw_pitch) < self.dead_zone else raw_pitch
            
            # Pitch inversion
            pitch = -pitch
            
            # Throttle rate control
            raw_throttle_val = 0.0 if abs(raw_throttle) < self.dead_zone else raw_throttle
            throttle_input = -raw_throttle_val
            
            current_throttle = self.control_state.throttle
            throttle_rate = 0.5
            new_throttle = current_throttle + (throttle_input * throttle_rate * dt)
            new_throttle = max(0.0, min(1.0, new_throttle))

            # Force axes to 0 when disarmed so UI doesn't move and drone receives neutral signals
            if not self.control_state.arm:
                yaw, roll, pitch, new_throttle, throttle_input = 0.0, 0.0, 0.0, 0.0, 0.0

            if not getattr(self.control_state, "keyboard_active", False):
                self.control_state.update_axes(roll, pitch, yaw, new_throttle, throttle_input)

            # Battery level check
            if loop_counter % 100 == 0:
                try:
                    self.control_state.gamepad_battery = joystick.get_power_level()
                except Exception:
                    self.control_state.gamepad_battery = "unknown"
            loop_counter += 1

            # Helper for button edge detection
            def is_clicked(btn_id):
                if btn_id is None or joystick.get_numbuttons() <= btn_id:
                    return False
                current_state = joystick.get_button(btn_id)
                old_state = last_buttons.get(btn_id, 0)
                last_buttons[btn_id] = current_state
                return current_state and not old_state

            # Edge trigger evaluation
            # 1. Arm / Disarm (Cross / Button 0)
            if is_clicked(self.btn_arm):
                self.arm_disarm_triggered.emit()

            # 2. Change Mode (Triangle / Button 3)
            if is_clicked(self.btn_change_mode):
                self.change_mode_triggered.emit()

            # 3. Confirm Selection / Confirm Dialog (Circle / Button 1)
            if is_clicked(self.btn_confirm):
                self.confirm_mode_triggered.emit()

            # 4. Cancel Confirmation Dialog (Square / Button 2)
            if is_clicked(self.btn_cancel):
                self.cancel_triggered.emit()

            # 5. Record Video (Share)
            if is_clicked(self.btn_rec):
                self.record_toggled.emit()

            # 6. Takeoff (R1)
            if is_clicked(self.btn_takeoff):
                self.takeoff_triggered.emit()

            # 7. Set Home (L1)
            if is_clicked(self.btn_set_home):
                self.set_home_triggered.emit()

            # 8. RTL (L2 - button or LT Analog Axis)
            l2_pressed = False
            if self.btn_rtl is not None:
                l2_pressed = is_clicked(self.btn_rtl)
            else:
                if joystick.get_numaxes() > 4:
                    if joystick.get_axis(4) > 0.5:
                        l2_pressed = True
            if l2_pressed and not last_l2_pressed:
                self.rtl_triggered.emit()
            last_l2_pressed = l2_pressed

            # 9. Land (R2 - button or RT Analog Axis)
            r2_pressed = False
            if self.btn_land is not None:
                r2_pressed = is_clicked(self.btn_land)
            else:
                if joystick.get_numaxes() > 5:
                    if joystick.get_axis(5) > 0.5:
                        r2_pressed = True
            if r2_pressed and not last_r2_pressed:
                self.land_triggered.emit()
            last_r2_pressed = r2_pressed
            
            # 10. Kill Motors (Touchpad)
            if is_clicked(self.btn_kill):
                self.kill_motors_triggered.emit()

            time.sleep(0.01)

    def stop(self):
        self.running = False
        self.wait()
        pygame.quit()
