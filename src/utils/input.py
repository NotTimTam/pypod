import RPi.GPIO as GPIO
import threading
import signal
import atexit

class ButtonState:
    """Holds the current pressed state of each button"""
    def __init__(self):
        self.A = False
        self.B = False
        self.X = False
        self.Y = False

    def reset(self):
        self.A = self.B = self.X = self.Y = False

    def __repr__(self):
        return f"Buttons(A={self.A}, B={self.B}, X={self.X}, Y={self.Y})"


class InputHandler:
    def __init__(self):
        # Pirate Audio button pins
        self.BUTTONS = [5, 6, 16, 24]
        self.LABELS = ['A', 'B', 'X', 'Y']
        self.PIN_TO_LABEL = dict(zip(self.BUTTONS, self.LABELS))

        self.LAST_BUTTON = '_'
        self.state = ButtonState()

        # Setup GPIO
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Attach both falling (press) and rising (release) events
        for pin in self.BUTTONS:
            GPIO.add_event_detect(pin, GPIO.BOTH, callback=self._button_event, bouncetime=60)

        # Keep the original signal.pause() behavior in a daemon thread
        self._running = True
        thread = threading.Thread(target=self._wait_for_events, daemon=True)
        thread.start()

        atexit.register(self.cleanup)

    def _button_event(self, pin):
        """Called on any edge — check current level to determine press vs release"""
        label = self.PIN_TO_LABEL[pin]
        if GPIO.input(pin) == GPIO.LOW:   # FALLING → pressed
            print(label, "down")
            self.LAST_BUTTON = label
            setattr(self.state, label, True)
        else:                              # RISING → released
            print(label, "up")
            setattr(self.state, label, False)

    def _wait_for_events(self):
        """Original approach - keeps the script alive"""
        signal.pause()

    def cleanup(self):
        """Clean up GPIO on exit"""
        self._running = False
        try:
            GPIO.cleanup()
        except:
            pass

# Global instance (easy to import)
input_handler = InputHandler()