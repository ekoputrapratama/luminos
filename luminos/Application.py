
import sys
import os
from os import path
import signal
import typing  # noqa
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWebEngineWidgets import QWebEngineProfile
from PyQt5.QtWebEngineCore import QWebEngineUrlScheme

import luminos
import luminos.resources
from luminos.core.AbstractApplication import AbstractApplication
from luminos.core.Controller import Controller
from luminos.core.PluginManager import PluginManager
from luminos.utils import log, standarddir, urlutils, qtutils, config
from luminos.windows.BrowserWindow import BrowserWindow
from luminos.browser.webengine.WebEngineSettings import WebEngineSettings, ProfileSetter, _SettingsWrapper
from luminos.utils.constants import HAS_PYTHON_3_6

l_app = None
RESTART_EXIT_CODE = 2


def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    # if QMessageBox.question(None, '', "Are you sure you want to quit?",
    #                         QMessageBox.Yes | QMessageBox.No,
    #                         QMessageBox.No) == QMessageBox.Yes:
    QApplication.quit()


def run(args):
    """"""
    signal.signal(signal.SIGINT, sigint_handler)

    global l_app
    """
    This attribute need to be set before QCoreApplication created,
    it will still show warning because QWebEngineView::initialize call this at the end.
    """
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

    l_app = Application(sys.argv)
    l_app.setOrganizationName("luminos")
    l_app.setApplicationName("luminos")
    l_app.setApplicationVersion(luminos.__version__)
    l_app.registerPluginDir(os.path.join(os.getcwd(), "plugins"))

    if len(args.url) == 0:
        p = os.path.join(os.getcwd(), "data", "static")
        l_app.registerApp(p)

    window = BrowserWindow(l_app)

    if len(args.url) > 0:
        window.loadUrl(args.url[0])

    # Python cannot handle signals while the Qt event loop is running.
    # so we need to use QTimer to let the interpreter run from time to time.
    # https://stackoverflow.com/questions/4938723/what-is-the-correct-way-to-make-my-pyqt-application-quit-when-killed-from-the-co
    timer = QTimer()
    timer.start(500)  # You may change this if you wish.
    timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.

    window.show()
    ret = l_app.exec_()
    return ret


class Application(AbstractApplication):
    schemes = {}
    pluginsDirs = []
    pluginManager: PluginManager = None

    def __init__(self, argv, name=None):
        if name is None:
            name = "luminos"
        super().__init__(argv, name)

        if QWebEngineUrlScheme is not None:
            if not QWebEngineUrlScheme.schemeByName(b"luminos").name():
                scheme = QWebEngineUrlScheme(b"luminos")
                scheme.setFlags(
                    QWebEngineUrlScheme.LocalScheme | QWebEngineUrlScheme.LocalAccessAllowed | QWebEngineUrlScheme.ContentSecurityPolicyIgnored | QWebEngineUrlScheme.SecureScheme
                )
                QWebEngineUrlScheme.registerScheme(scheme)

        self._initProfile()
        # self.interceptor = UrlRequestInterceptor()
        # self.profile.setRequestInterceptor(self.interceptor)
        log.init.debug("Initializing web setings...")
        config.instance.changed.connect(self._updateSettings)

        self.settings = WebEngineSettings(_SettingsWrapper(self.profile))
        self.settings.initSettings()

        self._setupSchemeHandler()
        self.pluginManager = PluginManager()
        self.controller = Controller(self)
        self.controller.mainWindowChanged.connect(self._mainWindowChanged)

    @classmethod
    def restart(cls):
        cls.exit(RESTART_EXIT_CODE)

    def _initProfile(self):
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.setter = ProfileSetter(self.profile)
        self.profile.setCachePath(
            os.path.join(standarddir.cache(), 'webengine'))
        self.profile.setPersistentStoragePath(
            os.path.join(standarddir.data(), 'webengine'))
        self.profile.setter.init_profile()
        self.profile.setter.set_persistent_cookie_policy()

    def _updateSettings(self, option, value):
        """Update global settings when qwebsettings changed."""
        self.settings.updateSetting(option)

        if option in ['content.headers.user_agent',
                      'content.headers.accept_language']:
            self.profile.setter.set_http_headers()
        elif option == 'content.cache.size':
            self.profile.setter.set_http_cache_size()
        elif (option == 'content.cookies.store' and qtutils.version_check('5.9', compiled=False)):  # https://bugreports.qt.io/browse/QTBUG-58650
            self.setter.set_persistent_cookie_policy()
        elif option == 'spellcheck.languages':
            self.profile.setter.set_dictionary_language()

    def _mainWindowChanged(self, window):
        self.mainWindow = window

    def _setupSchemeHandler(self):
        log.webview.debug("Initializing scheme handler...")
        from luminos.browser.webengine import WebEngineScheme

        self.schemeHandler = WebEngineScheme.LSchemeHandler()
        self.schemeHandler.install(self.profile, self.schemes)

    @classmethod
    def registerApp(self, directory: str) -> None:

        url = None
        if path.isabs(directory):
            if directory.endswith(".html"):
                url = "file://" + directory
            else:
                index = path.join(directory, "index.html")
                if path.exists(directory) and path.exists(index):
                    url = "file://" + index
                else:
                    log.url.warning(f"Expecting index.html to exists in directory {directory}")
                    return
        elif urlutils.is_url(directory):
            url = directory
        else:
            log.url.warning("Expecting a url or absolute path in registerApp")
            return

        Controller.setDefaultUrl(url)

    def registerPluginDir(self, directory: str) -> None:
        """"""
        if path.isabs(directory) and path.exists(directory):
            self.pluginManager.addPluginPath(directory)
        elif path.isabs(directory) and not path.exists(directory):
            log.plugins.debug("Plugin directory provided doesn't exists, trying to create the folder...")
            writable = os.access(path.dirname(directory), os.W_OK)
            if writable:
                os.makedirs(directory, 0o755, exist_ok=True)
                self.pluginManager.addPluginPath(directory)
            else:
                log.plugins.warning("Plugin directory provided is not writable, ignoring it.")

    @classmethod
    def registerUriScheme(self, name: str, base_path: str):
        if not name in self.schemes.keys():
            self.schemes[name] = base_path

            if not QWebEngineUrlScheme.schemeByName(name.encode()).name():
                scheme = QWebEngineUrlScheme(name.encode())
                scheme.setFlags(
                    QWebEngineUrlScheme.LocalScheme | QWebEngineUrlScheme.LocalAccessAllowed | QWebEngineUrlScheme.ContentSecurityPolicyIgnored | QWebEngineUrlScheme.SecureScheme
                )

                QWebEngineUrlScheme.registerScheme(scheme)

    def __init_subclass__(cls, **kwargs):
        if HAS_PYTHON_3_6:
            super().__init_subclass__()

        cls.__pre_init__()
