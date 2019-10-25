import os
import sys
from os import path
import typing
import gettext

from PyQt5.QtWidgets import QApplication
from luminos.core.Signal import Signal
from luminos.core.AbstractWindow import AbstractWindow
from luminos.utils import utils, log, standarddir
from luminos.utils import config
from luminos.utils.config import Configuration
from luminos.utils.constants import HAS_PYTHON_3_6


_ = gettext.gettext


class AbstractApplication(QApplication):

    windows: typing.List[AbstractWindow] = []
    windowAdded = Signal()
    windowRemoved = Signal()
    beforeRun = Signal()

    def __init__(self, argv, name):
        qt_argv = utils.cleanArgs(argv)
        super().__init__(qt_argv)

        self.aboutToQuit.connect(self._exiting)
        parser = utils.get_argparser()
        args = parser.parse_args(argv)

        log.init_log(args)
        log.init.debug("Log initialized.")

        args.name = name

        if args.version:
            from luminos.utils import version
            print(version.version())
            sys.exit(0)

        log.init.debug("Initializing directories...")
        standarddir.init(args)

        log.init.debug("Initializing application configuration...")
        if config.instance is None:
            self.config = Configuration(path.join(standarddir.config(), "{}.yml".format(name)))
        else:
            self.config = config.instance

        from PyQt5.QtWebEngineWidgets import QWebEnginePage
        if (hasattr(args, "enable_inspector") and not hasattr(QWebEnginePage, 'setInspectedPage')):  # only Qt < 5.11
            os.environ['QTWEBENGINE_REMOTE_DEBUGGING'] = str(utils.random_port())

    def _exiting(self):
        log.config.debug("saving configuration")
        if self.config is not None:
            self.config.save()

    def __init_subclass__(cls, **kwargs):
        if HAS_PYTHON_3_6:
            super().__init_subclass__()

        cls.__pre_init__()

    @classmethod
    def __pre_init__(cls):
        pass

    def exec_(self):
        self.beforeRun.emit()
        return super().exec_()

    def addWindow(self, window: AbstractWindow) -> None:
        self.windows.append(window)
        self.windowAdded.emit(window)

    def removeWindow(self, window: AbstractWindow) -> None:
        self.windows.remove(window)
        self.windowRemoved.emit(window)

    @classmethod
    def running(self) -> bool:
        return QApplication.instance() is not None
