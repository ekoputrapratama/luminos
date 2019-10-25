
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage

from luminos.core.Signal import Signal
from luminos.utils import usertypes, qtutils
from luminos.browser import Shared


class AbstractWebView(QWebEngineView):
    contentLoaded = False
    loadChanged = Signal(usertypes.LoadEvent)

    def __init__(self, parent):
        super().__init__(parent)
        self.loadStarted.connect(self._loadStarted)
        self.loadFinished.connect(self._loadFinished)

    def _loadStarted(self):
        self.contentLoaded = False
        self.loadChanged.emit(usertypes.LoadEvent.STARTED)

    def _loadFinished(self):
        self.contentLoaded = True
        self.loadChanged.emit(usertypes.LoadEvent.FINISHED)

    def load(self, url):
        self.setUrl(url)

    def setUrl(self, url):
        self.loadChanged.emit(usertypes.LoadEvent.BEFORE_LOAD)
        return super().setUrl(url)

    def loadProgress(self, progress):
        return super().loadProgress(progress)


class AbstractWebPage(QWebEnginePage):
    shuttingDown = Signal()
    _isShuttingDown = False

    def __init__(self, profile, parent):
        super().__init__(profile, parent)

    def shutdown(self):
        self._isShuttingDown = True
        self.shuttingDown.emit()

    def javaScriptAlert(self, securityOrigin, js_msg):
        """Override javaScriptAlert to use luminos prompts."""
        if self._isShuttingDown:
            return
        escape_msg = qtutils.version_check('5.11', compiled=False)
        try:
            Shared.javascript_alert(securityOrigin, js_msg,
                                    abort_on=[self.loadStarted,
                                              self.shuttingDown],
                                    escape_msg=escape_msg)
        except Shared.CallSuper:
            super().javaScriptAlert(securityOrigin, js_msg)

    def javaScriptConsoleMessage(self, level, message, lineNumber, source):
        level_map = {
            QWebEnginePage.InfoMessageLevel: usertypes.JsLogLevel.info,
            QWebEnginePage.WarningMessageLevel: usertypes.JsLogLevel.warning,
            QWebEnginePage.ErrorMessageLevel: usertypes.JsLogLevel.error,
        }
        Shared.javascript_log_message(level_map[level], source, lineNumber, message)

    def javaScriptPrompt(self, url, js_msg, defaultValue):
        """Override javaScriptPrompt to use luminos prompts."""
        escape_msg = qtutils.version_check('5.11', compiled=False)
        if self._isShuttingDown:
            return (False, "")
        try:
            return Shared.javascript_prompt(url, js_msg, defaultValue,
                                            abort_on=[self.loadStarted,
                                                      self.shuttingDown],
                                            escape_msg=escape_msg)
        except Shared.CallSuper:
            return super().javaScriptPrompt(url, js_msg, defaultValue)
