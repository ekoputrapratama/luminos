# import base64
# import binascii
from PyQt5.QtCore import QSize

from luminos.widgets import Layout
from luminos.core.Widget import LWidget
from luminos.utils import log  # noqa


def create(config, parent=None):
    """Get a WebKitInspector/WebEngineInspector.

    Args:
        parent: The Qt parent to set.
    """
    # Importing modules here so we don't depend on QtWebEngine without the
    # argument and to avoid circular imports.
    from luminos.browser.webengine.WebEngineInspector import WebEngineInspector
    return WebEngineInspector(config, parent)


class WebInspectorError(Exception):

    """Raised when the inspector could not be initialized."""


class AbstractWebInspector(LWidget):

    """A customized WebInspector which stores its geometry."""
    config = None

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._widget = None
        self._layout = Layout.WrapperLayout(self)
        self.restoreState("inspector")

    def _set_widget(self, widget):
        self._widget = widget
        self._layout.wrap(self, widget)

    def closeEvent(self, e):
        """Save the state when closed."""
        self.saveState("inspector")
        self.inspect(None)
        super().closeEvent(e)

    def restoreState(self, name: str):
        # check if the window state exists
        wcfg = self.config.get("windows.{}".format(name))
        if wcfg is not None:
            width = self.config.get("windows.{}.width".format(name))
            height = self.config.get("windows.{}.height".format(name))
            self.resize(QSize(width, height))

    def saveState(self, name: str):
        self.config.set("windows.{}.width".format(name), self.width())
        self.config.set("windows.{}.height".format(name), self.height())
        self.config.save()

    def inspect(self, page):
        """Inspect the given QWeb(Engine)Page."""
        raise NotImplementedError

    def toggle(self, page):
        """Show/hide the inspector."""
        if self._widget.isVisible():
            self.hide()
        else:
            self.inspect(page)
            self.show()
