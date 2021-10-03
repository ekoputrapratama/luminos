
import typing  # noqa
from PyQt5.QtCore import Qt, QSize, QUrl
from PyQt5.QtWidgets import QWidget, QDesktopWidget

from luminos.core.Signal import Signal
from luminos.utils import log
from luminos.utils.constants import HAS_PYTHON_3_6

Url = typing.TypeVar('Url', str, QUrl)


class WindowError(Exception):

    """Raised when the window could not be initialized."""


class AbstractWindow(QWidget):
    app = None
    config = None
    settings = None
    onClose = Signal()

    def __init__(self, application=None):
        """"""
        log.init.debug("initializing Window")
        super().__init__()

        # self register our window to application
        from luminos.core.AbstractApplication import AbstractApplication

        if application is not None and isinstance(application, AbstractApplication):
            self.app = application
            self.config = application.config
            self.app.addWindow(self)

        self.setWindowFlags(Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMinimumSize(QSize(640, 480))

    def closeEvent(self, e):
        super().closeEvent(e)
        self.onClose.emit()
        # unregister our window from application
        if self.app is not None:
            self.app.removeWindow(self)

    def __init_subclass__(cls, **kwargs):
        if HAS_PYTHON_3_6:
            super().__init_subclass__()

        cls.__pre_init__()

    @classmethod
    def __pre_init__(cls):
        pass

    def restoreState(self, name: str):
        width = self.config.get("windows.{}.width".format(name))
        height = self.config.get("windows.{}.height".format(name))
        if width is not None and height is not None:
            self.resize(QSize(width, height))

        maximized = self.config.get("windows.{}.maximized".format(name))
        if maximized is not None:
            if maximized:
                self.setWindowState(Qt.WindowMaximized)

        # move window position to the center of the screen
        centerPoint = QDesktopWidget().availableGeometry().center()
        frameGm = self.frameGeometry()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def saveState(self, name: str):
        maximized = self.isMaximized()

        if not maximized:
            self.config.set("windows.{}.width".format(name), self.width())
            self.config.set("windows.{}.height".format(name), self.height())

        self.config.set("windows.{}.maximized".format(name), maximized)

        self.config.save()
