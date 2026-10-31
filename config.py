"""
Robert's settings. You can change these numbers and words safely.
After changing something, close Robert and start him again.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- Looks ----------
SPRITE_SHEET = os.path.join(BASE_DIR, "assets", "robert_sheet.png")
SPRITE_DIR = os.path.join(BASE_DIR, "sprites")
SHEET_COLUMNS = 8          # how many pictures across in the sheet
SHEET_ROWS = 9             # how many rows in the sheet
PET_SIZE = 140             # how big Robert is on screen (in pixels)
GAMES_ACTIVITY_SECONDS = 30

# row number (starting at 0) and how many pictures that row really has
ANIMATIONS = {
    "idle":      (0, 6),
    "run_right": (1, 8),
    "run_left":  (2, 7),
    "wave":      (3, 4),
    "jump":      (4, 5),
    "failed":    (5, 8),
    "wait":      (6, 6),   # listening
    "run":       (7, 6),   # working on a task
    "review":    (8, 6),   # thinking
}
# Sleeping uses the "lying down" pictures from the failed row: (row, column)
SLEEP_CELLS = [(5, 4), (5, 4), (5, 3), (5, 4)]

# how long each picture stays (milliseconds). Smaller = faster.
FRAME_MS = {
    "idle": 400, "run_right": 220, "run_left": 220, "wave": 300, "jump": 250,
    "failed": 300, "wait": 400, "run": 250, "review": 400, "sleep": 900,
    "smart": 650, "read_activity": 650, "games_activity": 450,
    "blush": 900,
    "compliment_amazing": 900, "compliment_great": 900,
    "compliment_beautiful": 900, "compliment_incredible": 900,
    "compliment_special": 900, "compliment_lucky": 900,
}
# these play once (or twice) and then Robert goes back to idle
ONESHOT_LOOPS = {"wave": 2, "jump": 2, "failed": 1}

# ---------- Behaviour ----------
WANDER = True              # walks around on his own
WALK_SPEED = 1             # pixels per step
SLEEP_AFTER_SECONDS = 180  # falls asleep after 3 minutes of nothing

# ---------- Ears (voice in) ----------
WAKE_WORD = "robert"
USE_GOOGLE_SPEECH = True   # better listening (needs internet). False = fully offline
LISTEN_WAIT_SECONDS = 6    # how long he waits for you to start talking
LISTEN_MAX_SECONDS = 15    # longest sentence he will listen to

# ---------- Mouth (voice out) ----------
SPEAK_ALOUD = True
SPEECH_RATE = 175

# ---------- Brain (Ollama) ----------
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"

# ---------- Places and files ----------
CITY = "Hinganghat"                  # used when you ask "weather" without a city
FALLBACK_LATLON = (20.55, 78.84)     # used if the city search fails
NOTES_FILE = os.path.join(BASE_DIR, "notes.txt")
CONTACTS_FILE = os.path.join(BASE_DIR, "contacts.json")
MODEL_FOLDER = os.path.join(BASE_DIR, "model")   # the Vosk voice model folder

# ---------- WhatsApp ----------
WHATSAPP_AUTO_SEND = True   # press Enter for you after the chat opens
WHATSAPP_WAIT_SECONDS = 8   # how long to wait for WhatsApp to open
