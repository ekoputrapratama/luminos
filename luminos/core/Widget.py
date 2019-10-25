from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget

from luminos.core.Signal import Signal


class LWidget(QWidget):
    onClose = Signal()
    onDestroyed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.destroyed.connect(LWidget._onDestroy)

    @classmethod
    def _onDestroy(cls):
        cls.onDestroyed.emit()

    def closeEvent(self, e):
        self.onClose.emit(e)
        super().closeEvent(e)
