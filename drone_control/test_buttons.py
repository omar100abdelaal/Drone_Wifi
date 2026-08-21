import pygame
import time

pygame.init()
pygame.joystick.init()

print("Waiting for joystick...")
while pygame.joystick.get_count() == 0:
    pygame.event.pump()
    time.sleep(1)

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"Detected Joystick: {joystick.get_name()}")
print(f"Number of Buttons: {joystick.get_numbuttons()}")
print(f"Number of Axes: {joystick.get_numaxes()}")
print("\n--- PRESS YOUR CONTROLLER BUTTONS NOW ---")
print("Press Ctrl+C to exit.")

last_buttons = {}
while True:
    pygame.event.pump()
    
    # Check buttons
    for i in range(joystick.get_numbuttons()):
        state = joystick.get_button(i)
        if state and not last_buttons.get(i, False):
            print(f"BUTTON PRESSED: ID {i}")
        last_buttons[i] = state
        
    # Check axes (only print if significantly moved)
    for i in range(joystick.get_numaxes()):
        val = joystick.get_axis(i)
        if val > 0.8:
            print(f"AXIS {i} + pressed (value {val:.2f})")
            time.sleep(0.2) # debounce
            
    time.sleep(0.05)
