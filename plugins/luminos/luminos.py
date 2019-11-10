import os

from luminos.utils import version, constants, standarddir
from luminos.core.Bridge import BridgeObject, Bridge, Variant
from luminos.Application import Application
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor

versionInstance = None
pluginManagerInstance = None
directoryInstance = None
paletteInstance = None
pathInstance = None
schemeInstance = None


class Version(BridgeObject):
    noop_signal = Bridge.signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @Bridge.property(str, notify=noop_signal)
    def CHROMIUM(self):
        return version._chromium_version()

    @Bridge.property(str, notify=noop_signal)
    def QT(self):
        return constants.qt_version()


class PluginManager(BridgeObject):
    noop_signal = Bridge.signal()
    pluginAdded = Bridge.signal(str)
    pluginRemoved = Bridge.signal(str)
    pluginActivated = Bridge.signal(str)
    pluginDeactivated = Bridge.signal(str)
    loadedPlugins = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        app = QApplication.instance()
        self._pluginManager = app.pluginManager
        self._pluginManager.pluginActivated.connect(lambda name: self.pluginActivated.emit(name))
        self._pluginManager.pluginDeactivated.connect(lambda name: self.pluginDeactivated.emit(name))
        self._pluginManager.pluginAdded.connect(self._onPluginAdded)
        self._pluginManager.pluginRemoved.connect(self._onPluginRemoved)

    def _onPluginAdded(self, name):
        self.pluginAdded.emit(name)

    def _onPluginRemoved(self, name):
        self.pluginRemoved.emit(name)

    @Bridge.property(Variant, notify=noop_signal)
    def loadedPlugins(self):
        return [key for key in self._pluginManager._loadedPlugins.keys()]

    @Bridge.method(str)
    def addPluginPath(self, path: str):
        self._pluginManager.addPluginPath(path)

    @Bridge.method(str)
    def enablePlugin(self, name: str):
        self._pluginManager.enablePlugin(name)

    @Bridge.method(str)
    def disablePlugin(self, name: str):
        self._pluginManager.disablePlugin(name)


class Directory(BridgeObject):
    noop_signal = Bridge.signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @Bridge.property(str, notify=noop_signal)
    def cache(self):
        return standarddir.cache()

    @Bridge.property(str, notify=noop_signal)
    def data(self):
        return standarddir.data()

    @Bridge.property(str, notify=noop_signal)
    def config(self):
        return standarddir.config()


class Scheme(BridgeObject):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        app = QApplication.instance()
        self.schemes = app.schemes

    @Bridge.method(str, result=str)
    def pathByScheme(self, scheme):
        return self.schemes[scheme]


class Path(BridgeObject):
    noop_signal = Bridge.signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @Bridge.method(str, result=bool)
    def exists(self, path: str):
        return os.path.exists(path)

    @Bridge.property(Variant, notify=noop_signal)
    def dataDirs(self):
        return [
            "/usr/share/luminos",
            "/usr/local/share/luminos",
            os.path.expanduser("~/.local/share/luminos")
        ]


class Palette(BridgeObject):
    noop_signal = Bridge.signal()

    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)

    @Bridge.property(str, notify=noop_signal)
    def baseColor(self):
        app: Application = Application.instance()
        color = app.mainWindow.style().standardPalette().color(QPalette.Base)
        return color.name(QColor.HexRgb)

    @Bridge.property(str, notify=noop_signal)
    def alternateBaseColor(self):
        app: Application = Application.instance()
        color = app.palette().color(QPalette.AlternateBase)
        return color.name(QColor.HexArgb)

    @Bridge.property(str, notify=noop_signal)
    def backgroundColor(self):
        app: Application = Application.instance()
        color = app.mainWindow.style().standardPalette().color(QPalette.Background)
        return color.name(QColor.HexRgb)

    @Bridge.property(str, notify=noop_signal)
    def foregroundColor(self):
        app: Application = Application.instance()
        color = app.palette().color(QPalette.Foreground)
        return color.name(QColor.HexArgb)

    @Bridge.property(str, notify=noop_signal)
    def brightTextColor(self):
        app: Application = Application.instance()
        color = app.palette().color(QPalette.BrightText)
        return color.name(QColor.HexArgb)

    @Bridge.property(str, notify=noop_signal)
    def textColor(self):
        app: Application = Application.instance()
        color = app.palette().color(QPalette.Text)
        return color.name(QColor.HexArgb)

    @Bridge.property(str, notify=noop_signal)
    def highlightColor(self):
        app: Application = Application.instance()
        color = app.palette().color(QPalette.Highlight)
        return color.name(QColor.HexArgb)

    @Bridge.property(str, notify=noop_signal)
    def hightlightedTextColor(self):
        app: Application = Application.instance()
        color = app.palette().color(QPalette.HighlightedText)
        return color.name(QColor.HexArgb)

    @Bridge.property(str, notify=noop_signal)
    def buttonColor(self):
        app: Application = Application.instance()
        color = app.palette().color(QPalette.Button)
        return color.name(QColor.HexArgb)

    @Bridge.property(str, notify=noop_signal)
    def buttonTextColor(self):
        app: Application = Application.instance()
        color = app.palette().color(QPalette.ButtonText)
        return color.name(QColor.HexArgb)


def beforeLoad(channel, page):
    global versionInstance, pluginManagerInstance, directoryInstance, paletteInstance, schemeInstance, pathInstance

    if pluginManagerInstance is None:
        pluginManagerInstance = PluginManager()

    if schemeInstance is None:
        schemeInstance = Scheme()

    channel.registerObject("Directory", directoryInstance)
    channel.registerObject("PluginManager", pluginManagerInstance)
    channel.registerObject("Version", versionInstance)
    channel.registerObject("Palette", paletteInstance)
    channel.registerObject("Path", pathInstance)
    channel.registerObject("Scheme", schemeInstance)


def activate():
    global paletteInstance, directoryInstance, versionInstance, pathInstance

    if paletteInstance is None:
        paletteInstance = Palette()

    if directoryInstance is None:
        directoryInstance = Directory()

    if versionInstance is None:
        versionInstance = Version()

    if pathInstance is None:
        pathInstance = Path()


def deactivate():
    global versionInstance, pluginManagerInstance, directoryInstance, pathInstance, schemeInstance, paletteInstance
    versionInstance = None
    pluginManagerInstance = None
    directoryInstance = None
    pathInstance = None
    schemeInstance = None
    paletteInstance = None
