import RPi.GPIO as GPIO
import threading
import signal

# Buttons (Pirate Audio)
BUTTONS = [5, 6, 16, 24]
LABELS = ['A', 'B', 'X', 'Y']

LAST_KEY = ""

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def handle_button(pin):
    global LAST_KEY
    label = LABELS[BUTTONS.index(pin)]
    LAST_KEY = label
    # Optional: print for debugging
    # print(f"Button pressed: {label}")

# Setup interrupts
for pin in BUTTONS:
    GPIO.add_event_detect(pin, GPIO.FALLING, callback=handle_button, bouncetime=100)

# Run signal.pause() in a background thread so it doesn't block main.py
def _wait_for_events():
    signal.pause()

# Start the event listener thread
thread = threading.Thread(target=_wait_for_events, daemon=True)
thread.start()