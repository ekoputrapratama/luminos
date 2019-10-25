import operator
import typing  # noqa

import pkg_resources
from PyQt5.QtCore import qVersion, QT_VERSION_STR, PYQT_VERSION_STR
from PyQt5.QtWidgets import QApplication

MAXVALS = {
    'int': 2 ** 31 - 1,
    'int64': 2 ** 63 - 1,
}

MINVALS = {
    'int': -(2 ** 31),
    'int64': -(2 ** 63),
}


def version_check(version: str, exact: bool = False, compiled: bool = True) -> bool:
    """Check if the Qt runtime version is the version supplied or newer.

    Args:
        version: The version to check against.
        exact: if given, check with == instead of >=
        compiled: Set to False to not check the compiled version.
    """
    if compiled and exact:
        raise ValueError("Can't use compiled=True with exact=True!")

    parsed = pkg_resources.parse_version(version)
    op = operator.eq if exact else operator.ge
    result = op(pkg_resources.parse_version(qVersion()), parsed)
    if compiled and result:
        # qVersion() ==/>= parsed, now check if QT_VERSION_STR ==/>= parsed.
        result = op(pkg_resources.parse_version(QT_VERSION_STR), parsed)
    if compiled and result:
        # FInally, check PYQT_VERSION_STR as well.
        result = op(pkg_resources.parse_version(PYQT_VERSION_STR), parsed)
    return result


def qenum_key(base, value, add_base=False, klass=None):
    """Convert a Qt Enum value to its key as a string.

    Args:
        base: The object the enum is in, e.g. QFrame.
        value: The value to get.
        add_base: Whether the base should be added to the printed name.
        klass: The enum class the value belongs to.
               If None, the class will be auto-guessed.

    Return:
        The key associated with the value as a string if it could be found.
        The original value as a string if not.
    """
    if klass is None:
        klass = value.__class__
        if klass == int:
            raise TypeError("Can't guess enum class of an int!")

    try:
        idx = base.staticMetaObject.indexOfEnumerator(klass.__name__)
        ret = base.staticMetaObject.enumerator(idx).valueToKey(value)
    except AttributeError:
        ret = None

    if ret is None:
        for name, obj in vars(base).items():
            if isinstance(obj, klass) and obj == value:
                ret = name
                break
        else:
            ret = '0x{:04x}'.format(int(value))

    if add_base and hasattr(base, '__name__'):
        return '.'.join([base.__name__, ret])
    else:
        return ret


def qflags_key(base, value, add_base=False, klass=None):
    """Convert a Qt QFlags value to its keys as string.

    Note: Passing a combined value (such as Qt.AlignCenter) will get the names
    for the individual bits (e.g. Qt.AlignVCenter | Qt.AlignHCenter). FIXME

    https://github.com/qutebrowser/qutebrowser/issues/42

    Args:
        base: The object the flags are in, e.g. QtCore.Qt
        value: The value to get.
        add_base: Whether the base should be added to the printed names.
        klass: The flags class the value belongs to.
               If None, the class will be auto-guessed.

    Return:
        The keys associated with the flags as a '|' separated string if they
        could be found. Hex values as a string if not.
    """
    if klass is None:
        # We have to store klass here because it will be lost when iterating
        # over the bits.
        klass = value.__class__
        if klass == int:
            raise TypeError("Can't guess enum class of an int!")

    if not value:
        return qenum_key(base, value, add_base, klass)

    bits = []
    names = []
    mask = 0x01
    value = int(value)
    while mask <= value:
        if value & mask:
            bits.append(mask)
        mask <<= 1
    for bit in bits:
        # We have to re-convert to an enum type here or we'll sometimes get an
        # empty string back.
        names.append(qenum_key(base, klass(bit), add_base))
    return '|'.join(names)


def is_single_process():
    """Check whether QtWebEngine is running in single-process mode."""
    args = QApplication.instance().arguments()
    return '--single-process' in args


def check_overflow(arg: int, ctype: str, fatal: bool = True) -> int:
    """Check if the given argument is in bounds for the given type.

    Args:
        arg: The argument to check
        ctype: The C/Qt type to check as a string.
        fatal: Whether to raise exceptions (True) or truncate values (False)

    Return
        The truncated argument if fatal=False
        The original argument if it's in bounds.
    """
    maxval = MAXVALS[ctype]
    minval = MINVALS[ctype]
    if arg > maxval:
        if fatal:
            raise OverflowError(arg)
        return maxval
    elif arg < minval:
        if fatal:
            raise OverflowError(arg)
        return minval
    else:
        return arg
