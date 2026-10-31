"""Start Robert here:  python main.py"""
import sys

from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from pet import PetWindow, Bubble, CommandPanel, Bridge
from controller import Controller


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    bridge = Bridge()
    pet = PetWindow()
    bubble = Bubble()
    panel = CommandPanel()
    controller = Controller(bridge)
    was_open = {"v": False}

    # ---------- the command panel (click Robert to open or close it)
    def open_panel():
        pet.hold = True
        bubble.anchor = panel
        panel.popup(pet)

    def close_panel():
        pet.hold = False
        bubble.anchor = pet
        bubble.reposition()

    def toggle_panel():
        if panel.isVisible():
            panel.close_panel()
        else:
            open_panel()

    def hide_all():
        was_open["v"] = panel.isVisible()
        pet.hide(); bubble.hide(); panel.hide()

    def show_all():
        pet.show()
        if was_open["v"]:
            open_panel()

    def follow_pet():
        if panel.isVisible():
            panel.follow(pet)
        if bubble.isVisible():
            bubble.reposition()

    # ---------- screen updates (always on the main thread)
    bridge.say.connect(lambda text, ms: bubble.show_text(text, panel if panel.isVisible() else pet, ms))
    bridge.state.connect(pet.external_state)
    bridge.quit_app.connect(app.quit)
    bridge.hide_pet.connect(hide_all)
    bridge.show_pet.connect(show_all)
    bridge.open_typebox.connect(open_panel)
    pet.moved.connect(follow_pet)

    # ---------- what you do with the mouse
    pet.clicked.connect(toggle_panel)              # click Robert -> command box
    pet.type_requested.connect(open_panel)
    pet.mic_requested.connect(controller.on_click)
    pet.quit_requested.connect(app.quit)
    panel.submitted.connect(controller.submit_text)
    panel.mic_clicked.connect(controller.on_click)
    panel.closed.connect(close_panel)

    # little icon near the clock, so you can always quit
    tray = QSystemTrayIcon(QIcon(pet.frames["idle"][0]), app)
    menu = QMenu()
    show_action = QAction("Show Robert")
    show_action.triggered.connect(lambda: (pet.show(), pet.raise_()))
    quit_action = QAction("Quit Robert")
    quit_action.triggered.connect(app.quit)
    menu.addAction(show_action)
    menu.addAction(quit_action)
    tray.setContextMenu(menu)
    tray.setToolTip("Robert")
    tray.show()

    if not pet.has_real_sprites:
        print("NOTE: no sprite sheet or named sprites were found, so I drew a simple puppy. See the guide, Step 2.")

    pet.show()
    app.aboutToQuit.connect(controller.stop)
    controller.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
