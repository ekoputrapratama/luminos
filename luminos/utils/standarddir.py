import os
import sys  # noqa
import enum

from PyQt5.QtCore import QStandardPaths  # noqa

from luminos.utils import log, utils, qtutils


# The cached locations
_locations = {}
APPNAME = "luminos"


class EmptyValueError(Exception):

    """Error raised when QStandardPaths returns an empty value."""


class _Location(enum.Enum):
    """A key for _locations."""

    config = 1
    data = 2
    install = 3
    cache = 4


def defaultPluginsDir():
    dirs = [
        "/usr/lib/luminos/plugins",
        "/usr/local/lib/luminos/plugins",
        os.path.expanduser("~/.local/lib/luminos/plugins")
    ]

    for directory in dirs:
        if not os.path.exists(directory) and os.access(directory, os.W_OK):
            os.makedirs(directory)

    return dirs


def _fromArgs(typ, args):
    overridden = False
    path = None

    if args is not None:
        if typ == QStandardPaths.ConfigLocation and getattr(args, "configdir") is not None:
            if not os.path.isabs(args.configdir):
                args.configdir = path.abspath(args.configdir)

            path = args.configdir
            overridden = True

        elif typ == QStandardPaths.DataLocation and getattr(args, "datadir") is not None:
            if not os.path.isabs(args.datadir):
                args.configdir = path.abspath(args.datadir)

            path = args.datadir
            overridden = True
        elif typ == QStandardPaths.CacheLocation and getattr(args, "cachedir") is not None:
            if not os.path.isabs(args.cachedir):
                args.cachedir = path.abspath(args.cachedir)

            path = args.cachedir
            overridden = True

    if overridden:
        writable = os.access(path, os.W_OK)
        if not writable:
            path = _writable_location(args, typ)

    return overridden, path


def _appendBashrc(text: str):
    # try to write this thing in user .bashrc
    bashrc_path = os.path.expanduser("~/.bashrc")
    with open(bashrc_path, "a+") as f:
        f.write(text)


def _ensureXdgVariables():

    if not 'XDG_CONFIG_HOME' in os.environ:
        path = os.path.expanduser('~/.config')
        _appendBashrc(f'\nexport XDG_CONFIG_HOME="{path}"\n')

    if not 'XDG_DATA_HOME' in os.environ:
        path = os.path.expanduser('~/.local/share')
        _appendBashrc(f'\nexport XDG_DATA_HOME="{path}"\n')

    if not 'XDG_CACHE_HOME' in os.environ:
        path = os.path.expanduser('~/.cache')
        _appendBashrc(f'\nexport XDG_CACHE_HOME="{path}"\n')


def _writable_location(typ):
    """Wrapper around QStandardPaths.writableLocation.

    Arguments:
        typ: A QStandardPaths::StandardLocation member.
    """
    typ_str = qtutils.qenum_key(QStandardPaths, typ)

    # Types we are sure we handle correctly below.
    assert typ in [
        QStandardPaths.ConfigLocation, QStandardPaths.DataLocation,
        QStandardPaths.CacheLocation, QStandardPaths.DownloadLocation,
        QStandardPaths.RuntimeLocation, QStandardPaths.TempLocation], typ_str

    # with _unset_organization():
    # path = QStandardPaths.writableLocation(typ)
    # if path.endswith(".py"):
    #     path = path.replace(".py", "")

    if typ == QStandardPaths.DataLocation:
        default = os.path.expanduser("~/.local/share")
        path = os.getenv("XDG_DATA_HOME", default)
    elif typ == QStandardPaths.ConfigLocation:
        default = os.path.expanduser("~/.config")
        path = os.getenv("XDG_CONFIG_HOME", default)
    elif typ == QStandardPaths.CacheLocation:
        default = os.path.expanduser("~/.cache")
        path = os.getenv("XDG_CACHE_HOME", default)

    log.init.debug("writable location for {}: {}".format(typ_str, path))
    if not path:
        raise EmptyValueError("QStandardPaths returned an empty value!")

    # Qt seems to use '/' as path separator even on Windows...
    path = path.replace('/', os.sep)
    global APPNAME
    # Add the application name to the given path if needed.
    # This is in order for this to work without a QApplication (and thus
    # QStandardsPaths not knowing the application name).

    if (typ != QStandardPaths.DownloadLocation and path.split(os.sep)[-1] != APPNAME):
        path = os.path.join(path, APPNAME)

    return path


def _initConfigDir(args):
    """
    Initialize the location for configs.
    this can be overridden by setting --configdir=/path/to/config/directory when running the executable.
    """
    log.init.debug("initializing config directory...")
    _locations.pop(_Location.config, None)  # Remove old state

    typ = QStandardPaths.ConfigLocation
    overridden, path = _fromArgs(typ, args)

    if not overridden:
        if utils.isLinux:
            path = _writable_location(typ)

    _create(path)
    _locations[_Location.config] = path


def config() -> str:
    """Get the location for the config directory.

    If auto=True is given, get the location for the autoconfig.yml directory,
    which is different on macOS.
    """
    return _locations[_Location.config]


def _initDataDir(args):
    """
    Initialize the location for data.
    this can be overridden by setting --datadir=/path/to/data/directory when running the executable.
    """
    log.init.debug("initializing data directory...")
    _locations.pop(_Location.data, None)  # Remove old state

    typ = QStandardPaths.DataLocation
    overridden, path = _fromArgs(typ, args)

    if not overridden:
        if utils.isLinux:
            path = _writable_location(typ)

    _create(path)
    _locations[_Location.data] = path


def data() -> str:
    return _locations[_Location.data]


def _initCacheDir(args):
    """Initialize the location for the cache."""
    typ = QStandardPaths.CacheLocation
    if utils.isWindows:
        # Local, not Roaming!
        data_path = _writable_location(args, QStandardPaths.CacheLocation)
        path = os.path.join(data_path, 'cache')
    else:
        path = _writable_location(typ)

    _create(path)
    _locations[_Location.cache] = path


def cache():
    return _locations[_Location.cache]


def _create(path):
    """Create the `path` directory.

    From the XDG basedir spec:
        If, when attempting to write a file, the destination directory is
        non-existent an attempt should be made to create it with permission
        0755. If the destination directory exists already the permissions
        should not be changed.
    """
    os.makedirs(path, 0o755, exist_ok=True)


def _init_dirs(args=None):
    if utils.isLinux:
        _ensureXdgVariables()

    _initCacheDir(args)
    _initConfigDir(args)
    _initDataDir(args)


def init(args):
    """Initialize all standard directories."""
    global APPNAME
    if hasattr(args, "name") and args.name is not None:
        APPNAME = args.name

    _init_dirs(args)
    log.init.debug("Configuration directory: {}".format(config()))
    log.init.debug("Data directory: {}".format(data()))
    log.init.debug("Cache directory: {}".format(cache()))
