import os

from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings

from luminos.browser.Inspector import AbstractWebInspector, WebInspectorError


class WebEngineInspector(AbstractWebInspector):
    """"""

    def __init__(self, config, parent=None):
        super().__init__(config, parent)
        self.port = None
        view = QWebEngineView()
        settings = view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self._set_widget(view)

    def _inspect_old(self, page):
        """"""
        try:
            port = int(os.environ['QTWEBENGINE_REMOTE_DEBUGGING'])
        except KeyError:
            raise WebInspectorError(
                "QtWebEngine inspector is not enabled."
            )
        url = QUrl('http://localhost:{}/'.format(port))

        if page is None:
            self._widget.load(QUrl('about:blank'))
        else:
            self._widget.load(url)

    def _inspect_new(self, page):
        """Set up the inspector for Qt >= 5.11."""
        self._widget.page().setInspectedPage(page)

    def inspect(self, page):
        try:
            self._inspect_new(page)
        except AttributeError:
            self._inspect_old(page)
