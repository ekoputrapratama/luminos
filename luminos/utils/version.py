
"""Utilities to show various version information."""

import re
import sys
import glob
import enum
import os.path
import platform

import attr
import pkg_resources

import luminos
import luminos.utils.constants as constants
from luminos.utils import log, utils

from PyQt5.QtCore import PYQT_VERSION_STR, QLibraryInfo
from PyQt5.QtWidgets import QApplication
from PyQt5.QtNetwork import QSslSocket
from PyQt5.QtGui import QOpenGLVersionProfile, QOffscreenSurface, QOpenGLContext

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineProfile
except ImportError:  # pragma: no cover
    QWebEngineProfile = None  # type: ignore

try:
    from luminos.browser.webengine import WebEngineSettings
except ImportError:
    WebEngineSettings = None


@attr.s
class DistributionInfo:

    """Information about the running distribution."""

    id = attr.ib()
    parsed = attr.ib()
    version = attr.ib()
    pretty = attr.ib()


Distribution = enum.Enum(
    'Distribution', ['unknown', 'ubuntu', 'debian', 'void', 'arch',
                     'gentoo', 'fedora', 'opensuse', 'linuxmint', 'manjaro',
                     'kde'])


def distribution():
    """Get some information about the running Linux distribution.

    Returns:
        A DistributionInfo object, or None if no info could be determined.
            parsed: A Distribution enum member
            version: A Version object, or None
            pretty: Always a string (might be "Unknown")
    """
    filename = os.environ.get('LUMINOS_FAKE_OS_RELEASE', '/etc/os-release')
    info = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if (not line) or line.startswith('#'):
                    continue
                k, v = line.split("=", maxsplit=1)
                info[k] = v.strip('"')
    except (OSError, UnicodeDecodeError):
        return None

    pretty = info.get('PRETTY_NAME', None)
    if pretty in ['Linux', None]:  # Funtoo has PRETTY_NAME=Linux
        pretty = info.get('NAME', 'Unknown')

    if 'VERSION_ID' in info:
        dist_version = pkg_resources.parse_version(info['VERSION_ID'])
    else:
        dist_version = None

    dist_id = info.get('ID', None)
    id_mappings = {
        'funtoo': 'gentoo',  # does not have ID_LIKE=gentoo
        'org.kde.Platform': 'kde',
    }
    try:
        parsed = Distribution[id_mappings.get(dist_id, dist_id)]
    except KeyError:
        parsed = Distribution.unknown

    return DistributionInfo(parsed=parsed, version=dist_version, pretty=pretty,
                            id=dist_id)


def _release_info():
    """Try to gather distribution release information.

    Return:
        list of (filename, content) tuples.
    """
    blacklisted = ['ANSI_COLOR=', 'HOME_URL=', 'SUPPORT_URL=',
                   'BUG_REPORT_URL=']
    data = []
    for fn in glob.glob("/etc/*-release"):
        lines = []
        try:
            with open(fn, 'r', encoding='utf-8') as f:
                for line in f.read().strip().splitlines():
                    if not any(line.startswith(bl) for bl in blacklisted):
                        lines.append(line)

                if lines:
                    data.append((fn, '\n'.join(lines)))
        except OSError:
            log.misc.exception("Error while reading {}.".format(fn))
    return data


def _os_info():
    """Get operating system info.

    Return:
        A list of lines with version info.
    """
    lines = []
    releaseinfo = None
    if utils.is_linux:
        osver = ''
        releaseinfo = _release_info()
    elif utils.is_windows:
        osver = ', '.join(platform.win32_ver())
    elif utils.is_mac:
        release, versioninfo, machine = platform.mac_ver()
        if all(not e for e in versioninfo):
            versioninfo = ''
        else:
            versioninfo = '.'.join(versioninfo)
        osver = ', '.join([e for e in [release, versioninfo, machine] if e])
    elif utils.is_posix:
        osver = ' '.join(platform.uname())
    else:
        osver = '?'
    lines.append('OS Version: {}'.format(osver))
    if releaseinfo is not None:
        for (fn, data) in releaseinfo:
            lines += ['', '--- {} ---'.format(fn), data]
    return lines


def _backend():
    """Get the backend line with relevant information."""
    return 'QtWebEngine (Chromium {})'.format(_chromium_version())


def _chromium_version():
    """Get the Chromium version for QtWebEngine.

    This can also be checked by looking at this file with the right Qt tag:
    http://code.qt.io/cgit/qt/qtwebengine.git/tree/tools/scripts/version_resolver.py#n41

    Quick reference:

    Qt 5.7:  Chromium 49
             49.0.2623.111 (2016-03-31)
             5.7.1: Security fixes up to 54.0.2840.87 (2016-11-01)

    Qt 5.8:  Chromium 53
             53.0.2785.148 (2016-08-31)
             5.8.0: Security fixes up to 55.0.2883.75 (2016-12-01)

    Qt 5.9:  Chromium 56
    (LTS)    56.0.2924.122 (2017-01-25)
             5.9.8: Security fixes up to 72.0.3626.121 (2019-03-01)

    Qt 5.10: Chromium 61
             61.0.3163.140 (2017-09-05)
             5.10.1: Security fixes up to 64.0.3282.140 (2018-02-01)

    Qt 5.11: Chromium 65
             65.0.3325.151 (.1: .230) (2018-03-06)
             5.11.3: Security fixes up to 70.0.3538.102 (2018-11-09)

    Qt 5.12: Chromium 69
    (LTS)    69.0.3497.113 (2018-09-27)
             5.12.4: Security fixes up to 74.0.3729.157 (2019-05-14)

    Qt 5.13: Chromium 73
             73.0.3683.105 (~2019-02-28)
             5.13.0: Security fixes up to 74.0.3729.131 (2019-04-30)

    Also see https://www.chromium.org/developers/calendar
    and https://chromereleases.googleblog.com/
    """
    if WebEngineSettings is None or QWebEngineProfile is None:
        # This should never happen
        return 'unavailable'

    profile = QWebEngineProfile.defaultProfile()
    ua = profile.httpUserAgent()

    match = re.search(r' Chrome/([^ ]*) ', ua)
    if not match:
        log.misc.error("Could not get Chromium version from: {}".format(ua))
        return 'unknown'
    return match.group(1)


def version():
    """Return a string with various version information."""
    lines = ["luminos v{}".format(luminos.__version__)]

    lines.append("Backend: {}".format(_backend()))

    lines += [
        '',
        '{}: {}'.format(platform.python_implementation(),
                        platform.python_version()),
        'Qt: {}'.format(constants.qt_version()),
        'PyQt: {}'.format(PYQT_VERSION_STR),
        '',
    ]

    lines += [
        'QtNetwork SSL: {}\n'.format(QSslSocket.sslLibraryVersionString()
                                     if QSslSocket.supportsSsl() else 'no'),
    ]

    lapp = QApplication.instance()
    if lapp:
        style = lapp.style()
        lines.append('Style: {}'.format(style.metaObject().className()))

    importpath = os.path.dirname(os.path.abspath(luminos.__file__))

    lines += [
        'Platform: {}, {}'.format(platform.platform(),
                                  platform.architecture()[0]),
    ]
    dist = distribution()
    if dist is not None:
        lines += [
            'Linux distribution: {} ({})'.format(dist.pretty, dist.parsed.name)
        ]

    lines += [
        'Frozen: {}'.format(hasattr(sys, 'frozen')),
        "Imported from {}".format(importpath),
        "Using Python from {}".format(sys.executable),
        "Qt library executable path: {}, data path: {}".format(
            QLibraryInfo.location(QLibraryInfo.LibraryExecutablesPath),
            QLibraryInfo.location(QLibraryInfo.DataPath)
        )
    ]

    if not dist or dist.parsed == Distribution.unknown:
        lines += _os_info()

    return '\n'.join(lines)


def opengl_vendor():  # pragma: no cover
    """Get the OpenGL vendor used.

    This returns a string such as 'nouveau' or
    'Intel Open Source Technology Center'; or None if the vendor can't be
    determined.
    """
    assert QApplication.instance()

    override = os.environ.get('LUMINOS_FAKE_OPENGL_VENDOR')
    if override is not None:
        log.init.debug("Using override {}".format(override))
        return override

    old_context = QOpenGLContext.currentContext()
    old_surface = None if old_context is None else old_context.surface()

    surface = QOffscreenSurface()
    surface.create()

    ctx = QOpenGLContext()
    ok = ctx.create()
    if not ok:
        log.init.debug("Creating context failed!")
        return None

    ok = ctx.makeCurrent(surface)
    if not ok:
        log.init.debug("Making context current failed!")
        return None

    try:
        if ctx.isOpenGLES():
            # Can't use versionFunctions there
            return None

        vp = QOpenGLVersionProfile()
        vp.setVersion(2, 0)

        try:
            vf = ctx.versionFunctions(vp)
        except ImportError as e:
            log.init.debug("Importing version functions failed: {}".format(e))
            return None

        if vf is None:
            log.init.debug("Getting version functions failed!")
            return None

        return vf.glGetString(vf.GL_VENDOR)
    finally:
        ctx.doneCurrent()
        if old_context and old_surface:
            old_context.makeCurrent(old_surface)
