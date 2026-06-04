import os
os.environ["GPIOZERO_PIN_FACTORY"] = "lgpio"
from gpiozero import Button
import atexit
import time

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
        self.BUTTONS = [5, 6, 16, 24]
        self.LABELS = ['A', 'B', 'X', 'Y']
        self.PIN_TO_LABEL = dict(zip(self.BUTTONS, self.LABELS))
        self.LAST_BUTTON = '_'
        self.state = ButtonState()
        self.event_queue = []
        self._buttons = {}
        
        # Long press tracking
        self.press_times = {}  # Track when each button was pressed
        self.long_press_triggered = {}  # Track which buttons have triggered long press
        self.long_press_callbacks = {}  # Callbacks for long press events
        self.long_press_duration = 2.0  # 2 seconds
        
        for pin, label in self.PIN_TO_LABEL.items():
            b = Button(pin, pull_up=True, bounce_time=0.06)  # bounce_time in seconds
            b.when_pressed  = lambda l=label: self._pressed(l)
            b.when_released = lambda l=label: self._released(l)
            self._buttons[pin] = b
            self.long_press_triggered[label] = False
            print(f"DEBUG: Pin {pin} ({label}) OK")
        atexit.register(self.cleanup)
    
    def _pressed(self, label):
        self.LAST_BUTTON = label
        setattr(self.state, label, True)
        self.event_queue.append(label)
        # Record when button was pressed
        self.press_times[label] = time.time()
        self.long_press_triggered[label] = False
    
    def _released(self, label):
        setattr(self.state, label, False)
        # Clear press time when released
        if label in self.press_times:
            del self.press_times[label]
        self.long_press_triggered[label] = False
    
    def register_long_press(self, button_label, callback, duration=2.0):
        """
        Register a callback for when a button is held for a specified duration.
        
        Args:
            button_label: Button name ('A', 'B', 'X', 'Y')
            callback: Function to call when long press is detected
            duration: How long to hold in seconds (default 2.0)
        """
        label = str(button_label).upper()
        if label not in self.LABELS:
            raise ValueError(f"Unknown button label: {button_label}")
        self.long_press_callbacks[label] = callback
        self.long_press_duration = duration
    
    def check_long_presses(self):
        """
        Check for long presses and trigger callbacks.
        Call this regularly from your main loop.
        """
        current_time = time.time()
        for label, press_time in list(self.press_times.items()):
            # Check if button has been held long enough and callback hasn't been triggered yet
            if (current_time - press_time >= self.long_press_duration and 
                not self.long_press_triggered[label] and 
                label in self.long_press_callbacks):
                # Trigger the callback
                self.long_press_triggered[label] = True
                self.event_queue = [e for e in self.event_queue if e != label]
                self.long_press_callbacks[label]()

    def button_state(self, button_label):
        """Return whether the named button is currently pressed.
        Accepts case-insensitive labels like 'A', 'a', 'B', etc.
        """
        label = str(button_label).upper()
        if label not in self.LABELS:
            raise ValueError(f"Unknown button label: {button_label}")
        return getattr(self.state, label)
    
    def dequeue(self):
        """Get next event from queue, or None if empty."""
        return self.event_queue.pop(0) if self.event_queue else None
    
    def has_events(self):
        """Check if there are pending events."""
        return len(self.event_queue) > 0
    
    def process_events(self, callback):
        """Process events by calling callback(event_type, button) for each.
        Only dequeues events where callback returns True (handled).
        """
        while self.has_events():
            event = self.event_queue[0]
            if callback(*event):
                self.event_queue.pop(0)
            else:
                break
    
    def handle_button(self, button, callback):
        """If button was pressed, call callback and consume the event."""
        button = button.upper()
        for i, btn in enumerate(self.event_queue):
            if btn == button:
                callback()
                self.event_queue.pop(i)
                return True
        return False
    
    def cleanup(self):
        for b in self._buttons.values():
            b.close()

# Global instance (easy to import)
input_handler = InputHandler()