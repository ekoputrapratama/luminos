"""Loggers and utilities related to logging."""


import os
import sys
import logging
import contextlib
import json
import warnings
import traceback
import collections
import faulthandler

from PyQt5 import QtCore

# Optional imports
try:
    import colorama
except ImportError:
    colorama = None
_log_inited = False
_args = None

COLORS = ["black", "red", "green", "yellow", "blue", "purple", "cyan", "white"]
COLOR_ESCAPES = {
    color: "\033[{}m".format(i) for i, color in enumerate(COLORS, start=30)
}
RESET_ESCAPE = "\033[0m"


# Log formats to use.
SIMPLE_FMT = "{green}{asctime:8}{reset} {log_color}{levelname}{reset}: " "{message}"
EXTENDED_FMT = (
    "{green}{asctime:8}{reset} "
    "{log_color}{levelname:8}{reset} "
    "{cyan}{name:10} {module}:{funcName}:{lineno}{reset} "
    "{log_color}{message}{reset}"
)
DATEFMT = "%H:%M:%S"
LOG_COLORS = {
    "VDEBUG": "white",
    "DEBUG": "white",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red",
}
# We first monkey-patch logging to support our VDEBUG level before getting the
# loggers.  Based on http://stackoverflow.com/a/13638084
# mypy doesn't know about this, so we need to ignore it.
VDEBUG_LEVEL = 9
logging.addLevelName(VDEBUG_LEVEL, "VDEBUG")
logging.VDEBUG = VDEBUG_LEVEL  # type: ignore

LOG_LEVELS = {
    "VDEBUG": logging.VDEBUG,  # type: ignore
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def vdebug(self, msg, *args, **kwargs):
    """Log with a VDEBUG level.

    VDEBUG is used when a debug message is rather verbose, and probably of
    little use to the end user or for post-mortem debugging, i.e. the content
    probably won't change unless the code changes.
    """
    if self.isEnabledFor(VDEBUG_LEVEL):
        # pylint: disable=protected-access
        self._log(VDEBUG_LEVEL, msg, args, **kwargs)
        # pylint: enable=protected-access


logging.Logger.vdebug = vdebug  # type: ignore

webview = logging.getLogger("webview")
url = logging.getLogger("url")
init = logging.getLogger("init")
signals = logging.getLogger("signals")
js = logging.getLogger("js")  # Javascript console messages
qt = logging.getLogger("qt")  # Warnings produced by Qt
plugins = logging.getLogger("plugins")
controller = logging.getLogger("controller")
config = logging.getLogger("config")
message = logging.getLogger("message")

LOGGER_NAMES = [
    "init", "url", "webview", "signals",
    "js", "qt", "ipc", "message", "config",
    "network", "sql", "plugins", "controller"
]

ram_handler = None
console_handler = None
console_filter = None


def init_log(args):
    """Init loggers based on the argparse namespace passed."""
    numeric_level = logging.CRITICAL

    if args.debug:
        numeric_level = logging.DEBUG

    console = _init_handlers(
        numeric_level, args.color, args.force_color
    )

    root = logging.getLogger()
    global console_filter
    if console is not None:
        negate = False
        names = None
        console_filter = LogFilter(names, negate)
        console.addFilter(console_filter)
        root.addHandler(console)

    # If we add no handler, we shouldn't process non visible logs at all
    #
    # disable blocks the current level (while setHandler shows the current
    # level), so -1 to avoid blocking handled messages.
    logging.disable(numeric_level - 1)
    root.setLevel(logging.NOTSET)
    logging.captureWarnings(True)
    _init_py_warnings()
    QtCore.qInstallMessageHandler(qt_message_handler)
    global _log_inited, _args
    _log_inited = True
    _args = args


def _init_py_warnings():
    """Initialize Python warning handling."""
    warnings.simplefilter("default")
    warnings.filterwarnings("ignore", module="pdb", category=ResourceWarning)
    # This happens in many qutebrowser dependencies...
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message="Using or importing the ABCs from "
        "'collections' instead of from 'collections.abc' "
        "is deprecated, and in 3.8 it will stop working",
    )


def _init_handlers(level, color, force_color):
    """Init log handlers.

    Args:
        level: The numeric logging level.
        color: Whether to use color if available.
        force_color: Force colored output.
        json_logging: Output log lines in JSON (this disables all colors).
    """
    global ram_handler
    global console_handler
    console_fmt, ram_fmt, use_colorama = _init_formatters(
        level, color, force_color
    )

    if sys.stderr is None:
        console_handler = None
    else:
        strip = False if force_color else None
        if use_colorama:
            stream = colorama.AnsiToWin32(sys.stderr, strip=strip)
        else:
            stream = sys.stderr
        console_handler = logging.StreamHandler(stream)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_fmt)

    # ram_handler = RAMHandler(capacity=ram_capacity)
    # ram_handler.setLevel(logging.NOTSET)
    # ram_handler.setFormatter(ram_fmt)
    # ram_handler.html_formatter = html_fmt

    return console_handler


def get_console_format(level):
    """Get the log format the console logger should use.

    Args:
        level: The numeric logging level.

    Return:
        Format of the requested level.
    """
    return EXTENDED_FMT if level <= logging.DEBUG else SIMPLE_FMT


def _init_formatters(level, color, force_color):
    """Init log formatters.

    Args:
        level: The numeric logging level.
        color: Whether to use color if available.
        force_color: Force colored output.
        json_logging: Format lines as JSON (disables all color).

    Return:
        A (console_formatter, ram_formatter, use_colorama) tuple.
        console_formatter/ram_formatter: logging.Formatter instances.
        use_colorama: Whether to use colorama.
    """
    console_fmt = get_console_format(level)
    ram_formatter = ColoredFormatter(EXTENDED_FMT, DATEFMT, "{", use_colors=False)
    if sys.stderr is None:
        return None, ram_formatter, False

    use_colorama = False
    color_supported = os.name == "posix" or colorama

    if color_supported and (sys.stderr.isatty() or force_color) and color:
        use_colors = True
        if colorama and os.name != "posix":
            use_colorama = True
    else:
        use_colors = False

    console_formatter = ColoredFormatter(
        console_fmt, DATEFMT, "{", use_colors=use_colors
    )
    return console_formatter, ram_formatter, use_colorama


def change_console_formatter(level):
    """Change console formatter based on level.

    Args:
        level: The numeric logging level
    """
    if not isinstance(console_handler.formatter, ColoredFormatter):
        # JSON Formatter being used for end2end tests
        pass

    use_colors = console_handler.formatter.use_colors
    console_fmt = get_console_format(level)
    console_formatter = ColoredFormatter(
        console_fmt, DATEFMT, "{", use_colors=use_colors
    )
    console_handler.setFormatter(console_formatter)


def qt_message_handler(msg_type, context, msg):
    """Qt message handler to redirect qWarning etc. to the logging system.

    Args:
        QtMsgType msg_type: The level of the message.
        QMessageLogContext context: The source code location of the message.
        msg: The message text.
    """
    # Mapping from Qt logging levels to the matching logging module levels.
    # Note we map critical to ERROR as it's actually "just" an error, and fatal
    # to critical.
    qt_to_logging = {
        QtCore.QtDebugMsg: logging.DEBUG,
        QtCore.QtWarningMsg: logging.WARNING,
        QtCore.QtCriticalMsg: logging.ERROR,
        QtCore.QtFatalMsg: logging.CRITICAL,
    }
    try:
        qt_to_logging[QtCore.QtInfoMsg] = logging.INFO
    except AttributeError:
        # While we don't support Qt < 5.5 anymore, logging still needs to work
        pass

    # Change levels of some well-known messages to debug so they don't get
    # shown to the user.
    #
    # If a message starts with any text in suppressed_msgs, it's not logged as
    # error.
    suppressed_msgs = [
        # PNGs in Qt with broken color profile
        # https://bugreports.qt.io/browse/QTBUG-39788
        (
            "libpng warning: iCCP: Not recognizing known sRGB profile that has "
            "been edited"
        ),
        "libpng warning: iCCP: known incorrect sRGB profile",
        # Hopefully harmless warning
        "OpenType support missing for script ",
        # Error if a QNetworkReply gets two different errors set. Harmless Qt
        # bug on some pages.
        # https://bugreports.qt.io/browse/QTBUG-30298
        (
            "QNetworkReplyImplPrivate::error: Internal problem, this method must "
            "only be called once."
        ),
        # Sometimes indicates missing text, but most of the time harmless
        "load glyph failed ",
        # Harmless, see https://bugreports.qt.io/browse/QTBUG-42479
        (
            "content-type missing in HTTP POST, defaulting to "
            "application/x-www-form-urlencoded. "
            "Use QNetworkRequest::setHeader() to fix this problem."
        ),
        # https://bugreports.qt.io/browse/QTBUG-43118
        "Using blocking call!",
        # Hopefully harmless
        (
            '"Method "GetAll" with signature "s" on interface '
            '"org.freedesktop.DBus.Properties" doesn\'t exist'
        ),
        (
            '"Method \\"GetAll\\" with signature \\"s\\" on interface '
            '\\"org.freedesktop.DBus.Properties\\" doesn\'t exist\\n"'
        ),
        "WOFF support requires QtWebKit to be built with zlib support.",
        # Weird Enlightment/GTK X extensions
        'QXcbWindow: Unhandled client message: "_E_',
        'QXcbWindow: Unhandled client message: "_ECORE_',
        'QXcbWindow: Unhandled client message: "_GTK_',
        # Happens on AppVeyor CI
        "SetProcessDpiAwareness failed:",
        # https://bugreports.qt.io/browse/QTBUG-49174
        (
            "QObject::connect: Cannot connect (null)::stateChanged("
            "QNetworkSession::State) to "
            "QNetworkReplyHttpImpl::_q_networkSessionStateChanged("
            "QNetworkSession::State)"
        ),
        # https://bugreports.qt.io/browse/QTBUG-53989
        (
            "Image of format '' blocked because it is not considered safe. If "
            "you are sure it is safe to do so, you can white-list the format by "
            "setting the environment variable QTWEBKIT_IMAGEFORMAT_WHITELIST="
        ),
        # Installing Qt from the installer may cause it looking for SSL3 or
        # OpenSSL 1.0 which may not be available on the system
        "QSslSocket: cannot resolve ",
        "QSslSocket: cannot call unresolved function ",
        # When enabling debugging with QtWebEngine
        (
            "Remote debugging server started successfully. Try pointing a "
            "Chromium-based browser to "
        ),
        # https://github.com/qutebrowser/qutebrowser/issues/1287
        "QXcbClipboard: SelectionRequest too old",
        # https://github.com/qutebrowser/qutebrowser/issues/2071
        'QXcbWindow: Unhandled client message: ""',
        # https://codereview.qt-project.org/176831
        "QObject::disconnect: Unexpected null parameter",
        # https://bugreports.qt.io/browse/QTBUG-76391
        "Attribute Qt::AA_ShareOpenGLContexts must be set before "
        "QCoreApplication is created.",
    ]
    # not using utils.is_mac here, because we can't be sure we can successfully
    # import the utils module here.
    if sys.platform == "darwin":
        suppressed_msgs += [
            # https://bugreports.qt.io/browse/QTBUG-47154
            (
                "virtual void QSslSocketBackendPrivate::transmit() SSLRead "
                "failed with: -9805"
            )
        ]

    if not msg:
        msg = "Logged empty message!"

    if any(msg.strip().startswith(pattern) for pattern in suppressed_msgs):
        level = logging.DEBUG
    else:
        level = qt_to_logging[msg_type]

    if context.function is None:
        func = "none"
    elif ":" in context.function:
        func = '"{}"'.format(context.function)
    else:
        func = context.function

    if context.category is None or context.category == "default":
        name = "qt"
    else:
        name = "qt-" + context.category
    if msg.splitlines()[0] == (
        "This application failed to start because it "
        "could not find or load the Qt platform plugin "
        '"xcb".'
    ):
        # Handle this message specially.
        msg += (
            "\n\nOn Archlinux, this should fix the problem:\n"
            "    pacman -S libxkbcommon-x11"
        )
        faulthandler.disable()

    if _args.debug:
        stack = "".join(traceback.format_stack())
    else:
        stack = None
    record = qt.makeRecord(
        name, level, context.file, context.line, msg, (), None, func, sinfo=stack
    )
    qt.handle(record)


@contextlib.contextmanager
def ignore_py_warnings(**kwargs):
    """Contextmanager to temporarily disable certain Python warnings."""
    warnings.filterwarnings('ignore', **kwargs)
    yield
    if _log_inited:
        _init_py_warnings()


class QtWarningFilter(logging.Filter):

    """Filter to filter Qt warnings.

    Attributes:
        _pattern: The start of the message.
    """

    def __init__(self, pattern):
        super().__init__()
        self._pattern = pattern

    def filter(self, record):
        """Determine if the specified record is to be logged."""
        do_log = not record.msg.strip().startswith(self._pattern)
        return do_log


class LogFilter(logging.Filter):

    """Filter to filter log records based on the commandline argument.

    The default Filter only supports one name to show - we support a
    comma-separated list instead.

    Attributes:
        names: A list of record names to filter.
        negated: Whether names is a list of records to log or to suppress.
    """

    def __init__(self, names, negate=False):
        super().__init__()
        self.names = names
        self.negated = negate

    def filter(self, record):
        """Determine if the specified record is to be logged."""
        if self.names is None:
            return True
        if record.levelno > logging.DEBUG:
            # More important than DEBUG, so we won't filter at all
            return True
        for name in self.names:
            if record.name == name:
                return not self.negated
            elif not record.name.startswith(name):
                continue
            elif record.name[len(name)] == ".":
                return not self.negated
        return self.negated


class RAMHandler(logging.Handler):

    """Logging handler which keeps the messages in a deque in RAM.

    Loosely based on logging.BufferingHandler which is unsuitable because it
    uses a simple list rather than a deque.

    Attributes:
        _data: A deque containing the logging records.
    """

    def __init__(self, capacity):
        super().__init__()
        self.html_formatter = None
        if capacity != -1:
            self._data = collections.deque(maxlen=capacity)
        else:
            self._data = collections.deque()

    def emit(self, record):
        if record.levelno >= logging.DEBUG:
            # We don't log VDEBUG to RAM.
            self._data.append(record)

    def dump_log(self, html=False, level="vdebug"):
        """Dump the complete formatted log data as string.

        FIXME: We should do all the HTML formatter via jinja2.
        (probably obsolete when moving to a widget for logging,
        https://github.com/qutebrowser/qutebrowser/issues/34
        """
        minlevel = LOG_LEVELS.get(level.upper(), VDEBUG_LEVEL)
        fmt = self.html_formatter.format if html else self.format
        self.acquire()
        try:
            lines = [fmt(record) for record in self._data if record.levelno >= minlevel]
        finally:
            self.release()
        return "\n".join(lines)

    def change_log_capacity(self, capacity):
        self._data = collections.deque(self._data, maxlen=capacity)


class ColoredFormatter(logging.Formatter):

    """Logging formatter to output colored logs.

    Attributes:
        use_colors: Whether to do colored logging or not.
    """

    def __init__(self, fmt, datefmt, style, *, use_colors):
        super().__init__(fmt, datefmt, style)
        self.use_colors = use_colors

    def format(self, record):
        if self.use_colors:
            color_dict = dict(COLOR_ESCAPES)
            color_dict["reset"] = RESET_ESCAPE
            log_color = LOG_COLORS[record.levelname]
            color_dict["log_color"] = COLOR_ESCAPES[log_color]
        else:
            color_dict = {color: "" for color in COLOR_ESCAPES}
            color_dict["reset"] = ""
            color_dict["log_color"] = ""
        record.__dict__.update(color_dict)
        return super().format(record)


class JSONFormatter(logging.Formatter):

    """Formatter for JSON-encoded log messages."""

    def format(self, record):
        obj = {}
        for field in [
            "created",
            "msecs",
            "levelname",
            "name",
            "module",
            "funcName",
            "lineno",
            "levelno",
        ]:
            obj[field] = getattr(record, field)
        obj["message"] = record.getMessage()
        if record.exc_info is not None:
            obj["traceback"] = super().formatException(record.exc_info)
        return json.dumps(obj)
