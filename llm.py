"""Robert's brain. Talks to Ollama running on your own laptop (no key, no internet)."""
import re
import config

CHAT_PROMPT = (
    "You are Robert, a friendly, playful puppy who lives on the user's desktop. "
    "Reply in very simple English. Keep answers short: 1 to 3 sentences. "
    "Do not use markdown, lists, stars or emojis. If you do not know, say so."
)

STUDY_PROMPT = (
    "You are Robert, a kind teacher puppy helping a college student prepare for exams. "
    "Explain in very simple English, step by step. First give a one-line meaning. "
    "Then give 3 to 5 short numbered points. Then give one small example. "
    "Do not use markdown symbols like ** or #. Keep it under 150 words."
)

BRAIN_OFF = ("My brain is asleep. Please open the Ollama app on your laptop, "
             "wait a little, and ask me again.")
BRAIN_MISSING = ("I cannot find my brain file. Open Command Prompt and type: "
                 "ollama pull " + config.OLLAMA_MODEL)


def clean(text):
    """Remove markdown marks so the bubble looks neat."""
    text = re.sub(r"\*\*|__|`+", "", text)
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[\*\-]\s+", "- ", text, flags=re.M)
    return text.strip()


class LLM:
    def __init__(self):
        self.history = []   # remembers the last few things you talked about

    def _post(self, messages, num_predict):
        import requests
        try:
            r = requests.post(
                config.OLLAMA_URL + "/api/chat",
                json={
                    "model": config.OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "keep_alive": "30m",
                    "options": {"num_predict": num_predict, "temperature": 0.6},
                },
                timeout=240,
            )
        except requests.exceptions.ConnectionError:
            return False, BRAIN_OFF
        except requests.exceptions.Timeout:
            return False, "My brain is thinking too slowly. Please try a shorter question."
        if r.status_code == 404:
            return False, BRAIN_MISSING
        if r.status_code != 200:
            return False, "My brain had a problem (code %d)." % r.status_code
        try:
            return True, clean(r.json()["message"]["content"])
        except Exception:
            return False, "My brain gave a strange answer. Please ask again."

    def chat(self, user_text, study=False):
        system = STUDY_PROMPT if study else CHAT_PROMPT
        messages = [{"role": "system", "content": system}]
        messages += self.history[-6:]
        messages.append({"role": "user", "content": user_text})
        ok, text = self._post(messages, 380 if study else 140)
        if ok:
            self.history += [{"role": "user", "content": user_text},
                             {"role": "assistant", "content": text}]
            self.history = self.history[-12:]
        return ok, text

    def oneshot(self, instruction, text, num_predict=250):
        """Used for summarize / translate. Does not touch the chat memory."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Use simple English. No markdown."},
            {"role": "user", "content": instruction + "\n\n" + text[:4000]},
        ]
        return self._post(messages, num_predict)

    def warm_up(self):
        """Load the model into memory early so the first answer is faster."""
        try:
            import requests
            requests.post(config.OLLAMA_URL + "/api/generate",
                          json={"model": config.OLLAMA_MODEL, "keep_alive": "30m"},
                          timeout=120)
        except Exception:
            pass
