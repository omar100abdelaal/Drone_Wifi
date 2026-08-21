import time

class RPiFailsafe:
    def __init__(self, timeout_ms=300):
        self.timeout_seconds = timeout_ms / 1000.0
        self.last_packet_time = time.time()
        self.is_failsafe_active = False

    def update_heartbeat(self):
        self.last_packet_time = time.time()
        if self.is_failsafe_active:
            print("Failsafe DEACTIVATED: Control packets resumed.")
            self.is_failsafe_active = False

    def check_failsafe(self):
        # Check if communication has ceased for too long
        elapsed = time.time() - self.last_packet_time
        if elapsed > self.timeout_seconds and not self.is_failsafe_active:
            print(f"!!! EMERGENCY Failsafe ACTIVATED: No packet received for {elapsed:.2f}s !!!")
            self.is_failsafe_active = True
            return True
        return self.is_failsafe_active
