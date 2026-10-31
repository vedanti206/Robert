"""Timers, reminders and the Pomodoro study timer."""
import re
import threading
import time

ONES = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
        "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
        "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
        "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
        "seventy": 70, "eighty": 80, "ninety": 90}


def normalize_numbers(s):
    """'twenty five minutes' -> '25 minutes'"""
    tokens = s.lower().replace("-", " ").split()
    out, cur = [], None
    for tok in tokens:
        if tok in ONES:
            cur = (cur or 0) + ONES[tok]
        elif tok in TENS:
            cur = (cur or 0) + TENS[tok]
        elif tok == "hundred" and cur:
            cur *= 100
        else:
            if cur is not None:
                out.append(str(cur))
                cur = None
            out.append(tok)
    if cur is not None:
        out.append(str(cur))
    return " ".join(out)


def parse_duration(s):
    """Finds a time like '10 minutes' or 'half an hour' in a sentence. Returns seconds or None."""
    s = normalize_numbers(s)
    s = re.sub(r"\bhalf an? hour\b|\bhalf hour\b", "30 minutes", s)
    s = re.sub(r"\ban hour and a half\b", "90 minutes", s)
    s = re.sub(r"\b(?:an|a) hour\b", "1 hour", s)
    s = re.sub(r"\ba minute\b", "1 minute", s)
    s = re.sub(r"\ba second\b", "1 second", s)
    total, found = 0.0, False
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|minutes?|mins?|seconds?|secs?)\b", s):
        total += float(num) * {"h": 3600, "m": 60, "s": 1}[unit[0]]
        found = True
    return int(total) if found and total > 0 else None


def say_duration(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append("%d hour%s" % (h, "" if h == 1 else "s"))
    if m:
        parts.append("%d minute%s" % (m, "" if m == 1 else "s"))
    if s and not h:
        parts.append("%d second%s" % (s, "" if s == 1 else "s"))
    return " ".join(parts) or "0 seconds"


class Scheduler:
    def __init__(self, notify):
        self.notify = notify          # notify(text, state) - shows and speaks
        self.timers = []              # (Timer, end_time, label)
        self.pomo = None
        self._pomo_timer = None
        self._lock = threading.Lock()

    # ----- simple timers and reminders -----
    def add(self, seconds, message, label):
        t = threading.Timer(seconds, self._fire, args=(message,))
        t.daemon = True
        with self._lock:
            self.timers.append((t, time.time() + seconds, label))
        t.start()

    def _fire(self, message):
        now = time.time()
        with self._lock:
            self.timers = [x for x in self.timers if x[1] > now + 0.5]
        self.notify(message, "wave")

    def cancel_all(self):
        with self._lock:
            n = len(self.timers)
            for t, _, _ in self.timers:
                t.cancel()
            self.timers = []
        return n

    def pending(self):
        now = time.time()
        with self._lock:
            return [(label, max(0, int(end - now))) for _, end, label in self.timers]

    # ----- Pomodoro -----
    def start_pomodoro(self, work=25, short=5, long=15, rounds=4):
        self.stop_pomodoro()
        self.pomo = {"round": 1, "phase": "work", "rounds": rounds,
                     "work": work, "short": short, "long": long, "ends": 0}
        self._pomo_begin()

    def _pomo_begin(self):
        p = self.pomo
        mins = {"work": p["work"], "short": p["short"], "long": p["long"]}[p["phase"]]
        p["ends"] = time.time() + mins * 60
        self._pomo_timer = threading.Timer(mins * 60, self._pomo_next)
        self._pomo_timer.daemon = True
        self._pomo_timer.start()

    def _pomo_next(self):
        p = self.pomo
        if not p:
            return
        if p["phase"] == "work":
            if p["round"] >= p["rounds"]:
                p["phase"] = "long"
                self.notify("Round %d done! Take a long break: %d minutes."
                            % (p["round"], p["long"]), "jump")
            else:
                p["phase"] = "short"
                self.notify("Round %d done! Take a short break: %d minutes."
                            % (p["round"], p["short"]), "jump")
            self._pomo_begin()
        elif p["phase"] == "short":
            p["round"] += 1
            p["phase"] = "work"
            self.notify("Break is over! Round %d. Let us study for %d minutes."
                        % (p["round"], p["work"]), "wave")
            self._pomo_begin()
        else:
            self.pomo = None
            self.notify("All study rounds are finished. Well done, you worked hard!", "jump")

    def stop_pomodoro(self):
        was = self.pomo is not None
        if self._pomo_timer:
            self._pomo_timer.cancel()
        self._pomo_timer = None
        self.pomo = None
        return was

    def pomodoro_status(self):
        p = self.pomo
        if not p:
            return None
        left = max(0, int(p["ends"] - time.time()))
        phase = {"work": "study time", "short": "short break", "long": "long break"}[p["phase"]]
        return "Round %d of %d, %s. %s left." % (p["round"], p["rounds"], phase, say_duration(left))
