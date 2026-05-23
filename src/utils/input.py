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

        # Setup GPIO (same as your original)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Attach both falling (press) and rising (release) events
        for pin in self.BUTTONS:
            GPIO.add_event_detect(pin, GPIO.FALLING, 
                                callback=self._button_pressed, bouncetime=60)
            GPIO.add_event_detect(pin, GPIO.RISING, 
                                callback=self._button_released, bouncetime=60)

        # Keep the original signal.pause() behavior in a daemon thread
        self._running = True
        thread = threading.Thread(target=self._wait_for_events, daemon=True)
        thread.start()

        atexit.register(self.cleanup)

    def _button_pressed(self, pin):
        """Called when button is pressed (FALLING edge)"""
        label = self.PIN_TO_LABEL[pin]
        self.LAST_BUTTON = label
        setattr(self.state, label, True)

    def _button_released(self, pin):
        """Called when button is released (RISING edge)"""
        label = self.PIN_TO_LABEL[pin]
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