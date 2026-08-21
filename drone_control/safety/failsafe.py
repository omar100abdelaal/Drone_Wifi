class FailsafeHandler:
    def __init__(self, control_state):
        self.control_state = control_state
        self.had_gamepad = False

    def check_failsafe(self):
        # If we had a gamepad and it disconnected, trigger failsafe disarm
        if self.control_state.gamepad_connected:
            self.had_gamepad = True
            self.control_state.failsafe_active = False
        else:
            if self.had_gamepad:
                # Lost connection to gamepad during active session
                self.control_state.failsafe_active = True
                if self.control_state.arm:
                    self.control_state.set_arm(False)
                    return True
            else:
                # No gamepad was connected (e.g. using keyboard/GUI controls)
                self.control_state.failsafe_active = False
        return False

