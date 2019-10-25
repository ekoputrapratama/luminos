import sys
import faulthandler
import signal
import datetime
import traceback
import importlib


START_TIME = datetime.datetime.now()


def _missing_str(name, *, webengine=False):
    """Get an error string for missing packages.

    Args:
        name: The name of the package.
        webengine: Whether this is checking the QtWebEngine package
    """
    blocks = ["Fatal error: <b>{}</b> is required to run luminos but "
              "could not be imported! Maybe it's not installed?".format(name),
              "<b>The error encountered was:</b><br />%ERROR%"]
    lines = ['Please search for the python3 version of {} in your '
             'distributions packages, or see '
             'https://github.com/'
             .format(name)]
    blocks.append('<br />'.join(lines))
    if not webengine:
        lines = ['<b>If you installed a luminos package for your '
                 'distribution, please report this as a bug.</b>']
        blocks.append('<br />'.join(lines))
    return '<br /><br />'.join(blocks)


def _die(message, exception=None):
    """Display an error message using Qt and quit.

    We import the imports here as we want to do other stuff before the imports.

    Args:
        message: The message to display.
        exception: The exception object if we're handling an exception.
    """
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import Qt
    if (('--debug' in sys.argv or '--no-err-windows' in sys.argv) and
            exception is not None):
        print(file=sys.stderr)
        traceback.print_exc()
    app = QApplication(sys.argv)
    if '--no-err-windows' in sys.argv:
        print(message, file=sys.stderr)
        print("Exiting because of --no-err-windows.", file=sys.stderr)
    else:
        if exception is not None:
            message = message.replace('%ERROR%', str(exception))
        msgbox = QMessageBox(QMessageBox.Critical, "luminos: Fatal error!",
                             message)
        msgbox.setTextFormat(Qt.RichText)
        msgbox.resize(msgbox.sizeHint())
        msgbox.exec_()
    app.quit()
    sys.exit(1)


def init_faulthandler(fileobj=sys.__stderr__):
    """Enable faulthandler module if available.

    This print a nice traceback on segfaults.

    We use sys.__stderr__ instead of sys.stderr here so this will still work
    when sys.stderr got replaced, e.g. by "Python Tools for Visual Studio".

    Args:
        fobj: An opened file object to write the traceback to.
    """
    if fileobj is None:
        # When run with pythonw.exe, sys.__stderr__ can be None:
        # https://docs.python.org/3/library/sys.html#sys.__stderr__
        # If we'd enable faulthandler in that case, we just get a weird
        # exception, so we don't enable faulthandler if we have no stdout.
        #
        # Later when we have our data dir available we re-enable faulthandler
        # to write to a file so we can display a crash to the user at the next
        # start.
        return
    faulthandler.enable(fileobj)
    if (hasattr(faulthandler, 'register') and hasattr(signal, 'SIGUSR1') and sys.stderr is not None):
        # If available, we also want a traceback on SIGUSR1.
        faulthandler.register(signal.SIGUSR1)


def check_qt_version():
    """Check if the Qt version is recent enough."""
    from PyQt5.QtCore import (qVersion, QT_VERSION, PYQT_VERSION,
                              PYQT_VERSION_STR)
    from pkg_resources import parse_version
    from luminos.utils import log
    parsed_qversion = parse_version(qVersion())
    from luminos.utils import constants
    if (QT_VERSION < 0x050701 or PYQT_VERSION < 0x050700 or
            parsed_qversion < parse_version('5.7.1')):

        text = ("Fatal error: Qt >= 5.7.1 and PyQt >= 5.7 are required, "
                "but Qt {} / PyQt {} is installed.".format(constants.qt_version(),
                                                           PYQT_VERSION_STR))
        _die(text)

    if qVersion().startswith('5.8.'):
        log.init.warning("Running luminos with Qt 5.8 is untested and "
                         "unsupported!")

    if (parsed_qversion >= parse_version('5.12') and
            (PYQT_VERSION < 0x050c00 or QT_VERSION < 0x050c00)):
        log.init.warning("Combining PyQt {} with Qt {} is unsupported! Ensure "
                         "all versions are newer than 5.12 to avoid potential "
                         "issues.".format(PYQT_VERSION_STR, constants.qt_version()))


def check_pyqt_core():
    """Check if PyQt core is installed."""
    try:
        import PyQt5.QtCore  # noqa
    except ImportError as e:
        text = _missing_str('PyQt5')
        text = text.replace('<b>', '')
        text = text.replace('</b>', '')
        text = text.replace('<br />', '\n')
        text = text.replace('%ERROR%', str(e))
        if '--debug' in sys.argv or '--no-err-windows' in sys.argv:
            print(file=sys.stderr)
            traceback.print_exc()
        sys.exit(1)


def check_ssl_support():
    """Check if SSL support is available."""
    try:
        from PyQt5.QtNetwork import QSslSocket  # noqa
    except ImportError:
        _die("Fatal error: Your Qt is built without SSL support.")


def _check_modules(modules):
    """Make sure the given modules are available."""
    from luminos.utils import log

    for name, text in modules.items():
        try:
            # https://bitbucket.org/fdik/pypeg/commits/dd15ca462b532019c0a3be1d39b8ee2f3fa32f4e
            # pylint: disable=bad-continuation
            with log.ignore_py_warnings(
                category=DeprecationWarning,
                message=r'invalid escape sequence'
            ), log.ignore_py_warnings(
                category=ImportWarning,
                message=r'Not importing directory .*: missing __init__'
            ):
                # pylint: enable=bad-continuation
                importlib.import_module(name)
        except ImportError as e:
            _die(text, e)


def check_libraries():
    """Check if all needed Python libraries are installed."""
    modules = {
        'pkg_resources': _missing_str("pkg_resources/setuptools"),
        'yaml': _missing_str("PyYAML"),
        'attr': _missing_str("attrs"),
        'PyQt5.QtQml': _missing_str("PyQt5.QtQml"),
        'PyQt5.QtSql': _missing_str("PyQt5.QtSql"),
        'PyQt5.QtOpenGL': _missing_str("PyQt5.QtOpenGL"),
        'ruamel.yaml': _missing_str("ruamel.yaml")
    }
    _check_modules(modules)


def init_log(args):
    """Initialize logging.

    Args:
        args: The argparse namespace.
    """
    from luminos.utils import log
    log.init_log(args)
    log.init.debug("Log initialized.")


def early_init(args):
    """Do all needed early initialization.

    Note that it's vital the other earlyinit functions get called in the right
    order!

    Args:
        args: The argparse namespace.
    """
    # First we initialize the faulthandler as early as possible, so we
    # theoretically could catch segfaults occurring later during earlyinit.
    init_faulthandler()
    # Here we check if QtCore is available, and if not, print a message to the
    # console or via Tk.
    check_pyqt_core()
    # Init logging as early as possible
    # init_log(args)
    # Now we can be sure QtCore is available, so we can print dialogs on
    # errors, so people only using the GUI notice them as well.
    check_libraries()
    check_qt_version()
    # configure_pyqt()
    check_ssl_support()
