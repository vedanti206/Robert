"""Everything Robert can DO with his hands: open things, change volume, weather, notes, etc."""
import datetime
import json
import os
import re
import subprocess
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from typing import Optional

import config


@dataclass
class Reply:
    text: str                         # shown in the bubble
    state: str = "jump"               # animation after answering
    followup: bool = False            # True = Robert listens again right away
    speak_text: Optional[str] = None  # if different from text
    action: Optional[str] = None      # "quit" etc.
    activity_seconds: Optional[int] = None


def fail(text):
    return Reply(text, "failed")


# ---------------------------------------------------------------- time and date
def tell_time():
    now = datetime.datetime.now()
    return Reply("It is " + now.strftime("%I:%M %p").lstrip("0") + ".")


def tell_date():
    now = datetime.datetime.now()
    return Reply("Today is " + now.strftime("%A, %d %B %Y") + ".")


# ---------------------------------------------------------------- weather
WEATHER_WORDS = {
    0: "clear and sunny", 1: "mostly clear", 2: "partly cloudy", 3: "cloudy",
    45: "foggy", 48: "foggy", 51: "drizzling lightly", 53: "drizzling", 55: "drizzling heavily",
    61: "raining lightly", 63: "raining", 65: "raining heavily", 71: "snowing lightly",
    73: "snowing", 75: "snowing heavily", 80: "having rain showers", 81: "having rain showers",
    82: "having heavy rain showers", 95: "having a thunderstorm", 96: "having a thunderstorm with hail",
    99: "having a thunderstorm with hail",
}


def weather(city=None):
    import requests
    asked = city
    city = city or config.CITY
    try:
        geo = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                           params={"name": city, "count": 1}, timeout=8).json()
        results = geo.get("results")
        if results:
            lat, lon, name = results[0]["latitude"], results[0]["longitude"], results[0]["name"]
        elif not asked:
            lat, lon = config.FALLBACK_LATLON
            name = city
        else:
            return fail("I could not find a place called %s." % city)
        w = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": lat, "longitude": lon, "current_weather": "true",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto", "forecast_days": 1}, timeout=8).json()
        cur = w["current_weather"]
        daily = w.get("daily", {})
        text = "In %s it is %d degrees and %s." % (
            name, round(cur["temperature"]), WEATHER_WORDS.get(cur.get("weathercode"), "okay"))
        try:
            text += " Today: high %d, low %d." % (round(daily["temperature_2m_max"][0]),
                                                  round(daily["temperature_2m_min"][0]))
            rain = daily.get("precipitation_probability_max", [None])[0]
            if rain is not None:
                text += " Rain chance %d percent." % rain
        except Exception:
            pass
        return Reply(text)
    except Exception:
        return fail("I could not check the weather. Is the internet on?")


# ---------------------------------------------------------------- notes
def add_note(text):
    stamp = datetime.datetime.now().strftime("%d %b %Y %I:%M %p")
    with open(config.NOTES_FILE, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (stamp, text))
    return Reply("Okay! I wrote it in your notes.")


def read_notes(count=5):
    if not os.path.exists(config.NOTES_FILE):
        return Reply("You have no notes yet.", "idle")
    with open(config.NOTES_FILE, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines:
        return Reply("You have no notes yet.", "idle")
    last = lines[-count:]
    return Reply("Your last notes:\n" + "\n".join("- " + l for l in last),
                 speak_text="Here are your last notes. " + ". ".join(re.sub(r"^\[[^\]]*\]\s*", "", l) for l in last))


# ---------------------------------------------------------------- system control
def _keys(key, presses=1):
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.press(key, presses=presses, interval=0.01)


def volume_up(steps=5):
    _keys("volumeup", steps)
    return Reply("Volume up!")


def volume_down(steps=5):
    _keys("volumedown", steps)
    return Reply("Volume down!")


def volume_mute():
    _keys("volumemute")
    return Reply("Done. I pressed the mute button.")


def volume_set(percent):
    percent = max(0, min(100, percent))
    _keys("volumedown", 50)           # go to zero first
    _keys("volumeup", percent // 2)   # every press = 2 percent
    return Reply("Volume is now about %d percent." % percent)


def brightness_change(delta=None, absolute=None):
    try:
        import screen_brightness_control as sbc
        current = sbc.get_brightness()[0]
        new = absolute if absolute is not None else current + delta
        new = max(0, min(100, new))
        sbc.set_brightness(new)
        return Reply("Brightness is now %d percent." % new)
    except Exception:
        return fail("I could not change the brightness on this screen.")


def screenshot(bridge=None):
    from PIL import ImageGrab
    folder = os.path.join(os.path.expanduser("~"), "Pictures", "Robert Screenshots")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "robert_" + time.strftime("%Y%m%d_%H%M%S") + ".png")
    try:
        if bridge:
            bridge.hide_pet.emit()      # hide myself so I am not in the picture
            time.sleep(0.5)
        img = ImageGrab.grab(all_screens=True)
        img.save(path)
        return Reply("Screenshot saved in Pictures, in the Robert Screenshots folder.")
    except Exception:
        return fail("I could not take a screenshot.")
    finally:
        if bridge:
            bridge.show_pet.emit()


def lock_screen():
    import ctypes
    ctypes.windll.user32.LockWorkStation()
    return Reply("Locking the screen. Bye bye!", "idle")


def battery():
    try:
        import psutil
        b = psutil.sensors_battery()
        if b is None:
            return Reply("I cannot see a battery. Maybe this is a desktop PC.", "idle")
        text = "Battery is at %d percent, and it is %s." % (
            round(b.percent), "charging" if b.power_plugged else "not charging")
        if not b.power_plugged and b.secsleft and b.secsleft > 0:
            text += " About %d hours %d minutes left." % (b.secsleft // 3600, (b.secsleft % 3600) // 60)
        return Reply(text)
    except Exception:
        return fail("I could not read the battery.")


def media_key(key, message):
    _keys(key)
    return Reply(message)


# ---------------------------------------------------------------- clipboard
def get_clipboard():
    try:
        import pyperclip
        return (pyperclip.paste() or "").strip()
    except Exception:
        return ""


def read_clipboard():
    text = get_clipboard()
    if not text:
        return fail("Your clipboard is empty. Copy some text first.")
    short = text if len(text) <= 600 else text[:600] + " ..."
    return Reply(short, speak_text=short[:350])


# ---------------------------------------------------------------- YouTube
def play_youtube(query):
    import requests
    q = urllib.parse.quote_plus(query)
    try:
        html = requests.get("https://www.youtube.com/results?search_query=" + q,
                            headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"},
                            timeout=8).text
        m = re.search(r'"videoId":"([\w-]{11})"', html)
        if m:
            webbrowser.open("https://www.youtube.com/watch?v=" + m.group(1))
            return Reply("Playing %s on YouTube!" % query)
    except Exception:
        pass
    webbrowser.open("https://www.youtube.com/results?search_query=" + q)
    return Reply("I opened YouTube search for %s." % query)


# ---------------------------------------------------------------- open apps and sites
APPS = {
    "notepad": "notepad", "calculator": "calc", "paint": "mspaint", "chrome": "chrome",
    "google chrome": "chrome", "edge": "msedge", "explorer": "explorer",
    "file explorer": "explorer", "files": "explorer", "vs code": "code", "vscode": "code",
    "visual studio code": "code", "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
    "settings": "ms-settings:", "task manager": "taskmgr", "command prompt": "cmd", "cmd": "cmd",
    "terminal": "wt", "whatsapp": "whatsapp:", "spotify": "spotify:", "snipping tool": "snippingtool",
    "camera": "microsoft.windows.camera:", "clock": "ms-clock:",
}
SITES = {
    "youtube": "https://www.youtube.com", "google": "https://www.google.com",
    "gmail": "https://mail.google.com", "github": "https://github.com",
    "instagram": "https://www.instagram.com", "facebook": "https://www.facebook.com",
    "linkedin": "https://www.linkedin.com", "whatsapp web": "https://web.whatsapp.com",
    "maps": "https://maps.google.com", "drive": "https://drive.google.com",
    "chatgpt": "https://chat.openai.com", "stack overflow": "https://stackoverflow.com",
    "leetcode": "https://leetcode.com",
}


def open_thing(name):
    name = name.strip().lower().rstrip(".")
    name = re.sub(r"^(the|my|up)\s+", "", name)
    if name in SITES:
        webbrowser.open(SITES[name])
        return Reply("Opening %s!" % name)
    if name in APPS:
        try:
            subprocess.Popen('start "" "%s"' % APPS[name], shell=True)
            return Reply("Opening %s!" % name)
        except Exception:
            return fail("I could not open %s." % name)
    if re.match(r"^[\w.-]+\.(com|in|org|net|io|edu|dev|app)$", name):
        webbrowser.open("https://" + name)
        return Reply("Opening %s!" % name)
    return fail("I do not know how to open %s yet." % name)


# ---------------------------------------------------------------- WhatsApp
def load_contacts():
    try:
        with open(config.CONTACTS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return {k.lower(): v for k, v in data.items() if not k.startswith("_")}
    except Exception:
        return {}


def find_contact(name):
    contacts = load_contacts()
    name = name.lower().strip()
    if name in contacts:
        return name, contacts[name]
    for k, v in contacts.items():
        if k.startswith(name) or name.startswith(k):
            return k, v
    return None, None


def send_whatsapp(number, message):
    phone = re.sub(r"[^\d]", "", number)
    text = urllib.parse.quote(message)
    try:
        os.startfile("whatsapp://send?phone=%s&text=%s" % (phone, text))
    except Exception:
        webbrowser.open("https://wa.me/%s?text=%s" % (phone, text))
    if config.WHATSAPP_AUTO_SEND:
        time.sleep(config.WHATSAPP_WAIT_SECONDS)
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.press("enter")
        return Reply("Message sent!")
    return Reply("I opened the chat. Please press Enter to send.")


# ---------------------------------------------------------------- YouTube: skip ads
SKIP_IMG = os.path.join(config.BASE_DIR, "assets", "skip_button.png")


def foreground_title():
    """Name of the window you are using right now (for example the YouTube tab)."""
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        buf = ctypes.create_unicode_buffer(300)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 300)
        return buf.value
    except Exception:
        return ""


def try_click_skip():
    """Looks for the Skip button on the screen and clicks it. Returns True if clicked."""
    import pyautogui
    pyautogui.FAILSAFE = False
    try:
        pos = pyautogui.locateCenterOnScreen(SKIP_IMG, confidence=0.8)
    except Exception:
        return False
    if not pos:
        return False
    old = pyautogui.position()
    pyautogui.click(pos.x, pos.y)
    pyautogui.moveTo(old.x, old.y)
    return True


def skip_ad(bridge=None):
    if not os.path.exists(SKIP_IMG):
        return fail("I need a picture of the Skip button first. Save it as assets/skip_button.png. "
                    "The guide shows how.")
    try:
        import cv2  # noqa: F401  (needed to find the picture on the screen)
    except ImportError:
        return fail("I need one more part. In the terminal run: python -m pip install opencv-python")
    try:
        if bridge:
            bridge.hide_pet.emit()      # hide myself so I do not cover the button
            time.sleep(0.4)
        if try_click_skip():
            return Reply("Skipped the ad!")
        return fail("I cannot see a Skip button. Some ads cannot be skipped, "
                    "or the button is not ready yet. Try again in a few seconds.")
    finally:
        if bridge:
            bridge.show_pet.emit()
