"""Windows keyboard injection helpers using Unicode SendInput.

Unicode packets avoid translating replacement characters through the active
keyboard layout. Importing this module is safe on non-Windows test runners;
the Win32 API is resolved only when a helper is called.
"""
import ctypes
from ctypes import wintypes

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_BACK = 0x08
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", INPUT_UNION)]


def _send(events):
    if not events:
        return
    if not hasattr(ctypes, "windll"):
        raise OSError("SendInput is available only on Windows")
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    arr = (INPUT * len(events))(*events)
    sent = user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))
    if sent != len(events):
        raise ctypes.WinError(ctypes.get_last_error())
    return sent


def _key_event(vk=0, scan=0, flags=0):
    item = INPUT()
    item.type = INPUT_KEYBOARD
    item.ki = KEYBDINPUT(vk, scan, flags, 0, 0)
    return item


def send_backspaces(count):
    """Send count Backspace down/up pairs without touching Caps Lock."""
    events = []
    for _ in range(max(0, int(count))):
        events.append(_key_event(vk=VK_BACK))
        events.append(_key_event(vk=VK_BACK, flags=KEYEVENTF_KEYUP))
    return _send(events)


def send_unicode_text(value):
    """Type literal Unicode characters using VK_PACKET, independent of layout."""
    events = []
    for char in str(value):
        code = ord(char)
        if code <= 0xFFFF:
            events.append(_key_event(scan=code, flags=KEYEVENTF_UNICODE))
            events.append(_key_event(scan=code, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
        else:
            code -= 0x10000
            high = 0xD800 + (code >> 10)
            low = 0xDC00 + (code & 0x3FF)
            for unit in (high, low):
                events.append(_key_event(scan=unit, flags=KEYEVENTF_UNICODE))
                events.append(_key_event(scan=unit, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
    return _send(events)


def key_state(vk):
    """Return the low-bit toggle state for Caps Lock, or high-bit down state."""
    if not hasattr(ctypes, "windll"):
        return False
    return bool(ctypes.windll.user32.GetKeyState(int(vk)) & 1)
