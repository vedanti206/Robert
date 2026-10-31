"""Cuts Robert's picture sheet into small animation pictures."""
import os

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont

import config

NAMED_ANIMATIONS = {
    "idle": ("happy_sit", "hi_sit", "happy_blush"),
    "wave": ("hi_big", "hi_wave", "hi_shy"),
    "wait": ("hi_bubble", "heart_bubble", "hi_sit"),
    "run": ("chess1", "chess2", "chess3"),
    "review": ("idea", "read_glasses1", "read_glasses2"),
    "sleep": ("sleep", "blanket"),
    "blush": ("happy_blush",),
    "smart": ("read_glasses1", "read_glasses2"),
    "read_activity": ("read1", "read2", "read_glasses1", "read_glasses2"),
    "games_activity": ("chess1", "chess2", "chess3", "chess_happy1", "chess_cheer", "chess_win", "chess_wink"),
    "compliment_amazing": ("amazing",),
    "compliment_great": ("doing_great", "doing_great2"),
    "compliment_beautiful": ("beautiful", "beautiful2"),
    "compliment_incredible": ("incredible", "incredible2"),
    "compliment_special": ("special", "special2"),
    "compliment_lucky": ("lucky", "lucky2"),
}


def _union_box(path, cw, ch):
    """Finds the smallest box that holds the puppy in every cell (removes empty edges)."""
    try:
        from PIL import Image
        img = Image.open(path).convert("RGBA")
        alpha = img.getchannel("A")
        l, t, r, b = cw, ch, 0, 0
        for row in range(config.SHEET_ROWS):
            for col in range(config.SHEET_COLUMNS):
                cell = alpha.crop((col * cw, row * ch, (col + 1) * cw, (row + 1) * ch))
                box = cell.getbbox()
                if box:
                    l, t, r, b = min(l, box[0]), min(t, box[1]), max(r, box[2]), max(b, box[3])
        if r > l and b > t:
            pad = 2
            return QRect(max(0, l - pad), max(0, t - pad),
                         min(cw, r + pad) - max(0, l - pad), min(ch, b + pad) - max(0, t - pad))
    except Exception:
        pass
    return QRect(0, 0, cw, ch)


def _slice(sheet, path, size):
    cw = sheet.width() // config.SHEET_COLUMNS
    ch = sheet.height() // config.SHEET_ROWS
    print("Picture sheet is %dx%d -> each picture is %dx%d (columns=%d, rows=%d)" % (
        sheet.width(), sheet.height(), cw, ch, config.SHEET_COLUMNS, config.SHEET_ROWS))
    box = _union_box(path, cw, ch)

    def cell(row, col):
        pm = sheet.copy(col * cw + box.x(), row * ch + box.y(), box.width(), box.height())
        return pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)

    frames = {}
    for state, (row, count) in config.ANIMATIONS.items():
        frames[state] = [cell(row, c) for c in range(count)]
    frames["sleep"] = [cell(r, c) for r, c in config.SLEEP_CELLS]
    return frames


def _placeholder(size):
    """A simple drawn puppy, used when the picture sheet is missing."""
    frames = {}
    names = list(config.ANIMATIONS.keys()) + ["sleep"]
    for state in names:
        lst = []
        for i in range(4):
            pm = QPixmap(size, size)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            bob = (i % 2) * 4
            p.setBrush(QColor("#E8A04A"))
            p.setPen(QColor("#8A4B12"))
            p.drawEllipse(int(size * 0.18), int(size * 0.28) + bob, int(size * 0.64), int(size * 0.62))
            p.drawEllipse(int(size * 0.14), int(size * 0.14) + bob, int(size * 0.22), int(size * 0.30))
            p.drawEllipse(int(size * 0.64), int(size * 0.14) + bob, int(size * 0.22), int(size * 0.30))
            p.setBrush(QColor("#222222"))
            eye = 3 if state != "sleep" else 1
            p.drawEllipse(int(size * 0.36), int(size * 0.50) + bob, eye * 2, eye * 2)
            p.drawEllipse(int(size * 0.58), int(size * 0.50) + bob, eye * 2, eye * 2)
            p.drawEllipse(int(size * 0.47), int(size * 0.60) + bob, 8, 6)
            p.setPen(QColor("#444444"))
            p.setFont(QFont("Segoe UI", 7))
            p.drawText(QRect(0, size - 16, size, 16), Qt.AlignmentFlag.AlignCenter, state)
            p.end()
            lst.append(pm)
        frames[state] = lst
    return frames


def _named_frames(size):
    frames = {}
    for state, names in NAMED_ANIMATIONS.items():
        state_frames = []
        for name in names:
            path = os.path.join(config.SPRITE_DIR, name + ".png")
            if not os.path.isfile(path):
                continue
            pm = QPixmap(path)
            if pm.isNull():
                print("Could not load sprite:", path)
                continue
            state_frames.append(pm.scaled(
                size, size, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        if state_frames:
            frames[state] = state_frames
    return frames


def build_frames(size):
    """Returns (frames, using_real_art)."""
    path = config.SPRITE_SHEET
    using_real_sheet = False
    if os.path.exists(path):
        sheet = QPixmap(path)
        if not sheet.isNull():
            frames = _slice(sheet, path, size)
            using_real_sheet = True
        else:
            print("Could not load sprite sheet:", path)
            frames = _placeholder(size)
    else:
        frames = _placeholder(size)

    named_frames = _named_frames(size)
    frames.update(named_frames)
    return frames, using_real_sheet or bool(named_frames)
