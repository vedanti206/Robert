"""
demo_pet.py - a tiny test pet so you can SEE the new Robert before touching your big project.
  Run:   python demo_pet.py
  - Drag Robert with the left mouse button
  - Click him to open a small command box, type something (e.g. "play music", "study mode", "thank you") + Enter
  - Right-click = close
  - After 60 seconds of nothing he falls asleep; any click wakes him up
"""
import tkinter as tk
from robert_sprites import RobertSprites, mood_for_text

root = tk.Tk()
root.overrideredirect(True)                       # no window border
root.attributes("-topmost", True)                 # always on top
root.attributes("-transparentcolor", "#ff00fe")   # see-through background (Windows)
root.config(bg="#ff00fe")
root.geometry("+1000+500")

label = tk.Label(root)
label.pack()
pet = RobertSprites(root, label, folder="sprites", height=150)
pet.set_mood("hello", hold_ms=3000)

last_active = [0]
def touch():
    last_active[0] += 1
    n = last_active[0]
    root.after(60000, lambda: last_active[0] == n and pet.set_mood("sleep"))
touch()

# ---- drag to move ----
drag = {}
def start(e): drag.update(x=e.x, y=e.y, moved=False)
def move(e):
    drag["moved"] = True
    root.geometry(f"+{root.winfo_x() + e.x - drag['x']}+{root.winfo_y() + e.y - drag['y']}")
def release(e):
    if not drag.get("moved"): open_box()
label.bind("<Button-1>", start)
label.bind("<B1-Motion>", move)
label.bind("<ButtonRelease-1>", release)
label.bind("<Button-3>", lambda e: root.destroy())

# ---- click = command box ----
box = {"win": None}
def open_box():
    touch()
    if pet.mood == "sleep": pet.set_mood("hello", hold_ms=2500)
    if box["win"] and box["win"].winfo_exists():
        box["win"].focus_force(); return
    w = tk.Toplevel(root); box["win"] = w
    w.attributes("-topmost", True); w.title("Tell Robert")
    w.geometry(f"+{root.winfo_x()-40}+{root.winfo_y()+root.winfo_height()+5}")
    e = tk.Entry(w, width=34, font=("Segoe UI", 12)); e.pack(padx=8, pady=8); e.focus_force()
    def go(_=None):
        text = e.get(); w.destroy()
        if text.strip():
            mood = mood_for_text(text)
            pet.set_mood(mood, hold_ms=None if mood in ("music", "focus", "study", "break", "sleep") else 5000)
            print("You said:", text, "->", mood)
    e.bind("<Return>", go)
root.mainloop()
