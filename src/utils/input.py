import socket
from collections import deque

PISUGAR_SOCK = "/tmp/pisugar-server.sock"

BATTERY_STATUS_UNAVAILABLE = {
    "battery_pct": 0.0,
    "is_plugged":  False,
    "voltage":     0.0,
}

_SMOOTHING_SAMPLES = 10
_pct_history     = deque(maxlen=_SMOOTHING_SAMPLES)
_voltage_history = deque(maxlen=_SMOOTHING_SAMPLES)

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
    if ": " in response:
        return response.split(": ", 1)[1]
    return response

def get_battery_status() -> dict:
    """Returns smoothed battery percentage, charging status, and voltage."""
    pct     = get_pisugar_value("get battery")
    plugged = get_pisugar_value("get battery_power_plugged")
    voltage = get_pisugar_value("get battery_v")

    if None in (pct, plugged, voltage):
        return BATTERY_STATUS_UNAVAILABLE

    _pct_history.append(float(parse_value(pct)))
    _voltage_history.append(float(parse_value(voltage)))

    return {
        "battery_pct": sum(_pct_history) / len(_pct_history),
        "is_plugged":  parse_value(plugged).lower() == "true",
        "voltage":     sum(_voltage_history) / len(_voltage_history),
    }