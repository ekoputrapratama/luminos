import luminos
from gi.repository import Gio
import sys
import fnmatch
import os.path
import argparse
import glob
import re
import mimetypes
import gi

gi.require_version("Gio", "2.0")

from luminos.utils import log, standarddir  # noqa

_resource_cache = {}

isMac = sys.platform.startswith('darwin')
isLinux = sys.platform.startswith('linux')
isWindows = sys.platform.startswith('win')
isPosix = os.name == 'posix'

arguments = [
    ["-D", "--datadir", "Data directory for resources and data file.", None],
    ["-C", "--configdir", "Configuration directory.", None],
    ["-v", "--version", "Show version and quit.", "store_true"],
    ["-i", "--enable-inspector", "Enable web inspector.", "store_true"],
    ["-d", "--debug", "Show debug output.", "store_true"]
]

_content_types = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.png': 'image/png',
    '.webp': 'image/webp',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif'
}


def get_argparser():
    """Get the argparse parser."""
    parser = argparse.ArgumentParser(prog='luminos',
                                     description=luminos.__description__)
    global arguments
    for s, l, desc, act in arguments:
        parser.add_argument(s, l, help=desc, action=act)

    parser.add_argument('--nocolor', help="Turn off colored logging.",
                        action='store_false', dest='color')
    parser.add_argument('--force-color', help="Force colored logging",
                        action='store_true')
    # URLs will actually be in command
    parser.add_argument('url', nargs='*', help="Application directory to open on startup "
                        "(empty to load default application).")
    return parser


def cleanArgs(argv: list):
    def filter_arguments(arg: str):
        global arguments
        satisfied = False
        for argument in arguments:
            if arg in argument:
                satisfied = True
                break

        return satisfied

    return list(filter(filter_arguments, argv))


def findFiles(pattern, path, regex=False):
    matches = []
    for root, dirs, files in os.walk(path):
        for basename in files:
            if not regex:
                if fnmatch.fnmatch(basename, pattern):
                    filename = os.path.join(root, basename)
                    matches.append(filename)
            else:
                if len(re.findall(pattern, basename)) > 0:
                    filename = os.path.join(root, basename)
                    matches.append(filename)

    return matches


userBinPath = os.path.expanduser("~/.local/bin")
binDirs = [
    "/usr/bin",
    "/usr/local/bin",
    userBinPath
]


def ensureUserBinDirInPath():
    paths = os.getenv("PATH")
    if paths.find(userBinPath) < 0:
        # try to write this thing in user .bashrc
        bashrc_path = os.path.expanduser("~/.bashrc")

        with open(bashrc_path, "a+") as f:
            f.write('\nexport PATH="{}:$PATH"\n'.format(userBinPath))


def isInstalled() -> bool:
    """Check if the application is installed"""
    from luminos.utils import standarddir

    installed = False
    for p in binDirs:
        if standarddir.install().startswith(p):
            if standarddir.install().startswith(userBinPath):
                ensureUserBinDirInPath()

            installed = True
            break
    return installed


def preloadResources():
    """Load resource files into the cache."""
    for subdir, pattern in [('static', '*.html'), ('static', '*.js'), ('static', '*.css')]:
        path = getResourcePath(subdir)
        for full_path in glob.glob(os.path.join(path, pattern)):
            sub_path = '/'.join([subdir, os.path.basename(full_path)])
            _resource_cache[sub_path] = readResourceFile(sub_path)


def readResourceFile(filename, binary=False):
    """Get the contents of a file contained with luminos.

    Args:
        filename: The filename to open as string.
        binary: Whether to return a binary string.
                If False, the data is UTF-8-decoded.

    Return:
        The file contents as string.
    """

    if not binary and filename in _resource_cache:
        return _resource_cache[filename]

    fn = os.path.join(standarddir.data(), filename)

    return readFile(fn, binary)


def readFile(path, binary=False):
    assert os.path.isabs(path)

    if binary:
        with open(path, "rb") as f:
            return f.read()
    else:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


def readGResource(path: str):
    resource = Gio.Resource.load("/usr/share/gnome-shell/gnome-shell-theme.gresource")
    inputStream = resource.open_stream(path, Gio.ResourceLookupFlags.NONE)
    dataStream = Gio.DataInputStream.new(inputStream)

    return dataStream.read_upto("\0", 1)


def getResourcePath(name: str):
    """Get the absolute path to internal resource file"""
    base = standarddir.data()
    return os.path.join(base, name)


def getContentType(path: str) -> str:
    filename, extension = os.path.splitext(path)

    try:
        content_type = _content_types[extension]
    except KeyError:
        content_type = mimetypes.guess_type(path)[0]

    return content_type
