import socket
import threading
import time
from collections import deque

PISUGAR_SOCK = "/tmp/pisugar-server.sock"

UPDATE_INTERVAL = 20  # seconds (adjust 15–30 as needed)

BATTERY_STATUS_UNAVAILABLE = {
    "battery_pct": 0.0,
    "is_plugged": False,
    "voltage": 0.0,
}

# voltage smoothing
_voltage_history = deque(maxlen=10)

# shared cache
battery_cache = BATTERY_STATUS_UNAVAILABLE.copy()
_cache_lock = threading.Lock()


def get_pisugar_value(command: str) -> str | None:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(PISUGAR_SOCK)
            s.sendall((command + "\n").encode())
            return s.recv(1024).decode().strip()
    except (FileNotFoundError, ConnectionRefusedError, OSError, TimeoutError):
        return None


def parse_value(response: str) -> str:
    if response and ": " in response:
        return response.split(": ", 1)[1]
    return response or ""


def _battery_updater():
    global battery_cache

    while True:
        try:
            pct = get_pisugar_value("get battery")
            plugged = get_pisugar_value("get battery_power_plugged")
            voltage = get_pisugar_value("get battery_v")

            if None in (pct, plugged, voltage):
                time.sleep(UPDATE_INTERVAL)
                continue

            pct_val = float(parse_value(pct))
            is_plugged = parse_value(plugged).lower() == "true"
            voltage_raw = float(parse_value(voltage))

            _voltage_history.append(voltage_raw)
            avg_voltage = sum(_voltage_history) / len(_voltage_history)

            new_data = {
                "battery_pct": pct_val,
                "is_plugged": is_plugged,
                "voltage": avg_voltage,
            }

            with _cache_lock:
                battery_cache = new_data

        except Exception:
            # never crash the thread
            pass

        time.sleep(UPDATE_INTERVAL)


def start_device_thread():
    """Call once at app startup."""
    t = threading.Thread(target=_battery_updater, daemon=True)
    t.start()
    return t


def get_battery_status():
    """Fast, non-blocking getter for render loop."""
    with _cache_lock:
        return battery_cache.copy()