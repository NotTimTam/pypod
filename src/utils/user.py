import os
import pwd

def get_current_user():
    """Returns the current username reliably"""
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except Exception:
        return os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'