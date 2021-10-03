
import typing

# from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QFont

from luminos.utils import config, log  # noqa

UNSET = object()


class AttributeInfo:

    """Info about a settings attribute."""

    def __init__(self, *attributes: typing.Any,
                 converter: typing.Callable = None) -> None:
        self.attributes = attributes
        if converter is None:
            self.converter = lambda val: val
        else:
            self.converter = converter


class Unset:

    """Sentinel object."""

    __slots__ = ()

    def __repr__(self) -> str:
        return '<UNSET>'


CONFIG_UNSET = Unset()


class AbstractSettings:

    """Abstract base class for settings set via QWeb(Engine)Settings."""

    _ATTRIBUTES = {}  # type: typing.Dict[str, AttributeInfo]
    _FONT_SIZES = {}  # type: typing.Dict[str, typing.Any]
    _FONT_FAMILIES = {}  # type: typing.Dict[str, typing.Any]
    _FONT_TO_QFONT = {}  # type: typing.Dict[typing.Any, QFont.StyleHint]

    def __init__(self, settings: typing.Any) -> None:
        self._settings = settings

    def setAttribute(self, name: str, value: typing.Any) -> bool:
        """Set the given QWebSettings/QWebEngineSettings attribute.

        If the value is CONFIG_UNSET, the value is reset instead.

        Return:
            True if there was a change, False otherwise.
        """
        old_value = self.testAttribute(name)
        new_value = old_value
        info = self._ATTRIBUTES[name]
        for attribute in info.attributes:
            if value is not None:
                self._settings.setAttribute(attribute, info.converter(value))
                new_value = value
            else:
                config.instance.set(name, old_value)

        return old_value != new_value

    def testAttribute(self, name: str) -> bool:
        """Get the value for the given attribute.

        If the setting resolves to a list of attributes, only the first
        attribute is tested.
        """
        info = self._ATTRIBUTES[name]
        return self._settings.testAttribute(info.attributes[0])

    def setFontSize(self, name: str, value: int) -> bool:
        """Set the given QWebSettings/QWebEngineSettings font size.

        Return:
            True if there was a change, False otherwise.
        """
        assert value is not CONFIG_UNSET  # type: ignore
        family = self._FONT_SIZES[name]
        old_value = self._settings.fontSize(family)
        new_value = old_value

        if value is not None:
            self._settings.setFontSize(family, value)
            new_value = value
        else:
            config.instance.set(name, old_value)
            new_value = config.instance.get(name)

        return old_value != new_value

    def setFontFamily(self, name: str, value: typing.Optional[str]) -> bool:
        """Set the given QWebSettings/QWebEngineSettings font family.

        With None (the default), QFont is used to get the default font for the
        family.

        Return:
            True if there was a change, False otherwise.
        """

        family = self._FONT_FAMILIES[name]
        if value is None:
            font = QFont()
            font.setStyleHint(self._FONT_TO_QFONT[family])
            value = font.defaultFamily()
            config.instance.set(name, value)

        old_value = self._settings.fontFamily(family)
        self._settings.setFontFamily(family, value)

        return value != old_value

    def setDefaultTextEncoding(self, encoding: str) -> bool:
        """Set the default text encoding to use.

        Return:
            True if there was a change, False otherwise.
        """
        assert encoding is not CONFIG_UNSET  # type: ignore
        old_value = self._settings.defaultTextEncoding()

        if encoding is not None:
            self._settings.setDefaultTextEncoding(encoding)
        else:
            config.instance.set("content.default_encoding", encoding)

        return old_value != encoding

    def _updateSetting(self, setting: str, value: typing.Any) -> bool:
        """Update the given setting/value.

        Unknown settings are ignored.

        Return:
            True if there was a change, False otherwise.
        """

        if setting in self._ATTRIBUTES:
            return self.setAttribute(setting, value)
        elif setting in self._FONT_SIZES:
            return self.setFontSize(setting, value)
        elif setting in self._FONT_FAMILIES:
            return self.setFontFamily(setting, value)
        elif setting == 'content.default_encoding':
            return self.setDefaultTextEncoding(value)

        return False

    def updateSetting(self, setting: str) -> None:
        """Update the given setting."""
        value = config.instance.get(setting)
        self._updateSetting(setting, value)

    def initSettings(self) -> None:
        """Set all supported settings correctly."""
        for setting in (list(self._ATTRIBUTES) + list(self._FONT_SIZES) + list(self._FONT_FAMILIES)):
            self.updateSetting(setting)
