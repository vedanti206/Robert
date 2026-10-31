"""The router: reads what you said and decides what Robert should do."""
import random
import re
import threading
import time

import config
import skills
from skills import Reply, fail
from llm import LLM
from timers import Scheduler, parse_duration, say_duration, normalize_numbers

YES = {"yes", "yeah", "yep", "yup", "sure", "ok", "okay", "send", "send it", "do it", "correct", "haan", "ha"}
NO = {"no", "nope", "cancel", "stop", "dont", "don't", "no thanks", "nahi"}

HELP_TEXT = (
    "I can: play YouTube, open apps, send WhatsApp messages, set timers and reminders, "
    "run a Pomodoro, tell weather, time and date, take notes, change volume and brightness, "
    "take screenshots, lock the screen, tell battery, skip YouTube ads, read, summarize or "
    "translate your clipboard, and help you study. Just ask!"
)


class Assistant:
    def __init__(self, bridge, notify):
        self.bridge = bridge
        self.llm = LLM()
        self.scheduler = Scheduler(notify)
        self.study_mode = False
        self.speak_enabled = config.SPEAK_ALOUD
        self.pending = None   # something waiting for a "yes"
        self.auto_skip = False
        threading.Thread(target=self._auto_skip_loop, daemon=True).start()

    # ------------------------------------------------------------ helpers
    def _state(self, name):
        try:
            self.bridge.state.emit(name)
        except Exception:
            pass

    @staticmethod
    def normalize(text):
        t = text.lower().strip()
        t = re.sub(r"^(?:(?:hey|hi|hello|ok|okay)[, ]+)?robert[,:! ]*", "", t).strip()
        t = re.sub(r"[?.!]+$", "", t).strip()
        return t

    def _auto_skip_loop(self):
        """When 'auto skip' is ON, clicks the YouTube Skip button whenever it shows up."""
        while True:
            time.sleep(2)
            if not self.auto_skip:
                continue
            try:
                if "youtube" in skills.foreground_title().lower() and skills.try_click_skip():
                    self.bridge.say.emit("Skipped an ad!", 2000)
            except Exception:
                pass

    # ------------------------------------------------------------ main entry
    def handle(self, text):
        raw = text.strip()
        t = self.normalize(raw)
        if not t:
            return Reply("Yes? I am here!", "wave")

        # waiting for yes / no?
        if self.pending:
            action, self.pending = self.pending, None
            if t in YES:
                self._state("run")
                return action()
            if t in NO:
                return Reply("Okay, I cancelled it.", "idle")
            # anything else: forget the question and carry on

        self._state("run")
        try:
            reply = self.route(t, raw)
        except Exception as e:   # never crash Robert
            print("Robert error:", repr(e))
            return fail("Oops! Something went wrong with that.")
        return reply

    # ------------------------------------------------------------ the rules
    def route(self, t, raw):
        # ---- greetings and small talk
        if re.fullmatch(r"(hi|hello|hey|good (morning|afternoon|evening)|namaste)( there)?", t):
            return Reply("Woof! Hello! How can I help?", "wave")
        if re.search(r"\b(who are you|your name|what are you)\b", t):
            return Reply("I am Robert, your desktop puppy helper! Woof!", "wave")
        if re.search(r"\bwhat can you do\b|\byour commands\b|\bwhat do you do\b", t) or t == "help":
            return Reply(HELP_TEXT, "wave")
        if re.search(r"\b(thank you|thanks)\b", t):
            return Reply("You are welcome! Woof!", "jump")

        # ---- sprite-based greetings, compliments, and activities
        if re.search(r"\b(blush|blushing)\b", t):
            return Reply("Aww, you made me blush!", "blush",
                         speak_text="Aww, you made me blush!")

        if re.search(r"\b(say|tell|give)\b.*\b(compliment|something nice)\b", t) \
                or re.search(r"\bcompliment (me|us)\b|\b(cheer me up|encourage me)\b", t):
            compliments = [
                ("compliment_amazing", "You're amazing!"),
                ("compliment_great", "You're doing great!"),
                ("compliment_beautiful", "You're beautiful!"),
                ("compliment_incredible", "You're incredible!"),
                ("compliment_special", "You're so special!"),
                ("compliment_lucky", "I'm so lucky to know you!"),
            ]
            state, text = random.choice(compliments)
            return Reply(text, state, speak_text=text)

        if re.search(r"\b(smart|clever|brainy)\b", t) and re.search(
                r"\b(you|your|robert|are|look|picture|show)\b", t):
            return Reply("Aww, thank you! I'm thinking hard!", "smart",
                         speak_text="Aww, thank you! I'm thinking hard!")

        if re.search(r"\b(say|tell)\s+(?:me\s+)?(?:hi|hello)\b|\bgreet me\b", t):
            return Reply("Hiiii! Hello!", "wave", speak_text="Hiiii! Hello!")

        if re.search(r"\b(play|start|show)\b.*\b(chess|games?)\b", t):
            return Reply("I'll play my chess animation for 30 seconds. Say Robert to stop me.",
                         "games_activity", speak_text="I'll play chess for 30 seconds. Say Robert to stop me.",
                         activity_seconds=config.GAMES_ACTIVITY_SECONDS)

        if re.fullmatch(r"play(?: for (?:some time|a while|a bit))?", t):
            return Reply("I'll play my chess animation for 30 seconds. Say Robert to stop me.",
                         "games_activity", speak_text="I'll play chess for 30 seconds. Say Robert to stop me.",
                         activity_seconds=config.GAMES_ACTIVITY_SECONDS)

        if (re.fullmatch(r"read", t)
                or re.search(r"\b(read|reading)\b.*\b(book|story)\b", t)
                or re.fullmatch(r"(?:start )?reading(?: for (?:some time|a while))?", t)):
            return Reply("Okay, I'll read for a while. Say Robert when you want me to stop.",
                         "read_activity", speak_text="Okay, I'll read. Say Robert when you want me to stop.")

        # ---- sleep, quit, voice on / off
        if re.search(r"\b(go to sleep|good night|sleep now|take a nap)\b", t):
            return Reply("Okay, good night! Zzz...", "sleep")
        if re.fullmatch(r"(good ?bye|bye( bye)?|quit|exit|close yourself|close robert|shut down)( robert)?", t):
            return Reply("Bye bye! See you soon!", "wave", action="quit")
        if re.search(r"\b(be quiet|stop talking|mute yourself|do not speak|don't speak)\b", t):
            self.speak_enabled = False
            return Reply("Okay, I will stay quiet. I will still write in the bubble.", "idle")
        if re.search(r"\b(start talking|talk again|speak again|you can talk|unmute yourself)\b", t):
            self.speak_enabled = True
            return Reply("Yay! I can talk again!", "jump")

        # ---- study mode
        m = re.search(r"\bstudy mode (on|off)\b", t)
        if m or re.search(r"\b(start|stop) studying\b", t):
            on = (m.group(1) == "on") if m else ("start" in t)
            self.study_mode = on
            return Reply("Study mode is ON. Ask me any question and I will explain in simple steps."
                         if on else "Study mode is OFF.", "jump")

        # ---- timers, reminders, pomodoro
        r = self.timer_rules(t)
        if r:
            return r

        # ---- time and date
        if t == "time" or (re.search(r"\btime\b", t) and re.search(r"\b(what|tell|current|now)\b", t)):
            return skills.tell_time()
        if re.search(r"\b(date|what day|which day)\b", t) and re.search(r"\b(what|tell|today|the date)\b", t):
            return skills.tell_date()

        # ---- weather
        if re.search(r"\b(weather|temperature|is it (raining|hot|cold))\b", t):
            m = re.search(r"\b(?:in|at|for)\s+([a-z][a-z ]+?)(?:\s+(?:today|now|tomorrow))?$", t)
            return skills.weather(m.group(1).strip() if m else None)

        # ---- notes
        m = re.match(r"^(?:take|add|make|write|save)(?: a| me a)? note(?: that| to| saying)?[:, ]*(.+)$", t) \
            or re.match(r"^note (?:down|that)[:, ]*(.+)$", t) \
            or re.match(r"^remember (?:that )?(.+)$", t)
        if m:
            return skills.add_note(m.group(1).strip())
        if re.search(r"\b(read|show|what are|open)\b.*\bnotes\b", t):
            return skills.read_notes()

        # ---- system control
        if re.search(r"\bscreen ?shot\b|\bcapture (the )?screen\b", t):
            return skills.screenshot(self.bridge)
        if re.search(r"\block (the |my )?(screen|computer|laptop|pc)\b", t):
            return skills.lock_screen()
        if re.search(r"\bbattery\b", t):
            return skills.battery()

        if re.search(r"\bvolume\b|\blouder\b|\bquieter\b|\bunmute\b|\bmute\b", t) and "youtube" not in t:
            n = re.search(r"(\d{1,3})", normalize_numbers(t))
            if re.search(r"\b(set|make|put)\b.*\bvolume\b.*\b(to|at)\b", t) and n:
                return skills.volume_set(int(n.group(1)))
            if re.search(r"\bunmute\b|\bmute\b", t):
                return skills.volume_mute()
            if re.search(r"\b(up|increase|raise|louder|higher)\b", t):
                return skills.volume_up()
            if re.search(r"\b(down|decrease|lower|quieter|reduce|less)\b", t):
                return skills.volume_down()

        if re.search(r"\bbrightness\b|\bbrighter\b|\bdimmer\b", t):
            n = re.search(r"(\d{1,3})", normalize_numbers(t))
            if n and re.search(r"\b(set|to|at)\b", t):
                return skills.brightness_change(absolute=int(n.group(1)))
            if re.search(r"\b(up|increase|raise|brighter|higher)\b", t):
                return skills.brightness_change(delta=+20)
            if re.search(r"\b(down|decrease|lower|dimmer|reduce|dim)\b", t):
                return skills.brightness_change(delta=-20)

        # ---- clipboard
        if re.search(r"\bread\b.*\b(clipboard|copied)\b|\bread what i copied\b", t):
            return skills.read_clipboard()
        if re.search(r"\bsummari[sz]e\b.*\b(clipboard|copied|this|text)\b", t):
            return self.clipboard_ai("Summarize this text in 3 short simple sentences:", "summary")
        m = re.search(r"\btranslate\b.*?\b(?:in|to|into)\s+([a-z]+)\s*$", t)
        if m and re.search(r"\b(clipboard|copied|this|text)\b", t):
            lang = m.group(1)
            return self.clipboard_ai("Translate this text into %s. Give only the translation:" % lang, "translation")

        # ---- skip YouTube ads
        AD = r"(?:ads?|adds?|advertisements?|commercials?)"
        if (re.search(r"\bauto ?skip\b", t)
                or re.search(r"\b(always|automatically) skip\b", t)
                or re.search(r"\b(stop|disable|quit) skipping\b", t)):
            off = re.search(r"\b(off|stop|disable|quit|no more|do not|don't)\b", t)
            if not off and not skills.os.path.exists(skills.SKIP_IMG):
                return fail("I need a picture of the Skip button first. Save it as assets/skip_button.png.")
            self.auto_skip = not off
            return Reply("Okay! I will skip YouTube ads for you. Keep me away from the bottom-right of the video."
                         if self.auto_skip else "Okay, I stopped skipping ads.", "jump")
        if re.search(r"\bskip\b.*\b%s\b|\b%s\b.*\bskip\b" % (AD, AD), t):
            return skills.skip_ad(self.bridge)

        # ---- music / media keys
        if re.fullmatch(r"(pause|play|resume|play (the )?(music|song|video|youtube)|pause (the )?(music|song|video|youtube)|resume (the )?(music|song|video)|stop (the )?(music|song|video))", t):
            return skills.media_key("playpause", "Okay!")
        if re.search(r"\b(next|skip)\b.*\b(song|track|music)\b|^(next|skip)$", t):
            return skills.media_key("nexttrack", "Next song!")
        if re.search(r"\b(previous|last)\b.*\b(song|track)\b", t):
            return skills.media_key("prevtrack", "Going back!")

        # ---- YouTube
        m = re.match(r"^(?:play|put on|start playing)\s+(.+?)(?:\s+(?:on|in|at)\s+youtube)?$", t) \
            or re.match(r"^(?:search )?youtube (?:for )?(.+)$", t) \
            or re.match(r"^search (.+?) on youtube$", t)
        if m:
            return skills.play_youtube(m.group(1).strip())

        # ---- WhatsApp
        r = self.whatsapp_rule(t)
        if r:
            return r

        # ---- open apps / websites
        m = re.match(r"^(?:open|launch|start|go to)\s+(.+)$", t)
        if m:
            return skills.open_thing(m.group(1))

        # ---- everything else goes to the brain
        return self.ask_brain(raw)

    # ------------------------------------------------------------ timer rules
    def timer_rules(self, t):
        if re.search(r"\b(cancel|stop|clear|delete)\b.*\b(timers?|reminders?|alarms?)\b", t):
            n = self.scheduler.cancel_all()
            return Reply("Cancelled %d timer%s." % (n, "" if n == 1 else "s") if n else "You have no timers.", "idle")

        if "pomodoro" in t:
            if re.search(r"\b(stop|cancel|end|quit)\b", t):
                return Reply("Pomodoro stopped." if self.scheduler.stop_pomodoro() else "No Pomodoro is running.", "idle")
            if re.search(r"\b(status|left|how much)\b", t):
                s = self.scheduler.pomodoro_status()
                return Reply(s or "No Pomodoro is running.", "idle")
            self.scheduler.start_pomodoro()
            return Reply("Pomodoro started! Study for 25 minutes, then a 5 minute break. You can do it!", "jump")

        m = re.search(r"remind me (?:in|after) (.+?) (?:to|about|that) (.+)", t)
        if m and parse_duration(m.group(1)):
            return self.add_timer(parse_duration(m.group(1)), "Reminder: " + m.group(2), m.group(2))
        m = re.search(r"remind me (?:to|about|that) (.+?) (?:in|after) (.+)", t)
        if m and parse_duration(m.group(2)):
            return self.add_timer(parse_duration(m.group(2)), "Reminder: " + m.group(1), m.group(1))

        if re.search(r"\b(timer|alarm|countdown|wake me)\b", t) or re.search(r"\bremind me (?:in|after)\b", t):
            secs = parse_duration(t)
            if secs:
                return self.add_timer(secs, "Time is up! Your %s timer is done." % say_duration(secs), "timer")
            return Reply("For how long? Say something like: set a timer for 10 minutes.", "wait", followup=True)

        if re.search(r"\b(how long|time) left\b|\bmy timers?\b|\bany timers?\b", t):
            p = self.scheduler.pending()
            if not p:
                return Reply("You have no timers.", "idle")
            return Reply("; ".join("%s: %s left" % (l, say_duration(s)) for l, s in p))
        return None

    def add_timer(self, secs, message, label):
        self.scheduler.add(secs, message, label)
        return Reply("Okay! I will tell you in %s." % say_duration(secs))

    # ------------------------------------------------------------ WhatsApp
    def whatsapp_rule(self, t):
        m = re.match(r"^(?:send|write)(?: a)?(?: whatsapp)?(?: message| text| msg)?(?: on whatsapp)? to ([a-z]+)[,: ]*(?:saying|that|to say|which says)?[,: ]*(.+)$", t) \
            or re.match(r"^(?:whatsapp|message|text|msg)\s+([a-z]+)[,: ]*(?:saying|that|to say|which says)?[,: ]*(.+)$", t)
        if not m:
            return None
        name, message = m.group(1), m.group(2).strip()
        key, number = skills.find_contact(name)
        if not number:
            return fail("I do not have %s in my contacts. Please add them in contacts.json." % name)
        message = message[0].upper() + message[1:]

        def go():
            return skills.send_whatsapp(number, message)
        self.pending = go
        return Reply('Send "%s" to %s? Say yes or no.' % (message, key.title()),
                     "wait", followup=True, speak_text="Send %s to %s? Say yes or no." % (message, key.title()))

    # ------------------------------------------------------------ AI parts
    def ask_brain(self, raw):
        self._state("review")
        study = self.study_mode or bool(re.match(r"^(explain|define|teach me|what is|what are|why is|how does|how do)\b", raw.lower()))
        ok, text = self.llm.chat(raw, study=study)
        return Reply(text, "jump" if ok else "failed", speak_text=text[:350])

    def clipboard_ai(self, instruction, what):
        text = skills.get_clipboard()
        if not text:
            return fail("Your clipboard is empty. Copy some text first.")
        self._state("review")
        ok, out = self.llm.oneshot(instruction, text)
        return Reply(out, "jump" if ok else "failed", speak_text=out[:350])
