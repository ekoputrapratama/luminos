import typing  # noqa

from PyQt5.QtCore import QUrl, QFile
from PyQt5.QtWidgets import QMenu
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWebEngineWidgets import QWebEngineScript

from luminos.core.Signal import Signal
from luminos.core.AbstractWebEngine import AbstractWebView, AbstractWebPage
from luminos.utils import config

Url = typing.TypeVar('Url', str, QUrl)


class LWebView(AbstractWebView):
    toggleDevTools = Signal()

    def __init__(self, *, private, parent=None):
        super().__init__(parent)
        theme_color = self.style().standardPalette().color(QPalette.Base)
        page = LWebEnginePage(theme_color=theme_color, profile=None, parent=self)
        self.setPage(page)

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        reloadAction = menu.addAction("Reload")
        openDevToolsAction = menu.addAction("Open developer tools")
        action = menu.exec_(self.mapToGlobal(e.pos()))
        if action == openDevToolsAction:
            self.toggleDevTools.emit()
        elif action == reloadAction:
            self.reload()

    def shutdown(self):
        self.page().shutdown()

        # def createWindow(self, wintype):
        """Called by Qt when a page wants to create a new window.

        This function is called from the createWindow() method of the
        associated QWebEnginePage, each time the page wants to create a new
        window of the given type. This might be the result, for example, of a
        JavaScript request to open a document in a new window.

        Args:
            wintype: This enum describes the types of window that can be
                     created by the createWindow() function.

                     QWebEnginePage::WebBrowserWindow:
                         A complete web browser window.
                     QWebEnginePage::WebBrowserTab:
                         A web browser tab.
                     QWebEnginePage::WebDialog:
                         A window without decoration.
                     QWebEnginePage::WebBrowserBackgroundTab:
                         A web browser tab without hiding the current visible
                         WebEngineView.

        Return:
            The new QWebEngineView object.
        """
        # debug_type = debug.qenum_key(QWebEnginePage, wintype)
        # background = config.val.tabs.background

        # # log.webview.debug(
        # #     "createWindow with type {}, background {}".format(debug_type, background)
        # # )

        # if wintype == QWebEnginePage.WebBrowserWindow:
        #     # Shift-Alt-Click
        #     target = usertypes.ClickTarget.window
        # elif wintype == QWebEnginePage.WebDialog:
        #     # log.webview.warning(
        #     #     "{} requested, but we don't support " "that!".format(debug_type)
        #     # )
        #     target = usertypes.ClickTarget.tab
        # elif wintype == QWebEnginePage.WebBrowserTab:
        #     # Middle-click / Ctrl-Click with Shift
        #     # FIXME:qtwebengine this also affects target=_blank links...
        #     if background:
        #         target = usertypes.ClickTarget.tab
        #     else:
        #         target = usertypes.ClickTarget.tab_bg
        # elif wintype == QWebEnginePage.WebBrowserBackgroundTab:
        #     # Middle-click / Ctrl-Click
        #     if background:
        #         target = usertypes.ClickTarget.tab_bg
        #     else:
        #         target = usertypes.ClickTarget.tab
        # else:
        #     raise ValueError("Invalid wintype {}".format(debug_type))

        # tab = shared.get_tab(self._win_id, target)
        # return tab._widget  # pylint: disable=protected-access


def _createWebengineScript(path: Url, name: str, injectionPoint=None, isStylesheet: bool = False) -> QWebEngineScript:

    if injectionPoint is None:
        injectionPoint = QWebEngineScript.DocumentCreation

    script = QWebEngineScript()
    script_file = QFile(path)

    if script_file.open(QFile.ReadOnly):
        script_string = str(script_file.readAll(), 'utf-8')
        script.setInjectionPoint(injectionPoint)
        script.setName(name)
        script.setRunsOnSubFrames(True)
        script.setWorldId(QWebEngineScript.MainWorld)
        if isStylesheet:
            source = ("(function(){"
                      ""
                      "const css = document.createElement('style');\n"
                      "css.type = 'text/css';\n"
                      "css.innerText = `" + script_string.strip() + "`\n"
                      "document.head.appendChild(css);\n"
                      "})()")
            script.setSourceCode(source)
        else:
            script.setSourceCode(script_string)

    return script


class LWebEnginePage(AbstractWebPage):

    def __init__(self, *, theme_color, profile, parent=None):
        super().__init__(profile, parent)
        self._isShuttingDown = False
        self._theme_color = theme_color
        self._set_bg_color(None, None)
        config.instance.changed.connect(self._set_bg_color)

    def _onShuttingDown(self):
        self._isShuttingDown = True

    def shutdown(self):
        self._isShuttingDown = True
        self.shuttingDown.emit()

    def injectScript(self, path: Url, name: str, injectionPoint=None):
        """Inject javascript to a web page."""
        script = _createWebengineScript(path, name, injectionPoint, False)
        self.scripts().insert(script)

    def injectStylesheet(self, path: Url, name: str, injectionPoint=None):
        """Inject stylesheet to a web page."""
        script = _createWebengineScript(path, name, injectionPoint, True)
        self.scripts().insert(script)

    @config.change_filter("colors.webpage.bg")
    def _set_bg_color(self, option, value):
        col = config.instance.get("colors.webpage.bg")
        if col is None:
            col = self._theme_color.name(QColor.HexArgb)
            config.instance.set("colors.webpage.bg", col)

        self.setBackgroundColor(QColor(col))
