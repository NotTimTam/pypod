import socket
from collections import deque

PISUGAR_SOCK = "/tmp/pisugar-server.sock"

BATTERY_STATUS_UNAVAILABLE = {
    "battery_pct": 0.0,
    "is_plugged":  False,
    "voltage":     0.0,
}

_voltage_history = deque(maxlen=10)

def get_pisugar_value(command: str) -> str | None:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(PISUGAR_SOCK)
            s.sendall((command + "\n").encode())
            return s.recv(1024).decode().strip()
    except (FileNotFoundError, ConnectionRefusedError, OSError, TimeoutError):
        print("DEBUG: Failed to collect pisugar battery stats")
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

    _voltage_history.append(float(parse_value(voltage)))

    battery_pct = float(parse_value(pct)),
    is_plugged  = parse_value(plugged).lower() == "true",
    voltage     = float(parse_value(voltage)),

    print(voltage, _voltage_history)

    return {
        "battery_pct": battery_pct,
        "is_plugged":  is_plugged,
        "voltage":     sum(_voltage_history) / len(_voltage_history) or voltage,
    }