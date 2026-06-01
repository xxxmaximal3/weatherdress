"""
Запусти этот скрипт пока weather_widget.py работает в фоне.
Он найдёт HWND иконки трея и напечатает её координаты.
"""
import ctypes
import time

user32  = ctypes.windll.user32
shell32 = ctypes.windll.shell32

class RECT(ctypes.Structure):
    _fields_ = [("left",ctypes.c_long),("top",ctypes.c_long),
                ("right",ctypes.c_long),("bottom",ctypes.c_long)]

class POINT(ctypes.Structure):
    _fields_ = [("x",ctypes.c_long),("y",ctypes.c_long)]

class NOTIFYICONIDENTIFIER(ctypes.Structure):
    _fields_ = [
        ("cbSize",   ctypes.c_uint),
        ("hWnd",     ctypes.c_void_p),
        ("uID",      ctypes.c_uint),
        ("guidItem", ctypes.c_byte * 16),
    ]

# 1. Ищем все окна с именем класса "WeatherDress"
print("=== FindWindow 'WeatherDress' ===")
hwnd = user32.FindWindowW("WeatherDress", None)
print(f"  by class: {hwnd} (0x{hwnd:x})" if hwnd else "  by class: NOT FOUND")
hwnd2 = user32.FindWindowW(None, "WeatherDress")
print(f"  by title: {hwnd2} (0x{hwnd2:x})" if hwnd2 else "  by title: NOT FOUND")

# 2. Перечисляем все окна — ищем что у pystray
print("\n=== All top-level windows (hidden too) ===")
found = []
def enum_cb(hwnd, lparam):
    buf = ctypes.create_unicode_buffer(256)
    cls = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    user32.GetClassNameW(hwnd, cls, 256)
    title = buf.value
    klass = cls.value
    if any(x in (title+klass).lower() for x in ["weather","tray","pystray"]):
        found.append((hwnd, klass, title))
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
cb = WNDENUMPROC(enum_cb)
user32.EnumWindows(cb, 0)
for h, c, t in found:
    print(f"  hwnd=0x{h:x}  class='{c}'  title='{t}'")
if not found:
    print("  (ничего не найдено)")

# 3. Пробуем Shell_NotifyIconGetRect с разными hWnd и uID
print("\n=== Shell_NotifyIconGetRect probe ===")
candidates = [(hwnd, 0), (hwnd, 1), (hwnd2, 0), (hwnd2, 1)]
for h, uid in candidates:
    if not h:
        continue
    nii = NOTIFYICONIDENTIFIER()
    nii.cbSize = ctypes.sizeof(NOTIFYICONIDENTIFIER)
    nii.hWnd   = h
    nii.uID    = uid
    r = RECT()
    hr = shell32.Shell_NotifyIconGetRect(ctypes.byref(nii), ctypes.byref(r))
    print(f"  hWnd=0x{h:x} uID={uid} → hr=0x{hr:08x}  rect=({r.left},{r.top},{r.right},{r.bottom})")

# 4. Текущая позиция курсора для сравнения
pt = POINT()
user32.GetCursorPos(ctypes.byref(pt))
print(f"\nКурсор сейчас: ({pt.x}, {pt.y})")
print("Разрешение экрана:", user32.GetSystemMetrics(0), "x", user32.GetSystemMetrics(1))
