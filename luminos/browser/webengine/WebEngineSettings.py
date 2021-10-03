import operator
import typing
from PyQt5.QtGui import QFont
from PyQt5.QtWebEngineWidgets import QWebEngineSettings, QWebEngineProfile

from luminos.browser.webengine import Spell
from luminos.utils import log, config, message, qtutils
from luminos.core.AbstractSettings import AbstractSettings, AttributeInfo as Attr


class _SettingsWrapper:

    """Expose a QWebEngineSettings interface which acts on all profiles.

    For read operations, the default profile value is always used.
    """

    def __init__(self, profile):
        self._settings: typing.List[QWebEngineSettings] = [profile.settings()]

    def setAttribute(self, attr, value):
        if value is not None:
            for settings in self._settings:
                settings.setAttribute(attr, value)

    def setFontFamily(self, attr, value):
        if value is not None:
            for settings in self._settings:
                settings.setFontFamily(attr, value)

    def setFontSize(self, attr, value):
        if value is not None:
            for settings in self._settings:
                settings.setFontSize(attr, value)

    def setDefaultTextEncoding(self, encoding: str):
        if encoding is not None:
            for settings in self._settings:
                settings.setDefaultTextEncoding(encoding)

    def testAttribute(self, *args, **kwargs):
        return self._settings[0].testAttribute(*args, **kwargs)

    def fontSize(self, *args, **kwargs):
        return self._settings[0].fontSize(*args, **kwargs)

    def fontFamily(self, *args, **kwargs):
        return self._settings[0].fontFamily(*args, **kwargs)

    def defaultTextEncoding(self, *args, **kwargs):
        return self._settings[0].defaultTextEncoding(*args, **kwargs)


class WebEngineSettings(AbstractSettings):
    """A wrapper for the config for QWebEngineSettings."""
    _ATTRIBUTES = {
        'content.xss_auditing':
            Attr(QWebEngineSettings.XSSAuditingEnabled),
        'content.images':
            Attr(QWebEngineSettings.AutoLoadImages),
        'content.javascript.enabled':
            Attr(QWebEngineSettings.JavascriptEnabled),
        'content.javascript.can_open_windows_automatically':
            Attr(QWebEngineSettings.JavascriptCanOpenWindows),
        'content.javascript.can_access_clipboard':
            Attr(QWebEngineSettings.JavascriptCanAccessClipboard),
        'content.plugins':
            Attr(QWebEngineSettings.PluginsEnabled),
        'content.hyperlink_auditing':
            Attr(QWebEngineSettings.HyperlinkAuditingEnabled),
        'content.local_content_can_access_remote_urls':
            Attr(QWebEngineSettings.LocalContentCanAccessRemoteUrls),
        'content.local_content_can_access_file_urls':
            Attr(QWebEngineSettings.LocalContentCanAccessFileUrls),
        'content.webgl':
            Attr(QWebEngineSettings.WebGLEnabled),
        'content.local_storage':
            Attr(QWebEngineSettings.LocalStorageEnabled),
        'content.desktop_capture':
            Attr(QWebEngineSettings.ScreenCaptureEnabled,
                 converter=lambda val: True if val == 'ask' else val),
        'content.accelerated_2d_canvas': Attr(QWebEngineSettings.Accelerated2dCanvasEnabled),
        # 'ask' is handled via the permission system,
        # or a hardcoded dialog on Qt < 5.10

        'input.spatial_navigation':
            Attr(QWebEngineSettings.SpatialNavigationEnabled),
        'input.links_included_in_focus_chain':
            Attr(QWebEngineSettings.LinksIncludedInFocusChain),
        'scrolling.smooth':
            Attr(QWebEngineSettings.ScrollAnimatorEnabled),
    }

    _FONT_SIZES = {
        'fonts.web.size.minimum':
            QWebEngineSettings.MinimumFontSize,
        'fonts.web.size.minimum_logical':
            QWebEngineSettings.MinimumLogicalFontSize,
        'fonts.web.size.default':
            QWebEngineSettings.DefaultFontSize,
        'fonts.web.size.default_fixed':
            QWebEngineSettings.DefaultFixedFontSize,
    }

    _FONT_FAMILIES = {
        'fonts.web.family.standard': QWebEngineSettings.StandardFont,
        'fonts.web.family.fixed': QWebEngineSettings.FixedFont,
        'fonts.web.family.serif': QWebEngineSettings.SerifFont,
        'fonts.web.family.sans_serif': QWebEngineSettings.SansSerifFont,
        'fonts.web.family.cursive': QWebEngineSettings.CursiveFont,
        'fonts.web.family.fantasy': QWebEngineSettings.FantasyFont,
    }

    # Mapping from WebEngineSettings::initDefaults in
    # qtwebengine/src/core/web_engine_settings.cpp
    _FONT_TO_QFONT = {
        QWebEngineSettings.StandardFont: QFont.Serif,
        QWebEngineSettings.FixedFont: QFont.Monospace,
        QWebEngineSettings.SerifFont: QFont.Serif,
        QWebEngineSettings.SansSerifFont: QFont.SansSerif,
        QWebEngineSettings.CursiveFont: QFont.Cursive,
        QWebEngineSettings.FantasyFont: QFont.Fantasy,
    }

    def __init__(self, settings):
        super().__init__(settings)
        # Attributes which don't exist in all Qt versions.
        new_attributes = {
            # Qt >= 5.6
            'content.fullscreen_support':
                ('FullScreenSupportEnabled', None),
            # Qt 5.8
            'content.print_element_backgrounds':
                ('PrintElementBackgrounds', None),
            # Qt 5.10
            'content.javascript.can_activate_window':
                ('AllowWindowActivationFromJavaScript', None),
            # Qt 5.11
            'content.autoplay':
                ('PlaybackRequiresUserGesture', operator.not_),
            # Qt 5.12
            'content.dns_prefetch':
                ('DnsPrefetchEnabled', None),
            # Qt 5.13
            'content.pdfviewer':
                ('PdfViewerEnabled', None)
        }
        for name, (attribute, converter) in new_attributes.items():
            try:
                value = getattr(QWebEngineSettings, attribute)
            except AttributeError:
                continue

            self._ATTRIBUTES[name] = Attr(value, converter=converter)


class ProfileSetter:

    """Helper to set various settings on a profile."""

    def __init__(self, profile: QWebEngineProfile):
        self._profile = profile

    def init_profile(self):
        """Initialize settings on the given profile."""
        self.set_http_headers()
        self.set_http_cache_size()

        settings = self._profile.settings()
        settings.setAttribute(
            QWebEngineSettings.FullScreenSupportEnabled, True)
        try:
            settings.setAttribute(
                QWebEngineSettings.FocusOnNavigationEnabled, False)
        except AttributeError:
            # Added in Qt 5.8
            pass

        if qtutils.version_check('5.8'):
            self.set_dictionary_language()

    def set_http_headers(self):
        """Set the user agent and accept-language for the given profile.

        We override those per request in the URL interceptor (to allow for
        per-domain values), but this one still gets used for things like
        window.navigator.userAgent/.languages in JS.
        """
        default_value = self._profile.httpUserAgent()
        userAgent = config.instance.get("content.headers.user_agent")
        if userAgent is None:
            config.instance.set("content.headers.user_agent", default_value)
            userAgent = default_value

        self._profile.setHttpUserAgent(userAgent)

        default_value = self._profile.httpAcceptLanguage()
        accept_language = config.instance.get("content.headers.accept_language")

        if accept_language is None:
            config.instance.set("content.headers.accept_language", default_value)
            accept_language = default_value

        if accept_language is not None:
            self._profile.setHttpAcceptLanguage(accept_language)

    def set_http_cache_size(self):
        """Initialize the HTTP cache size for the given profile."""
        defaultValue = self._profile.httpCacheMaximumSize()
        size = config.instance.get("content.cache.size")

        if size is None:
            config.instance.set("content.cache.size", defaultValue)
            size = defaultValue
        else:
            size = qtutils.check_overflow(size, 'int', fatal=False)

        # 0: automatically managed by QtWebEngine
        self._profile.setHttpCacheMaximumSize(size)

    def set_persistent_cookie_policy(self):
        """Set the HTTP Cookie size for the given profile."""
        assert not self._profile.isOffTheRecord()

        defaultValue = self._profile.persistentCookiesPolicy()
        allowCookies = config.instance.get("content.cookies.store")
        if allowCookies is None:
            if defaultValue == QWebEngineProfile.NoPersistentCookies:
                allowCookies = False
            else:
                allowCookies = True

            config.instance.set("content.cookies.store", allowCookies)

        if allowCookies:
            value = QWebEngineProfile.AllowPersistentCookies
        else:
            value = QWebEngineProfile.NoPersistentCookies

        self._profile.setPersistentCookiesPolicy(value)

    def set_dictionary_language(self, warn=True):
        """Load the given dictionaries."""
        filenames = []
        languages = config.instance.get("spellcheck.languages")

        for code in languages or []:
            local_filename = Spell.local_filename(code)
            if not local_filename:
                if warn:
                    message.warning("Language {} is not installed - see "
                                    "scripts/dictcli.py in luminos "
                                    "sources".format(code))
                continue

            filenames.append(local_filename)

        log.config.debug("Found dicts: {}".format(filenames))
        self._profile.setSpellCheckLanguages(filenames)
        self._profile.setSpellCheckEnabled(bool(filenames))
