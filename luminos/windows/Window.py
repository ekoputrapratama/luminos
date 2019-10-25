from PyQt5.QtWidgets import QVBoxLayout

from luminos.core.AbstractWindow import AbstractWindow
# from luminos.utils import log, usertypes


class Window(AbstractWindow):
    app = None
    bridgeInitialized = False

    def __init__(self, app):
        super().__init__(app)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
