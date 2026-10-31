"""The helper thread: waits for 'Robert', listens, thinks, acts, answers."""
import queue
import threading
import time

import config
from assistant import Assistant
from voice import Mouth, Ears


def beep(freq=900, ms=110):
    try:
        import winsound
        winsound.Beep(freq, ms)
    except Exception:
        pass


class Controller:
    def __init__(self, bridge):
        self.bridge = bridge
        self.cmd_q = queue.Queue()          # typed commands
        self.click_evt = threading.Event()  # set when you click Robert
        self.running = True
        self._activity_lock = threading.Lock()
        self._activity_generation = 0
        self._activity_timer = None
        self.mouth = Mouth()
        self.assistant = Assistant(bridge, notify=self.async_notify)
        self.ears = None

    # ---------- called from the screen (main thread)
    def on_click(self):
        self.click_evt.set()

    def submit_text(self, text):
        self.cmd_q.put(text)

    def stop(self):
        self.running = False
        self._cancel_activity()

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()
        threading.Thread(target=self.assistant.llm.warm_up, daemon=True).start()

    # ---------- helpers
    def _say(self, text, ms=0):
        self.bridge.say.emit(text, ms)

    def _speak(self, text):
        if self.assistant.speak_enabled and text:
            self.mouth.say(text, wait=True)

    def _cancel_activity(self):
        with self._activity_lock:
            self._activity_generation += 1
            timer = self._activity_timer
            self._activity_timer = None
        if timer:
            timer.cancel()

    def _finish_activity(self, generation):
        with self._activity_lock:
            if generation != self._activity_generation:
                return
            self._activity_timer = None
        self.bridge.state.emit("idle")

    def _schedule_activity_end(self, seconds):
        self._cancel_activity()
        with self._activity_lock:
            generation = self._activity_generation
            timer = threading.Timer(seconds, self._finish_activity, args=(generation,))
            timer.daemon = True
            self._activity_timer = timer
            timer.start()

    def async_notify(self, text, state="wave"):
        """Timers and Pomodoro call this from their own threads."""
        beep(1000, 150)
        self.bridge.state.emit(state)
        self._say(text, 15000)
        if self.assistant.speak_enabled:
            self.mouth.say(text)

    def _interrupt(self):
        return (not self.running) or (not self.cmd_q.empty()) or self.click_evt.is_set()

    # ---------- the main loop
    def _loop(self):
        self.ears = Ears(self.mouth)
        if self.ears.ok:
            self.bridge.state.emit("wave")
            self._say("Woof! I am Robert. Say 'Robert' or click me. Right-click to type.", 7000)
        else:
            err = self.ears.error
            self.ears = None
            self.bridge.state.emit("wave")
            self._say("Woof! I am Robert. I cannot hear yet: %s Click me to type instead." % err, 20000)
            print("EARS PROBLEM:", err)

        while self.running:
            woke = False
            if self.ears:
                try:
                    woke = self.ears.listen_for_wake(self._interrupt)
                except Exception as e:
                    print("Microphone problem:", repr(e))
                    self.ears = None
                    self._say("My ears stopped working. Click me and type instead.", 10000)
                    continue
            else:
                while not self._interrupt():
                    time.sleep(0.1)
            if not self.running:
                break

            if not self.cmd_q.empty():
                self._process(self.cmd_q.get())
                self.click_evt.clear()
            elif woke or self.click_evt.is_set():
                self.click_evt.clear()
                if self.ears:
                    self._voice_turn()
                else:
                    self.bridge.open_typebox.emit()

    def _voice_turn(self):
        self._cancel_activity()
        self.bridge.state.emit("wait")
        self._say("Yes? I am listening...", 6000)
        beep(880, 110)
        while True:
            text = self.ears.listen_command()
            if not text:
                self.bridge.state.emit("idle")
                self._say("I did not hear anything. Say 'Robert' to try again.", 4000)
                return
            reply = self._process(text, shown_as="You said: " + text)
            if reply is None or not reply.followup:
                return
            self.bridge.state.emit("wait")
            beep(880, 110)

    def _process(self, text, shown_as=None):
        self._cancel_activity()
        self._say(shown_as or ("You typed: " + text), 3000)
        self.bridge.state.emit("run")
        reply = self.assistant.handle(text)
        self.bridge.state.emit(reply.state)
        self._say(reply.text)
        if reply.action == "quit":
            self._speak(reply.speak_text or reply.text)
            self.bridge.quit_app.emit()
            return reply
        self._speak(reply.speak_text or reply.text)
        if reply.activity_seconds is not None:
            self._schedule_activity_end(reply.activity_seconds)
        return reply
