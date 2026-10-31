"""Robert's ears (listening) and mouth (speaking)."""
import json
import os
import queue
import threading
import time

import config


# ====================================================================== MOUTH
class Mouth:
    """Speaks text out loud. Runs in its own thread so Robert never freezes."""

    def __init__(self):
        self.q = queue.Queue()
        self.busy = False
        self.last_end = 0.0
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        engine = None
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", config.SPEECH_RATE)
        except Exception as e:
            print("Robert cannot speak:", repr(e))
        while True:
            text, done = self.q.get()
            self.busy = True
            try:
                if engine:
                    engine.say(text)
                    engine.runAndWait()
            except Exception as e:
                print("Speak error:", repr(e))
            finally:
                self.busy = False
                self.last_end = time.time()
                if done:
                    done.set()

    def say(self, text, wait=False):
        if not text:
            return
        done = threading.Event() if wait else None
        self.q.put((text, done))
        if done:
            done.wait(timeout=90)

    def is_busy(self):
        return self.busy or not self.q.empty() or (time.time() - self.last_end) < 0.6


# ====================================================================== EARS
def find_model_dir():
    """Finds the Vosk model, even if it is inside one extra folder."""
    root = config.MODEL_FOLDER
    if not os.path.isdir(root):
        return None
    if os.path.isdir(os.path.join(root, "am")):
        return root
    for name in os.listdir(root):
        sub = os.path.join(root, name)
        if os.path.isdir(os.path.join(sub, "am")):
            return sub
    return None


class Ears:
    RATE = 16000

    def __init__(self, mouth):
        self.mouth = mouth
        self.error = None
        self.ok = False
        try:
            import sounddevice as sd
            import vosk
        except ImportError as e:
            self.error = "Some voice parts are not installed (%s). Run install_robert.bat again." % e.name
            return
        path = find_model_dir()
        if not path:
            self.error = "I cannot find my voice model. Please follow Step 4 of the guide (the 'model' folder)."
            return
        try:
            vosk.SetLogLevel(-1)
            self.vosk = vosk
            self.model = vosk.Model(path)
            self.wake_rec = vosk.KaldiRecognizer(
                self.model, self.RATE, json.dumps([config.WAKE_WORD, "[unk]"]))
            self.stream = sd.RawInputStream(samplerate=self.RATE, blocksize=3200,
                                            dtype="int16", channels=1)
            self.stream.start()
            self.ok = True
        except Exception as e:
            self.error = "I cannot use the microphone (%s). Check Windows microphone settings." % e

    # ---------- small helpers
    def _read(self):
        data, _ = self.stream.read(3200)
        return bytes(data)

    def _flush(self):
        try:
            n = self.stream.read_available
            if n:
                self.stream.read(n)
        except Exception:
            pass

    # ---------- wait for the name "Robert"
    def listen_for_wake(self, interrupt):
        """Blocks until Robert hears his name (True) or interrupt() says stop (False)."""
        self.wake_rec.Reset()
        self._flush()
        last_trigger = 0
        while not interrupt():
            data = self._read()
            if self.mouth.is_busy():          # do not listen to myself
                self.wake_rec.Reset()
                continue
            if self.wake_rec.AcceptWaveform(data):
                text = json.loads(self.wake_rec.Result()).get("text", "")
            else:
                text = json.loads(self.wake_rec.PartialResult()).get("partial", "")
            if config.WAKE_WORD in text.split() and time.time() - last_trigger > 1.5:
                self.wake_rec.Reset()
                return True
        return False

    # ---------- listen to one sentence
    def listen_command(self):
        """Listens until you stop talking. Returns the text, or None if nothing was said."""
        rec = self.vosk.KaldiRecognizer(self.model, self.RATE)
        self._flush()
        frames, started = [], False
        t0 = time.time()
        text = ""
        while True:
            data = self._read()
            frames.append(data)
            if rec.AcceptWaveform(data):
                text = json.loads(rec.Result()).get("text", "")
                break
            partial = json.loads(rec.PartialResult()).get("partial", "")
            if partial:
                started = True
            elapsed = time.time() - t0
            if not started and elapsed > config.LISTEN_WAIT_SECONDS:
                return None
            if elapsed > config.LISTEN_MAX_SECONDS:
                text = json.loads(rec.FinalResult()).get("text", "")
                break
        if not text and not started:
            return None

        # Try Google for better accuracy; fall back to Vosk's own answer.
        if config.USE_GOOGLE_SPEECH:
            try:
                import speech_recognition as sr
                audio = sr.AudioData(b"".join(frames), self.RATE, 2)
                better = sr.Recognizer().recognize_google(audio, language="en-IN")
                if better.strip():
                    return better.strip()
            except Exception:
                pass
        return text.strip() or None
