from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QLayout

from luminos.utils import utils


class WrapperLayout(QLayout):

    """A Qt layout which simply wraps a single widget.

    This is used so the widget is hidden behind a defined API and can't
    easily be accidentally accessed.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._widget = None

    def addItem(self, _widget):
        raise utils.Unreachable

    def sizeHint(self):
        return self._widget.sizeHint()

    def itemAt(self, _index):
        return None

    def takeAt(self, _index):
        raise utils.Unreachable

    def setGeometry(self, rect):
        self._widget.setGeometry(rect)

    def wrap(self, container, widget):
        """Wrap the given widget in the given container."""
        self._widget = widget
        container.setFocusProxy(widget)
        widget.setParent(container)

    def unwrap(self):
        self._widget.setParent(None)
        self._widget.deleteLater()


class PseudoLayout(QLayout):

    """A layout which isn't actually a real layout.

    This is used to replace QWebEngineView's internal layout, as a WORKAROUND
    for https://bugreports.qt.io/browse/QTBUG-68224 and other related issues.

    This is partly inspired by https://codereview.qt-project.org/#/c/230894/
    which does something similar as part of Qt.
    """

    def addItem(self, item):
        assert self.parent() is not None
        item.widget().setParent(self.parent())

    def removeItem(self, item):
        item.widget().setParent(None)

    def count(self):
        return 0

    def itemAt(self, _pos):
        return None

    def widget(self):
        return self.parent().render_widget()

    def setGeometry(self, rect):
        """Resize the render widget when the view is resized."""
        widget = self.widget()
        if widget is not None:
            widget.setGeometry(rect)

    def sizeHint(self):
        """Make sure the view has the sizeHint of the render widget."""
        widget = self.widget()
        if widget is not None:
            return widget.sizeHint()
        return QSize()
