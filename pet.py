"""Robert's body: the puppy window, the speech bubble above his head, and the typing box."""
import random
import time

from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, pyqtSignal, QObject
from PyQt6.QtGui import (QPainter, QColor, QPen, QPolygonF, QFont, QFontMetrics,
                         QCursor, QGuiApplication)
from PyQt6.QtWidgets import QWidget, QMenu, QTextBrowser, QLineEdit, QPushButton

import config
from sprites import build_frames

FLAGS = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool


class Bridge(QObject):
    """Safe messenger between Robert's helper thread and the screen."""
    say = pyqtSignal(str, int)      # text, how long to show (ms, 0 = automatic)
    state = pyqtSignal(str)
    quit_app = pyqtSignal()
    hide_pet = pyqtSignal()
    show_pet = pyqtSignal()
    open_typebox = pyqtSignal()


# ====================================================================== BUBBLE
class Bubble(QWidget):
    WIDTH_MAX, WIDTH_MIN, PAD, TAIL, TEXT_MAX_H = 330, 150, 12, 12, 230

    def __init__(self):
        super().__init__(None, FLAGS | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.font_ = QFont("Segoe UI", 10)
        self.view = QTextBrowser(self)
        self.view.setFont(self.font_)
        self.view.setFrameShape(QTextBrowser.Shape.NoFrame)
        self.view.setStyleSheet("background: transparent; color: #2B2B2B;")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        self.tail_x = 100
        self.anchor = None

    def show_text(self, text, anchor, ms=0):
        self.anchor = anchor
        fm = QFontMetrics(self.font_)
        w = max(self.WIDTH_MIN, min(self.WIDTH_MAX, fm.horizontalAdvance(text) + 2 * self.PAD + 24))
        text_w = w - 2 * self.PAD
        self.view.setPlainText(text)
        self.view.document().setDocumentMargin(2)
        self.view.document().setTextWidth(text_w - 6)
        h = int(self.view.document().size().height()) + 6
        inner_h = min(h, self.TEXT_MAX_H)
        self.view.setGeometry(self.PAD, self.PAD, text_w, inner_h)
        self.view.verticalScrollBar().setValue(0)
        self.setFixedSize(w, inner_h + 2 * self.PAD + self.TAIL)
        self.reposition()
        self.show()
        self.raise_()
        ms = ms or max(4000, min(30000, 2500 + len(text) * 60))
        self.timer.start(ms)

    def reposition(self):
        if not self.anchor:
            return
        geo = QGuiApplication.primaryScreen().availableGeometry()
        center = self.anchor.x() + self.anchor.width() // 2
        x = max(geo.left() + 4, min(center - self.width() // 2, geo.right() - self.width() - 4))
        y = max(geo.top() + 4, self.anchor.y() - self.height() + 6)
        self.move(x, y)
        self.tail_x = max(24, min(center - x, self.width() - 24))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body_h = self.height() - self.TAIL
        p.setPen(QPen(QColor("#E8892B"), 2))
        p.setBrush(QColor("#FFFDF8"))
        p.drawRoundedRect(1, 1, self.width() - 2, body_h - 2, 14, 14)
        tri = QPolygonF([QPointF(self.tail_x - 9, body_h - 2), QPointF(self.tail_x + 9, body_h - 2),
                         QPointF(self.tail_x, self.height() - 2)])
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(tri)
        p.setPen(QPen(QColor("#E8892B"), 2))
        p.drawLine(QPointF(self.tail_x - 9, body_h - 2), QPointF(self.tail_x, self.height() - 2))
        p.drawLine(QPointF(self.tail_x + 9, body_h - 2), QPointF(self.tail_x, self.height() - 2))

    def mousePressEvent(self, _):
        self.hide()


# ====================================================================== COMMAND PANEL
class _Edit(QLineEdit):
    escape = pyqtSignal()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.escape.emit()
        else:
            super().keyPressEvent(e)


class CommandPanel(QWidget):
    """The little box that opens when you click Robert: type a command, or press the mic."""
    submitted = pyqtSignal(str)
    mic_clicked = pyqtSignal()
    closed = pyqtSignal()
    BODY_H, TAIL = 52, 10

    def __init__(self):
        super().__init__(None, FLAGS)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(350, self.BODY_H + self.TAIL)
        self.tail_x = 175

        self.edit = _Edit(self)
        self.edit.setGeometry(12, 9, 240, 34)
        self.edit.setPlaceholderText("Tell Robert what to do...")
        self.edit.setFont(QFont("Segoe UI", 10))
        self.edit.setStyleSheet("QLineEdit { background: #FFFFFF; border: 1px solid #E8B98A;"
                                " border-radius: 10px; padding: 2px 10px; color: #2B2B2B; }"
                                "QLineEdit:focus { border: 2px solid #E8892B; }")
        self.edit.returnPressed.connect(self._send)
        self.edit.escape.connect(self.close_panel)

        btn_style = ("QPushButton { background: #FDE9D2; border: 1px solid #E8B98A;"
                     " border-radius: 10px; font-size: 14px; }"
                     "QPushButton:hover { background: #F9D3AA; }")
        self.mic = QPushButton("\U0001F3A4", self)
        self.mic.setGeometry(258, 9, 40, 34)
        self.mic.setToolTip("Talk to Robert")
        self.mic.setStyleSheet(btn_style)
        self.mic.clicked.connect(self.mic_clicked.emit)

        self.x_btn = QPushButton("\u2715", self)
        self.x_btn.setGeometry(304, 9, 34, 34)
        self.x_btn.setToolTip("Close")
        self.x_btn.setStyleSheet(btn_style)
        self.x_btn.clicked.connect(self.close_panel)

    def _send(self):
        text = self.edit.text().strip()
        self.edit.clear()
        if text:
            self.submitted.emit(text)

    def close_panel(self):
        self.hide()
        self.closed.emit()

    def follow(self, pet):
        """Sit just above Robert's head."""
        geo = QGuiApplication.primaryScreen().availableGeometry()
        center = pet.x() + pet.width() // 2
        x = max(geo.left() + 4, min(center - self.width() // 2, geo.right() - self.width() - 4))
        y = max(geo.top() + 4, pet.y() - self.height() + 8)
        self.move(x, y)
        self.tail_x = max(24, min(center - x, self.width() - 24))
        self.update()

    def popup(self, pet):
        self.follow(pet)
        self.show()
        self.raise_()
        self.activateWindow()
        self.edit.setFocus()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#E8892B"), 2))
        p.setBrush(QColor("#FFFDF8"))
        p.drawRoundedRect(1, 1, self.width() - 2, self.BODY_H - 2, 16, 16)
        y0 = self.BODY_H - 2
        tri = QPolygonF([QPointF(self.tail_x - 9, y0), QPointF(self.tail_x + 9, y0),
                         QPointF(self.tail_x, self.height() - 2)])
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(tri)
        p.setPen(QPen(QColor("#E8892B"), 2))
        p.drawLine(QPointF(self.tail_x - 9, y0), QPointF(self.tail_x, self.height() - 2))
        p.drawLine(QPointF(self.tail_x + 9, y0), QPointF(self.tail_x, self.height() - 2))


# ====================================================================== PET
class PetWindow(QWidget):
    clicked = pyqtSignal()
    type_requested = pyqtSignal()
    mic_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    moved = pyqtSignal()

    def __init__(self):
        super().__init__(None, FLAGS)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.frames, self.has_real_sprites = build_frames(config.PET_SIZE)
        self.setFixedSize(config.PET_SIZE, config.PET_SIZE)

        self.state = "idle"
        self.frame_i = 0
        self.loops = 0
        self.target_x = None
        self.last_activity = time.time()
        self._press = None
        self._offset = QPoint()
        self.dragging = False
        self.hold = False      # True while the command panel is open (he stays still)

        geo = QGuiApplication.primaryScreen().availableGeometry()
        self.move(geo.right() - config.PET_SIZE - 80, geo.bottom() - config.PET_SIZE + 4)

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._next_frame)
        self.anim_timer.start(config.FRAME_MS["idle"])

        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self._walk_tick)
        self.move_timer.start(35)

        self.think_timer = QTimer(self)
        self.think_timer.timeout.connect(self._think_tick)
        self.think_timer.start(1500)

    # ---------- states
    def set_state(self, name):
        if name not in self.frames:
            name = "idle"
        self.state = name
        self.frame_i = 0
        self.loops = 0
        self.anim_timer.start(config.FRAME_MS.get(name, 150))
        self.update()

    def external_state(self, name):
        """Called when Robert's brain wants a new animation (counts as activity)."""
        self.touch()
        if name in ("run_left", "run_right"):
            name = "idle"
        self.target_x = None
        self.set_state(name)

    def touch(self):
        self.last_activity = time.time()

    def _next_frame(self):
        frames = self.frames[self.state]
        self.frame_i += 1
        if self.frame_i >= len(frames):
            self.frame_i = 0
            self.loops += 1
            limit = config.ONESHOT_LOOPS.get(self.state)
            if limit and self.loops >= limit:
                self.set_state("idle")
                return
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        pm = self.frames[self.state][self.frame_i % len(self.frames[self.state])]
        x = (self.width() - pm.width()) // 2
        y = self.height() - pm.height()
        p.drawPixmap(x, y, pm)

    # ---------- walking and moods
    def start_walk(self, target_x):
        geo = QGuiApplication.primaryScreen().availableGeometry()
        target_x = max(geo.left(), min(int(target_x), geo.right() - self.width()))
        if abs(target_x - self.x()) < 25:
            return False
        self.target_x = target_x
        self.set_state("run_right" if target_x > self.x() else "run_left")
        return True

    def _walk_tick(self):
        if self.state not in ("run_left", "run_right") or self.target_x is None or self.dragging:
            return
        step = config.WALK_SPEED
        dx = self.target_x - self.x()
        if abs(dx) <= step:
            self.move(self.target_x, self.y())
            self.target_x = None
            self.set_state("wave" if random.random() < 0.3 else "idle")
        else:
            self.move(self.x() + (step if dx > 0 else -step), self.y())
        self.moved.emit()

    def _think_tick(self):
        if self.dragging or self.hold:
            return
        if self.state == "idle":
            if time.time() - self.last_activity > config.SLEEP_AFTER_SECONDS:
                self.set_state("sleep")
                return
            if config.WANDER:
                r = random.random()
                geo = QGuiApplication.primaryScreen().availableGeometry()
                if r < 0.15:
                    self.start_walk(random.randint(geo.left(), geo.right() - self.width()))
                elif r < 0.22:   # follow the mouse for a bit
                    cur = QCursor.pos()
                    self.start_walk(cur.x() - self.width() // 2)

    # ---------- mouse
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press = e.globalPosition().toPoint()
            self._offset = self._press - self.frameGeometry().topLeft()
            self.dragging = False
            self.touch()

    def mouseMoveEvent(self, e):
        if self._press is None or not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        pos = e.globalPosition().toPoint()
        if not self.dragging and (pos - self._press).manhattanLength() > 6:
            self.dragging = True
            self.target_x = None
            self.set_state("jump")
        if self.dragging:
            self.move(pos - self._offset)
            self.moved.emit()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        was_drag = self.dragging
        self.dragging = False
        self._press = None
        self.touch()
        if was_drag:
            self.set_state("idle")
        else:
            if self.state == "sleep":
                self.set_state("wave")
            self.clicked.emit()

    def contextMenuEvent(self, e):
        self.touch()
        menu = QMenu(self)
        menu.addAction("Talk to Robert (microphone)").triggered.connect(self.mic_requested.emit)
        menu.addAction("Open command box").triggered.connect(self.type_requested.emit)
        menu.addSeparator()
        menu.addAction("Say hi").triggered.connect(lambda: self.external_state("wave"))
        menu.addAction("Go to sleep").triggered.connect(lambda: self.set_state("sleep"))
        menu.addSeparator()
        menu.addAction("Quit Robert").triggered.connect(self.quit_requested.emit)
        menu.exec(e.globalPos())
