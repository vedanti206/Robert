"""
robert_sprites.py  -  gives Robert the Shiba puppy look + moods.

How to use inside your Robert app (3 steps):
    from robert_sprites import RobertSprites, mood_for_text
    pet = RobertSprites(root, label, folder="sprites", height=150)   # root = Tk(), label = tk.Label
    pet.set_mood("hello")                                            # change his picture/animation
    pet.set_mood(mood_for_text("open youtube and play music"))       # or pick mood from a sentence
"""
import os
import random
from PIL import Image

KEY = "#ff00fe"          # this colour becomes see-through in the Tkinter window (never used in sprites)

# mood  ->  list of sprite names (they play one after another like an animation)
MOODS = {
    "idle":      ["happy_sit", "hi_sit", "happy_blush", "hi_sit"],
    "hello":     ["hi_big", "hi_wave", "hi_shy", "hi_wave"],            # wake word "Robert" heard / greeting
    "listening": ["hi_bubble"],                                         # waiting for your command
    "thinking":  ["idea"],                                              # AI is making an answer
    "study":     ["read1", "read2", "read_glasses1", "read_glasses2", "idea"],
    "study_long":["read_lying", "read_sleepy"],
    "music":     ["cool"],                                              # YouTube / music / skip track
    "focus":     ["chess1", "chess2", "chess3", "chess_happy1"],        # Pomodoro / timer running
    "win":       ["chess_cheer", "chess_win", "chess_wink"],            # timer finished / task done
    "break":     ["coffee"],                                            # Pomodoro break
    "sleep":     ["sleep", "blanket"],                                  # idle for a long time
    "love":      ["hug_heart", "amazing", "special", "doing_great", "beautiful", "incredible", "lucky"],
    "kiss":      ["muah", "kiss1", "kiss2", "kiss_face"],
    "cute":      ["love_lying", "flower", "flower_crown"],
    "done":      ["stay_happy", "heart_bubble"],                        # command finished
}

# simple keyword rules: first match wins
_RULES = [
    ("sleep",    ["good night", "go to sleep", "sleep", "bye"]),
    ("music",    ["music", "song", "youtube", "play", "skip", "volume", "spotify"]),
    ("break",    ["break", "coffee", "tea", "rest"]),
    ("focus",    ["pomodoro", "focus", "timer", "countdown", "stopwatch"]),
    ("study",    ["study", "explain", "read", "notes", "summar", "translate", "what is", "define", "learn"]),
    ("win",      ["finished", "completed", "well done", "congrat", "i passed"]),
    ("kiss",     ["love you", "kiss", "muah", "miss you"]),
    ("love",     ["thank", "good boy", "good robert", "nice", "great", "cute", "best"]),
    ("hello",    ["hello", "hi ", "hey", "good morning", "robert"]),
]

def mood_for_text(text, default="done"):
    t = " " + text.lower().strip() + " "
    for mood, words in _RULES:
        if any(w in t for w in words):
            return mood
    return default


class RobertSprites:
    def __init__(self, root, label, folder="sprites", height=150, frame_ms=450):
        from PIL import ImageTk                       # imported here so the file can be tested without Tk
        self._ImageTk = ImageTk
        self.root, self.label = root, label
        self.height, self.frame_ms = height, frame_ms
        self.mood, self._frames, self._i, self._job = None, [], 0, None
        self._cache = {}
        self._folder = folder
        label.configure(bg=KEY, bd=0, highlightthickness=0)

    # ---- picture loading (resize + make background see-through, no halo) ----
    def _photo(self, name):
        if name in self._cache:
            return self._cache[name]
        im = Image.open(os.path.join(self._folder, name + ".png")).convert("RGBA")
        w = max(1, round(im.width * self.height / im.height))
        im = im.resize((w, self.height), Image.LANCZOS)
        key = Image.new("RGBA", im.size, KEY)
        alpha = im.getchannel("A").point(lambda v: 255 if v >= 128 else 0)   # hard edge = Windows safe
        key.paste(im, (0, 0), alpha)
        photo = self._ImageTk.PhotoImage(key.convert("RGB"))
        self._cache[name] = photo
        return photo

    # ---- moods ----
    def set_mood(self, mood, hold_ms=None, then="idle"):
        """Show a mood. If hold_ms is given, go to `then` after that many milliseconds."""
        if mood not in MOODS:
            mood = "idle"
        if self._job:
            self.root.after_cancel(self._job)
        self.mood = mood
        names = MOODS[mood][:]
        if mood in ("love", "kiss", "cute", "done", "win"):
            random.shuffle(names)                      # a different cute picture each time
        self._frames = [self._photo(n) for n in names]
        self._i = 0
        self._tick()
        if hold_ms:
            self.root.after(hold_ms, lambda: self.mood == mood and self.set_mood(then))

    def _tick(self):
        photo = self._frames[self._i % len(self._frames)]
        self.label.configure(image=photo)
        self.label.image = photo                       # keep a reference (Tkinter needs it)
        self._i += 1
        if len(self._frames) > 1:
            self._job = self.root.after(self.frame_ms, self._tick)
