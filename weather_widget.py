"""
WeatherDress Widget — стеклянный виджет в стиле Windows 7 Aero
3 размера: маленький / средний / большой
"""

import tkinter as tk
import threading
import requests
import json
import os
import ctypes
from datetime import datetime

# ─── Win32 ────────────────────────────────────────────────────
try:
    dwmapi  = ctypes.windll.dwmapi
    user32  = ctypes.windll.user32
except:
    dwmapi = user32 = None

class MARGINS(ctypes.Structure):
    _fields_ = [("l",ctypes.c_int),("r",ctypes.c_int),
                ("t",ctypes.c_int),("b",ctypes.c_int)]

HWND_TOPMOST   = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE     = 0x0002
SWP_NOSIZE     = 0x0001
SWP_NOACTIVATE = 0x0010

def set_topmost(hwnd, on):
    if user32:
        user32.SetWindowPos(hwnd, HWND_TOPMOST if on else HWND_NOTOPMOST,
                            0,0,0,0, SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE)

def enable_blur(hwnd):
    try:
        dwmapi.DwmExtendFrameIntoClientArea(hwnd,
            ctypes.byref(MARGINS(-1,-1,-1,-1)))
        return
    except: pass
    try:
        class ACCENT(ctypes.Structure):
            _fields_ = [("state",ctypes.c_int),("flags",ctypes.c_int),
                        ("color",ctypes.c_uint),("anim",ctypes.c_int)]
        class WCA(ctypes.Structure):
            _fields_ = [("attr",ctypes.c_int),("data",ctypes.c_void_p),
                        ("size",ctypes.c_uint)]
        acc  = ACCENT(3, 0, 0x99101820, 0)
        data = WCA(19, ctypes.cast(ctypes.byref(acc),ctypes.c_void_p),
                   ctypes.sizeof(acc))
        user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
    except: pass

# ─── Трей ─────────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageFont
    import pystray
    TRAY_OK = True
except ImportError:
    TRAY_OK = False

def make_tray_img(text="?"):
    img = Image.new("RGBA",(64,64),(0,0,0,0))
    d   = ImageDraw.Draw(img)
    d.ellipse([2,2,62,62], fill=(20,60,100,220))
    try:    fnt = ImageFont.truetype("arial.ttf", 20)
    except: fnt = None
    t = text[:4]
    if fnt:
        bb = d.textbbox((0,0),t,font=fnt)
        d.text(((64-(bb[2]-bb[0]))//2,(64-(bb[3]-bb[1]))//2-1),t,fill="white",font=fnt)
    else:
        d.text((8,18),t,fill="white")
    return img

# ─── Таблица стилей для трёх размеров ────────────────────────
#  Каждый ключ → (small, medium, large)
SIZES = {
    # ширина окна
    "W":            (240,  320,  420),
    # отступы
    "px":           (8,    12,   16),
    "hdr_h":        (24,   28,   32),
    # шрифты
    "hdr_font":     (("Segoe UI",8,"bold"),  ("Segoe UI",9,"bold"),  ("Segoe UI",10,"bold")),
    "btn_font":     (("Segoe UI",9,"bold"),  ("Segoe UI",10,"bold"), ("Segoe UI",11,"bold")),
    "icon_font":    (("Segoe UI Emoji",20),  ("Segoe UI Emoji",28),  ("Segoe UI Emoji",36)),
    "temp_font":    (("Segoe UI Light",24),  ("Segoe UI Light",32),  ("Segoe UI Light",42)),
    "feels_font":   (("Segoe UI",7),         ("Segoe UI",8),         ("Segoe UI",9)),
    "cond_font":    (("Segoe UI",8),         ("Segoe UI",9),         ("Segoe UI",10)),
    "oico_font":    (("Segoe UI Emoji",11),  ("Segoe UI Emoji",14),  ("Segoe UI Emoji",18)),
    "outfit_font":  (("Segoe UI Semibold",9),("Segoe UI Semibold",10),("Segoe UI Semibold",12)),
    "hint_font":    (("Segoe UI",7),         ("Segoe UI",8),         ("Segoe UI",9)),
    "fc_day_font":  (("Segoe UI",7),         ("Segoe UI",8),         ("Segoe UI",9)),
    "fc_ico_font":  (("Segoe UI Emoji",12),  ("Segoe UI Emoji",14),  ("Segoe UI Emoji",18)),
    "fc_t_font":    (("Segoe UI",7),         ("Segoe UI",8),         ("Segoe UI",9)),
    "time_font":    (("Segoe UI",6),         ("Segoe UI",7),         ("Segoe UI",8)),
    # показывать ли прогноз (только medium и large)
    "show_forecast":(False,                  True,                   True),
    # показывать ли строку ощущается (все)
    "show_feels":   (False,                  True,                   True),
    # показывать ли влажность в строке условий
    "show_humidity":(False,                  True,                   True),
}

IDX = {"small": 0, "medium": 1, "large": 2}

def S(key, size):
    return SIZES[key][IDX.get(size, 1)]

# ─── Конфиг ───────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".weatherdress_config.json")
UPDATE_INTERVAL = 30 * 60

DEFAULT_CONFIG = {
    "city":     "Helsinki",
    "units":    "metric",
    "widget_x": 40,
    "widget_y": 40,
    "topmost":  True,
    "size":     "medium",
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except: pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE,"w") as f:
        json.dump(cfg, f, indent=2)

# ─── Погода ───────────────────────────────────────────────────
def wmo_condition(code):
    if code==0:            return "Ясно"
    if code in(1,2):       return "Малооблачно"
    if code==3:            return "Облачно"
    if code in(45,48):     return "Туман"
    if code in(51,53,55):  return "Морось"
    if code in(61,63,65):  return "Дождь"
    if code in(71,73,75):  return "Снег"
    if code in(80,81,82):  return "Ливень"
    if code in(95,96,99):  return "Гроза"
    return "—"

def wmo_icon(code):
    if code==0:            return "☀"
    if code in(1,2):       return "⛅"
    if code==3:            return "☁"
    if code in(45,48):     return "🌫"
    if code in(51,53,55,61,63,65,80,81,82): return "🌧"
    if code in(71,73,75):  return "❄"
    if code in(95,96,99):  return "⛈"
    return "~"

def get_outfit(temp_c, condition=""):
    c    = condition.lower()
    rain = any(w in c for w in ["дождь","морось","ливень","гроза"])
    snow = any(w in c for w in ["снег"])
    wind = any(w in c for w in ["ветер"])
    if snow or temp_c<=-10: return "❄",  "Пуховик + термобельё + штаны", "Шапка, шарф, перчатки"
    if temp_c<=0:           return "🌨", "Пуховик + тёплые штаны",       "Шапка и шарф обязательны"
    if temp_c<=5:           return "🍂", "Пальто + джинсы",               "Шарф не помешает"
    if temp_c<=10:          return "🍁", "Куртка + тёплые штаны",         "Свитер под куртку"
    if temp_c<=15:
        if rain:            return "🌧", "Плащ / дождевик + джинсы",      "Зонт обязателен!"
        return                     "🧥", "Лёгкая куртка + джинсы",        "Без шапки уже можно"
    if temp_c<=20:
        if rain:            return "🌦", "Толстовка + джинсы",            "Зонт пригодится"
        if wind:            return "💨", "Толстовка + штаны",             "Ветровка спасёт"
        return                     "🌤", "Толстовка + джинсы",            "Отличная погода!"
    if temp_c<=25:
        if rain:            return "🌧", "Футболка + штаны",              "Зонт с собой"
        return                     "👕", "Футболка + лёгкие штаны",       "Солнечные очки 😎"
    if temp_c<=30:          return "☀",  "Футболка + шорты",              "Крем от солнца!"
    return                         "🔥", "Майка + шорты",                 "Пей воду, SPF обязателен"

def get_weather(city, units="metric"):
    try:
        geo = requests.get(
            f"https://geocoding-api.open-meteo.com/v1/search"
            f"?name={city}&count=1&language=ru", timeout=8).json()
        if not geo.get("results"):
            return None, f"Город '{city}' не найден"
        r = geo["results"][0]
        lat, lon = r["latitude"], r["longitude"]
        tu = "celsius" if units=="metric" else "fahrenheit"
        wx = requests.get(
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,apparent_temperature,weathercode,windspeed_10m,relative_humidity_2m"
            f"&daily=temperature_2m_max,temperature_2m_min,weathercode"
            f"&temperature_unit={tu}&windspeed_unit=kmh&timezone=auto&forecast_days=4",
            timeout=8).json()
        cur   = wx["current"]
        daily = wx.get("daily", {})
        temp_c = cur["temperature_2m"]
        if units != "metric":
            temp_c = (temp_c - 32) * 5/9
        sym = "°C" if units=="metric" else "°F"
        forecast = []
        times  = daily.get("time",[])
        t_max  = daily.get("temperature_2m_max",[])
        t_min  = daily.get("temperature_2m_min",[])
        wcodes = daily.get("weathercode",[])
        for i in range(1, min(4, len(times))):
            try:
                d = datetime.strptime(times[i], "%Y-%m-%d")
                forecast.append({
                    "day":  ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"][d.weekday()],
                    "icon": wmo_icon(wcodes[i]),
                    "max":  f"{round(t_max[i])}{sym}",
                    "min":  f"{round(t_min[i])}{sym}",
                })
            except: pass
        return {
            "city":     r.get("name", city),
            "temp":     round(cur["temperature_2m"]),
            "feels":    round(cur["apparent_temperature"]),
            "symbol":   sym,
            "condition":wmo_condition(cur["weathercode"]),
            "wcode":    cur["weathercode"],
            "wind":     round(cur["windspeed_10m"]),
            "humidity": round(cur.get("relative_humidity_2m", 0)),
            "temp_c":   temp_c,
            "forecast": forecast,
        }, None
    except requests.exceptions.ConnectionError:
        return None, "Нет интернета"
    except Exception as e:
        return None, str(e)[:50]


# ─── Виджет ───────────────────────────────────────────────────
class WeatherWidget:
    BG      = "#090f1a"
    ACCENT  = "#6ec6f5"
    WHITE   = "#ffffff"
    DIM     = "#b0cce8"
    HINT    = "#6a8aaa"
    BORDER  = "#1a3a5c"
    HDR_BG  = "#0d2040"
    FC_BG   = "#0a1828"

    def __init__(self):
        self.config   = load_config()
        self.weather  = None
        self.error    = None
        self._size    = self.config.get("size", "medium")
        self._drag_x  = self._drag_y = 0
        self._stop    = threading.Event()
        self._tray    = None
        self._visible = True
        self._fc_tiles = []

        self._build()
        threading.Thread(target=self._loop, daemon=True).start()

    # ══ Построение ═══════════════════════════════════════════
    def _build(self):
        sz = self._size
        W  = S("W", sz)
        x  = self.config.get("widget_x", 40)
        y  = self.config.get("widget_y", 40)

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=self.BG)
        self.root.wm_attributes("-alpha", 0.0)
        self.root.geometry(f"{W}x300+{x}+{y}")   # высота скорректируется

        self.root.update_idletasks()
        self._hwnd = self.root.winfo_id()
        enable_blur(self._hwnd)
        set_topmost(self._hwnd, self.config.get("topmost", True))

        self._build_ui(sz, W)
        self._bind_drag()

        if TRAY_OK and self._tray is None:
            self._start_tray()

        # авторазмер по содержимому
        self.root.update_idletasks()
        self.root.geometry(f"{W}x{self._outer.winfo_reqheight()}+{x}+{y}")
        self._fade()

    def _rebuild(self):
        """Перестраивает UI при смене размера (сохраняя окно)"""
        sz = self._size
        W  = S("W", sz)
        x  = self.root.winfo_x()
        y  = self.root.winfo_y()

        self._outer.destroy()
        self._fc_tiles = []
        self._build_ui(sz, W)
        self._bind_drag()

        self.root.geometry(f"{W}x300+{x}+{y}")
        self.root.update_idletasks()
        self.root.geometry(f"{W}x{self._outer.winfo_reqheight()}+{x}+{y}")

        if self.weather:
            self._refresh()

    def _autofit(self):
        W = S("W", self._size)
        self.root.update_idletasks()
        h = self._outer.winfo_reqheight()
        self.root.geometry(f"{W}x{h}+{self.root.winfo_x()}+{self.root.winfo_y()}")

    # ══ UI ═══════════════════════════════════════════════════
    def _build_ui(self, sz, W):
        px = S("px", sz)

        outer = tk.Frame(self.root, bg=self.BG,
                         highlightthickness=1,
                         highlightbackground=self.BORDER)
        outer.pack(fill="both", expand=True)
        self._outer = outer

        # ── Шапка ──────────────────────────────────────────
        hdr = tk.Frame(outer, bg=self.HDR_BG, height=S("hdr_h", sz))
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        self.lbl_city = tk.Label(hdr, text="⟳ загрузка...",
            bg=self.HDR_BG, fg=self.ACCENT,
            font=S("hdr_font", sz), anchor="w", padx=px)
        self.lbl_city.pack(side="left", fill="y")

        for txt, cmd, hover in [
            ("✕", self._quit,     "#ff5555"),
            ("_", self._minimize, self.ACCENT),
            ("⚙", self._settings, self.ACCENT),
        ]:
            b = tk.Label(hdr, text=txt, bg=self.HDR_BG, fg=self.DIM,
                         font=S("btn_font", sz), cursor="hand2", padx=6)
            b.pack(side="right", fill="y")
            b.bind("<Button-1>", lambda e, f=cmd: f())
            b.bind("<Enter>",    lambda e, w=b, c=hover: w.config(fg=c))
            b.bind("<Leave>",    lambda e, w=b: w.config(fg=self.DIM))

        # ── Иконка + температура ────────────────────────────
        top = tk.Frame(outer, bg=self.BG)
        top.pack(fill="x", padx=px, pady=(px, 0))

        self.lbl_icon = tk.Label(top, text="~",
            bg=self.BG, fg=self.ACCENT, font=S("icon_font", sz))
        self.lbl_icon.pack(side="left")

        col = tk.Frame(top, bg=self.BG)
        col.pack(side="left", padx=6)

        self.lbl_temp = tk.Label(col, text="--°",
            bg=self.BG, fg=self.WHITE, font=S("temp_font", sz), anchor="w")
        self.lbl_temp.pack(anchor="w")

        self.lbl_feels = tk.Label(col, text="",
            bg=self.BG, fg=self.HINT, font=S("feels_font", sz), anchor="w")
        if S("show_feels", sz):
            self.lbl_feels.pack(anchor="w")

        # ── Условия ─────────────────────────────────────────
        self.lbl_cond = tk.Label(outer, text="",
            bg=self.BG, fg=self.DIM, font=S("cond_font", sz), anchor="w")
        self.lbl_cond.pack(fill="x", padx=px, pady=(2, 0))

        # ── Разделитель ─────────────────────────────────────
        tk.Frame(outer, bg=self.BORDER, height=1).pack(
            fill="x", padx=px, pady=(5, 4))

        # ── Одежда ──────────────────────────────────────────
        orow = tk.Frame(outer, bg=self.BG)
        orow.pack(fill="x", padx=px, pady=(0, 2))

        self.lbl_oico = tk.Label(orow, text="",
            bg=self.BG, fg=self.ACCENT, font=S("oico_font", sz))
        self.lbl_oico.pack(side="left")

        self.lbl_outfit = tk.Label(orow, text="",
            bg=self.BG, fg=self.WHITE, font=S("outfit_font", sz), anchor="w")
        self.lbl_outfit.pack(side="left", padx=(4, 0))

        self.lbl_hint = tk.Label(outer, text="",
            bg=self.BG, fg=self.HINT, font=S("hint_font", sz), anchor="w")
        self.lbl_hint.pack(fill="x", padx=px + 20, pady=(0, 2))

        # ── Прогноз (только medium/large) ───────────────────
        self._fc_tiles = []
        if S("show_forecast", sz):
            tk.Frame(outer, bg=self.BORDER, height=1).pack(
                fill="x", padx=px, pady=(3, 4))

            fc_row = tk.Frame(outer, bg=self.BG)
            fc_row.pack(fill="x", padx=px, pady=(0, 4))

            for _ in range(3):
                tile = tk.Frame(fc_row, bg=self.FC_BG,
                                highlightthickness=1,
                                highlightbackground=self.BORDER)
                tile.pack(side="left", expand=True, fill="x", padx=2)

                d  = tk.Label(tile, text="—",  bg=self.FC_BG, fg=self.HINT,
                              font=S("fc_day_font", sz))
                ic = tk.Label(tile, text="~",  bg=self.FC_BG, fg=self.ACCENT,
                              font=S("fc_ico_font", sz))
                mx = tk.Label(tile, text="--", bg=self.FC_BG, fg=self.WHITE,
                              font=S("fc_t_font", sz))
                mn = tk.Label(tile, text="--", bg=self.FC_BG, fg=self.HINT,
                              font=S("fc_t_font", sz))
                for w in (d, ic, mx, mn):
                    w.pack()
                self._fc_tiles.append((d, ic, mx, mn))

        # ── Время ───────────────────────────────────────────
        self.lbl_time = tk.Label(outer, text="",
            bg=self.BG, fg="#2a4a6a", font=S("time_font", sz), anchor="e")
        self.lbl_time.pack(fill="x", padx=px, pady=(2, 4))

    # ══ Drag ═════════════════════════════════════════════════
    def _bind_drag(self):
        for w in [self._outer, self.lbl_city, self.lbl_temp, self.lbl_icon]:
            w.bind("<ButtonPress-1>",   self._ds)
            w.bind("<B1-Motion>",       self._dm)
            w.bind("<ButtonRelease-1>", self._de)

    def _ds(self,e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _dm(self,e):
        self.root.geometry(f"+{e.x_root-self._drag_x}+{e.y_root-self._drag_y}")

    def _de(self,e):
        self.config["widget_x"] = self.root.winfo_x()
        self.config["widget_y"] = self.root.winfo_y()
        save_config(self.config)

    # ══ Fade ═════════════════════════════════════════════════
    def _fade(self, a=0.0):
        if a < 0.88:
            self.root.wm_attributes("-alpha", a)
            self.root.after(14, self._fade, a+0.05)
        else:
            self.root.wm_attributes("-alpha", 0.88)

    # ══ Данные ═══════════════════════════════════════════════
    def _loop(self):
        while not self._stop.is_set():
            data, err = get_weather(self.config["city"], self.config["units"])
            self.weather, self.error = data, err
            self.root.after(0, self._refresh)
            self._stop.wait(UPDATE_INTERVAL)

    def _refresh(self):
        self.lbl_time.config(text=f"обновлено {datetime.now().strftime('%H:%M')}")
        sz = self._size

        if self.error:
            self.lbl_city.config(text="⚠ ошибка")
            self.lbl_temp.config(text="--°")
            self.lbl_cond.config(text=self.error)
            self.lbl_outfit.config(text="")
            self.lbl_hint.config(text="")
            self._autofit()
            return

        w = self.weather
        o_ico, o_main, o_hint = get_outfit(w["temp_c"], w["condition"])

        self.lbl_city.config(text=f"📍 {w['city']}")
        self.lbl_icon.config(text=wmo_icon(w["wcode"]))
        self.lbl_temp.config(text=f"{w['temp']}{w['symbol']}")
        self.lbl_feels.config(text=f"ощущается {w['feels']}{w['symbol']}")

        if S("show_humidity", sz):
            self.lbl_cond.config(
                text=f"{w['condition']}  ·  💨 {w['wind']} км/ч  ·  💧 {w['humidity']}%")
        else:
            self.lbl_cond.config(
                text=f"{w['condition']}  ·  💨 {w['wind']} км/ч")

        self.lbl_oico.config(text=o_ico)
        self.lbl_outfit.config(text=o_main)
        self.lbl_hint.config(text=o_hint)

        for i, tile in enumerate(self._fc_tiles):
            fc = w["forecast"][i] if i < len(w["forecast"]) else {}
            tile[0].config(text=fc.get("day","—"))
            tile[1].config(text=fc.get("icon","~"))
            tile[2].config(text=fc.get("max","--"))
            tile[3].config(text=fc.get("min","--"))

        if self._tray:
            try: self._tray.icon = make_tray_img(f"{w['temp']}°")
            except: pass

        self._autofit()

    # ══ Свернуть / развернуть ════════════════════════════════
    def _minimize(self):
        self._visible = False
        self.root.withdraw()

    def _show(self):
        self._visible = True
        self.root.deiconify()
        set_topmost(self._hwnd, self.config.get("topmost", True))
        self._fade()

    # ══ Трей ═════════════════════════════════════════════════
    def _start_tray(self):
        def on_show(icon, item): self.root.after(0, self._show)
        def on_quit(icon, item): self.root.after(0, self._quit)
        menu = pystray.Menu(
            pystray.MenuItem("Показать виджет", on_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", on_quit),
        )
        self._tray = pystray.Icon("WeatherDress", make_tray_img("..."),
                                  "", menu)
        self._tray_hwnd = None   # HWND окна pystray — нужен для Shell_NotifyIconGetRect

        threading.Thread(target=self._tray.run, daemon=True).start()

        # Ждём пока pystray создаст своё окно и берём его HWND
        # pystray называет класс окна: "WeatherDress<число>SystemTrayIcon"
        def grab_tray_hwnd():
            import time
            time.sleep(1.0)
            found_hwnd = None
            found_uid  = None

            # Перечисляем все окна, ищем по префиксу класса
            buf = ctypes.create_unicode_buffer(512)
            result = ctypes.c_void_p(None)

            WNDENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

            def cb(hwnd, _):
                nonlocal found_hwnd
                ctypes.windll.user32.GetClassNameW(hwnd, buf, 512)
                cls = buf.value
                if cls.startswith("WeatherDress") and "SystemTrayIcon" in cls:
                    found_hwnd = hwnd
                    return False   # стоп — нашли
                return True

            ctypes.windll.user32.EnumWindows(WNDENUMPROC(cb), 0)

            if found_hwnd:
                # Перебираем uID 0..9 — ищем тот что даёт S_OK
                class NII(ctypes.Structure):
                    _fields_ = [("cbSize",ctypes.c_uint),
                                ("hWnd",  ctypes.c_void_p),
                                ("uID",   ctypes.c_uint),
                                ("guid",  ctypes.c_byte*16)]
                class RECT2(ctypes.Structure):
                    _fields_ = [("l",ctypes.c_long),("t",ctypes.c_long),
                                ("r",ctypes.c_long),("b",ctypes.c_long)]
                for uid in range(10):
                    nii = NII()
                    nii.cbSize = ctypes.sizeof(NII)
                    nii.hWnd   = found_hwnd
                    nii.uID    = uid
                    r = RECT2()
                    hr = ctypes.windll.shell32.Shell_NotifyIconGetRect(
                        ctypes.byref(nii), ctypes.byref(r))
                    if hr == 0:
                        found_uid = uid
                        break
                self._tray_hwnd = found_hwnd
                self._tray_uid  = found_uid if found_uid is not None else 0
            else:
                self._tray_hwnd = None
                self._tray_uid  = 0

        threading.Thread(target=grab_tray_hwnd, daemon=True).start()

        # Всплывающее окно при наведении на иконку трея
        self._popup = None
        self._popup_visible = False
        threading.Thread(target=self._hover_loop, daemon=True).start()

    def _hover_loop(self):
        """Следит за курсором — показывает popup только над нашей иконкой трея"""

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        class RECT(ctypes.Structure):
            _fields_ = [("left",ctypes.c_long),("top",ctypes.c_long),
                        ("right",ctypes.c_long),("bottom",ctypes.c_long)]

        # NOTIFYICONIDENTIFIER для Shell_NotifyIconGetRect
        class NOTIFYICONIDENTIFIER(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("hWnd",   ctypes.c_void_p),
                ("uID",    ctypes.c_uint),
                ("guidItem", ctypes.c_byte * 16),
            ]

        shell32 = ctypes.windll.shell32

        def get_icon_rect():
            try:
                hwnd = self._tray_hwnd
                uid  = getattr(self, '_tray_uid', 0)
                if not hwnd:
                    return None
                nii = NOTIFYICONIDENTIFIER()
                nii.cbSize = ctypes.sizeof(NOTIFYICONIDENTIFIER)
                nii.hWnd   = hwnd
                nii.uID    = uid
                r = RECT()
                hr = shell32.Shell_NotifyIconGetRect(
                    ctypes.byref(nii), ctypes.byref(r))
                if hr == 0:
                    return r
            except:
                pass
            return None

        over = False
        while not self._stop.is_set():
            try:
                pt = POINT()
                user32.GetCursorPos(ctypes.byref(pt))

                ir = get_icon_rect()
                if ir:
                    on_icon = (ir.left <= pt.x <= ir.right and
                               ir.top  <= pt.y <= ir.bottom)
                else:
                    on_icon = False

                if on_icon and not over:
                    over = True
                    if not self._visible:
                        self.root.after(0, self._show_popup, pt.x, pt.y)
                elif not on_icon and over:
                    over = False
                    self.root.after(0, self._hide_popup)
            except:
                pass
            self._stop.wait(0.1)

    def _show_popup(self, mx, my):
        """Маленькое стеклянное окно с погодой — появляется над иконкой трея"""
        if self._visible:
            return
        if self._popup and self._popup.winfo_exists():
            return

        w = self.weather
        if not w:
            return

        o_ico, o_main, _ = get_outfit(w["temp_c"], w["condition"])

        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.wm_attributes("-topmost", True)
        popup.wm_attributes("-alpha", 0.0)
        popup.configure(bg="#090f1a")

        frame = tk.Frame(popup, bg="#090f1a",
                         highlightthickness=1,
                         highlightbackground="#1a3a5c")
        frame.pack()

        # Иконка + температура
        r1 = tk.Frame(frame, bg="#090f1a")
        r1.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(r1, text=wmo_icon(w["wcode"]),
                 bg="#090f1a", fg="#6ec6f5",
                 font=("Segoe UI Emoji", 18)).pack(side="left")
        tk.Label(r1, text=f"  {w['temp']}{w['symbol']}",
                 bg="#090f1a", fg="#ffffff",
                 font=("Segoe UI Light", 22)).pack(side="left")

        # Условия
        tk.Label(frame, text=f"{w['condition']}  ·  💨 {w['wind']} км/ч",
                 bg="#090f1a", fg="#b0cce8",
                 font=("Segoe UI", 9)).pack(padx=10, pady=(0, 4))

        # Разделитель
        tk.Frame(frame, bg="#1a3a5c", height=1).pack(fill="x", padx=8)

        # Одежда
        r3 = tk.Frame(frame, bg="#090f1a")
        r3.pack(fill="x", padx=10, pady=(5, 8))
        tk.Label(r3, text=o_ico,
                 bg="#090f1a", fg="#6ec6f5",
                 font=("Segoe UI Emoji", 13)).pack(side="left")
        tk.Label(r3, text=f"  {o_main}",
                 bg="#090f1a", fg="#ffffff",
                 font=("Segoe UI Semibold", 10)).pack(side="left")

        popup.update_idletasks()
        pw = popup.winfo_reqwidth()
        ph = popup.winfo_reqheight()
        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()

        px = max(0, min(mx - pw // 2, sw - pw))
        py = (my - ph - 12) if my > sh // 2 else (my + 20)

        popup.geometry(f"+{px}+{py}")
        self._popup = popup
        self._popup_visible = True

        popup.update_idletasks()
        enable_blur(popup.winfo_id())
        self._popup_fade(0.0)

    def _popup_fade(self, a=0.0):
        if self._popup and self._popup.winfo_exists():
            if a < 0.92:
                self._popup.wm_attributes("-alpha", a)
                self.root.after(12, self._popup_fade, a + 0.07)
            else:
                self._popup.wm_attributes("-alpha", 0.92)

    def _hide_popup(self):
        if self._popup:
            try: self._popup.destroy()
            except: pass
            self._popup = None
            self._popup_visible = False

    # ══ Настройки ════════════════════════════════════════════
    def _settings(self):
        win = tk.Toplevel(self.root)
        win.title("WeatherDress — Настройки")
        win.geometry("320x245")
        win.configure(bg="#0d1e30")
        win.resizable(False, False)
        win.wm_attributes("-topmost", True)

        def lbl(text, y):
            tk.Label(win, text=text, bg="#0d1e30", fg=self.DIM,
                     font=("Segoe UI", 10)).place(x=20, y=y)

        # Город
        lbl("Город:", 22)
        city_var = tk.StringVar(value=self.config["city"])
        tk.Entry(win, textvariable=city_var, bg="#1a3a5c", fg="white",
                 insertbackground="white", font=("Segoe UI", 11),
                 bd=0, relief="flat", width=17).place(x=90, y=20)

        # Единицы
        lbl("Единицы:", 62)
        units_var = tk.StringVar(value=self.config["units"])
        for i,(txt,val) in enumerate([("°C","metric"),("°F","imperial")]):
            tk.Radiobutton(win, text=txt, variable=units_var, value=val,
                bg="#0d1e30", fg=self.WHITE, selectcolor="#1a3a5c",
                font=("Segoe UI", 10), activebackground="#0d1e30"
            ).place(x=100+i*65, y=59)

        # Поверх всех
        lbl("Поверх\nокон:", 102)
        topmost_var = tk.BooleanVar(value=self.config.get("topmost", True))
        tk.Checkbutton(win, text="Включено", variable=topmost_var,
            bg="#0d1e30", fg=self.WHITE, selectcolor="#1a3a5c",
            activebackground="#0d1e30", activeforeground=self.WHITE,
            font=("Segoe UI", 10)).place(x=100, y=100)

        # Размер — 3 кнопки с визуальным превью
        lbl("Размер:", 148)
        size_var = tk.StringVar(value=self._size)
        sizes = [
            ("small",  "S\nМаленький"),
            ("medium", "M\nСредний"),
            ("large",  "L\nБольшой"),
        ]
        for i, (val, caption) in enumerate(sizes):
            rb = tk.Radiobutton(win, text=caption, variable=size_var, value=val,
                bg="#0d1e30", fg=self.WHITE, selectcolor="#1a4a7a",
                font=("Segoe UI", 9), activebackground="#0d1e30",
                justify="center", indicatoron=0,
                width=7, height=2,
                relief="flat", bd=1,
            )
            rb.place(x=90 + i*75, y=143)

        def apply():
            self.config["city"]    = city_var.get().strip() or self.config["city"]
            self.config["units"]   = units_var.get()
            self.config["topmost"] = topmost_var.get()
            new_size               = size_var.get()
            save_config(self.config)
            set_topmost(self._hwnd, self.config["topmost"])
            win.destroy()
            size_changed = new_size != self._size
            self._size = new_size
            self.config["size"] = new_size
            save_config(self.config)
            if size_changed:
                self._rebuild()
            # Перезапустить цикл данных
            self._stop.set()
            self._stop = threading.Event()
            threading.Thread(target=self._loop, daemon=True).start()

        tk.Button(win, text="  Применить  ", command=apply,
            bg=self.ACCENT, fg="#001828", font=("Segoe UI Semibold", 10),
            relief="flat", cursor="hand2", bd=0).place(x=20, y=200)
        tk.Button(win, text="  Отмена  ", command=win.destroy,
            bg="#1a3a5c", fg=self.WHITE, font=("Segoe UI", 10),
            relief="flat", cursor="hand2", bd=0).place(x=185, y=200)

    # ══ Выход ════════════════════════════════════════════════
    def _quit(self):
        self._stop.set()
        if self._tray:
            try: self._tray.stop()
            except: pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ─── Точка входа ──────────────────────────────────────────────
if __name__ == "__main__":
    try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    WeatherWidget().run()
