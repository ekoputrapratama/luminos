import typing  # noqa

from luminos.windows.Window import Window
from luminos.utils import standarddir, log  # noqa
from luminos.core.Signal import Signal


class Controller(object):
    mainWindowChanged = Signal()
    app = None

    defaultUrl = None
    _mainWindow: Window = None

    @classmethod
    def setMainWindow(cls, window) -> None:
        cls._mainWindow = window
        cls.mainWindowChanged.emit(window)

    @classmethod
    def setDefaultUrl(cls, url: str) -> None:
        cls.defaultUrl = url

    def _onMainWindowChanged(self, window: Window):
        if self.defaultUrl is not None:
            window.loadUrl(self.defaultUrl)

        window.restoreState("main")
        window.onClose.connect(self._onMainWindowClosed)

    def _onMainWindowClosed(self):
        self._mainWindow.saveState("main")

    def _onWindowAdded(self, window: Window):
        if self._mainWindow is None and isinstance(window, Window):
            self.setMainWindow(window)

    def __init__(self, app):
        super().__init__()
        log.controller.debug("Initializing controller")
        self.app = app

        # listen for window added signal in case user is late to register their window
        app.windowAdded.connect(self._onWindowAdded)
        self.mainWindowChanged.connect(self._onMainWindowChanged)

        w: list = app.windows

        if self._mainWindow is not None and len(w) > 0:
            self.setMainWindow(w[0])
        elif self._mainWindow is not None:
            self._mainWindow.restoreState("main")
            if getattr(self, "defaultUrl") is not None:
                self._mainWindow.loadUrl(self.defaultUrl)
