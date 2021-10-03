import sys

from PyQt5.QtCore import QT_VERSION_STR as QT_V_STR, QT_VERSION as QT_V, qVersion

HAS_PYTHON_3_5_OR_ABOVE = sys.version_info.major > 2 and sys.version_info.minor >= 5
HAS_PYTHON_3_6 = sys.version_info.major > 2 and sys.version_info.minor > 5
COMPILED_QT_VERSION = QT_V
COMPILED_QT_VERSION_STR = QT_V_STR
QT_VERSION = qVersion()


def qt_version(qversion=None, qt_version_str=None):
    """Get a Qt version string based on the runtime/compiled versions."""
    if qversion is None:
        qversion = QT_VERSION
    if qt_version_str is None:
        qt_version_str = COMPILED_QT_VERSION_STR
    if qversion != qt_version_str:
        return '{} (compiled {})'.format(qversion, qt_version_str)
    else:
        return qversion
