
from typing import TypeVar

from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWebChannel import QWebChannel

from luminos.windows.Window import Window
from luminos.browser import Inspector
from luminos.browser.webengine import WebView
from luminos.utils import log, usertypes

Url = TypeVar('Url', str, QUrl)


class BrowserWindow(Window):
    webview = None
    _pendingLoad = False

    def __init__(self, app):
        super().__init__(app)
        self.channel = QWebChannel()

        self.webview = WebView.LWebView(private=None, parent=self)
        self.webview.toggleDevTools.connect(self.toggleInspector)
        self.webview.loadChanged.connect(self._loadChanged)
        self.layout.addWidget(self.webview)

    def _loadChanged(self, e):
        app = self.app
        if app is None:
            app = QApplication.instance()

        if e == usertypes.LoadEvent.BEFORE_LOAD and not self.bridgeInitialized:
            self._initBridge()
            self.bridgeInitialized = True

        from luminos.Application import Application
        # app is probably None in test
        if app is not None and isinstance(app, Application):
            page = self.webview.page()
            if e == usertypes.LoadEvent.BEFORE_LOAD:
                app.pluginManager.beforeLoad.emit(self.channel, page)
            elif e == usertypes.LoadEvent.STARTED:
                app.pluginManager.loadStarted.emit(page)
            elif e == usertypes.LoadEvent.FINISHED:
                app.pluginManager.loadFinished.emit(page)

    def _initBridge(self):
        log.webview.debug("Initializing web channel bridge...")
        page = self.webview.page()

        page.injectScript(":/qtwebchannel/qwebchannel.js", "QWebChannel API")
        page.injectScript(":/luminos/js/bridge.js", "Luminos Bridge")

        app = self.app
        if app is None:
            app = QApplication.instance()

        from luminos.Application import Application
        # app is probably None in test
        if app is not None and isinstance(app, Application):
            app.pluginManager.bridgeInitialize.emit(page)

        page.setWebChannel(self.channel)

    def loadScript(self, path, name):
        """Inject javascript to be loaded when document is created"""
        page = self.webview.page()
        script = self._createWebengineScript(path, name)
        page.scripts().insert(script)

    def showEvent(self, e):
        if self._pendingLoad:
            self.loadUrl(self.url)
            self._pendingLoad = False

        super().showEvent(e)

    def load(self, path):
        pass

    def loadUrl(self, url: str) -> None:

        if self.webview is None:
            self._pendingLoad = True
            self.url = url
        else:
            self.webview.setUrl(QUrl(url))

    def toggleInspector(self):
        if "webInspector" in dir(self) and self.webInspector is not None:
            page = self.webview.page()
            self.webInspector.toggle(page)
        else:
            page = self.webview.page()
            self.webInspector = Inspector.create(self.config)
            self.webInspector.onDestroyed.connect(self._onWebInspectorDestroyed)
            self.webInspector.toggle(page)

    def _onWebInspectorDestroyed(self):
        self.webInspector = None
