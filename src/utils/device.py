import socket

def get_pisugar_value(command: str) -> str:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect("/tmp/pisugar-server.sock")
        s.sendall((command + "\n").encode())
        return s.recv(1024).decode().strip()

def parse_value(response: str) -> str:
    if ": " in response:
        return response.split(": ", 1)[1]
    return response

def get_battery_status() -> dict:
    """Returns battery percentage, charging status, and voltage."""
    return {
        "battery_pct": float(parse_value(get_pisugar_value("get battery"))),
        "is_plugged":  parse_value(get_pisugar_value("get battery_power_plugged")).lower() == "true",
        "voltage":     float(parse_value(get_pisugar_value("get battery_v"))),
    }
