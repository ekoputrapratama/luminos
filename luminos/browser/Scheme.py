import os
import functools
import typing

from PyQt5.QtCore import QUrl

from luminos.utils import utils, urlutils

_HANDLERS = {}
_CUSTOM_HANDLERS = {}


class Error(Exception):

    """Exception for generic errors on a luminos:// page."""


class NotFoundError(Error):

    """Raised when the given URL was not found."""


class SchemeOSError(Error):

    """Raised when there was an OSError inside a handler."""


class UrlInvalidError(Error):

    """Raised when an invalid URL was opened."""


class RequestDeniedError(Error):

    """Raised when the request is forbidden."""


class Redirect(Exception):

    """Exception to signal a redirect should happen.

    Attributes:
        url: The URL to redirect to, as a QUrl.
    """

    def __init__(self, url):
        super().__init__(url.toDisplayString())
        self.url = url


class add_scheme_handler:

    """Decorator to register custom uri scheme handler.

    Attributes:
        _name: The 'foo' part of foo://
    """

    def __init__(self, name, isFunction: bool = True):
        self._name = name
        self._function = None
        self.isFunction = isFunction

    def __call__(self, function):
        self._function = function

        if self.isFunction:
            @functools.wraps(function)
            def func_wrapper(url: QUrl) -> typing.Any:
                """Call the underlying function."""
                return function(url)
            self.callback = func_wrapper
        else:
            @functools.wraps(function)
            def meth_wrapper(self_wrapper, url: QUrl) -> typing.Any:
                """Call the underlying function."""
                return function(self_wrapper, url)
            self.callback = meth_wrapper

        _CUSTOM_HANDLERS[self._name] = self.callback
        return self.callback

    def wrapper(self, *args, **kwargs):
        """Call the underlying function."""
        return self._function(*args, **kwargs)


class add_handler:  # noqa: N801,N806 pylint: disable=invalid-name

    """Decorator to register a luminos://* URL handler.

    Attributes:
        _name: The 'foo' part of luminos://foo
    """

    def __init__(self, name):
        self._name = name
        self._function = None

    def __call__(self, function):
        self._function = function
        _HANDLERS[self._name] = self.wrapper
        return function

    def wrapper(self, *args, **kwargs):
        """Call the underlying function."""
        return self._function(*args, **kwargs)


def data_for_custom_scheme(url: QUrl):
    """"""
    scheme = url.scheme()

    try:
        handler = _CUSTOM_HANDLERS[scheme]
    except KeyError:
        raise NotFoundError("No handler found for scheme {}".format(url.toDisplayString()))

    try:
        mimetype, data = handler(url)
    except OSError as e:
        raise SchemeOSError(e)

    assert mimetype is not None, url
    if mimetype == "text/html" and isinstance(data, str):
        # We let handlers return HTML as text
        data = data.encode("utf-8", errors="xmlcharrefreplace")

    return mimetype, data


def data_for_url(url: QUrl):
    """Get the data to show for the given URL.

    Args:
        url: The QUrl to show.

    Return:
        A (mimetype, data) tuple.
    """
    norm_url = url.adjusted(QUrl.NormalizePathSegments | QUrl.StripTrailingSlash)
    if norm_url != url:
        raise Redirect(norm_url)

    path = url.path()
    host = url.host()
    query = urlutils.query_string(url)
    # A url like "luminos:foo" is split as "scheme:path", not "scheme:host".

    if not path or not host:
        new_url = QUrl()
        new_url.setScheme("luminos")
        # When path is absent, e.g. luminos://help (with no trailing slash)
        if host:
            new_url.setHost(host)
        # When host is absent, e.g. luminos:help
        else:
            new_url.setHost(path)

        new_url.setPath("/")
        if query:
            new_url.setQuery(query)
        if new_url.host():  # path was a valid host
            raise Redirect(new_url)

    try:
        handler = _HANDLERS[host]
    except KeyError:
        raise NotFoundError("No handler found for {}".format(url.toDisplayString()))

    try:
        mimetype, data = handler(url)
    except OSError as e:
        raise SchemeOSError(e)

    assert mimetype is not None, url
    if mimetype == "text/html" and isinstance(data, str):
        # We let handlers return HTML as text
        data = data.encode("utf-8", errors="xmlcharrefreplace")

    return mimetype, data


@add_handler("javascript")
def luminosJavascript(url):
    """Handler for luminos://javascript.

    Return content of file given as query parameter.
    """
    path = url.path()[1:]
    if path:
        path = "javascript" + os.sep.join(path.split("/"))
        return "text/javascript", utils.readResourceFile(path, binary=False)
    else:
        raise UrlInvalidError("No file specified")


@add_handler("templates")
def luminosTemplates(url):
    path = url.path()[1:]

    if path:
        path = "templates" + os.sep.join(path.split("/"))
        return "text/html", utils.readResourceFile(path, binary=False)
    else:
        raise UrlInvalidError("No file specified")


@add_handler("css")
def luminosCss(url):
    path = url.path()

    if path:
        path = "css" + os.sep.join(path.split("/"))
        return "text/css", utils.readResourceFile(path, binary=False)
    else:
        raise UrlInvalidError("No file specified")


@add_handler("vendor")
def luminosVendor(url):
    url_path = url.path()[1:]
    vendorPaths = [
        "/usr/share/luminos/vendor",
        "/usr/local/share/luminos/vendor",
        os.path.expanduser("~/.local/share/luminos/vendor")
    ]

    for p in vendorPaths:
        path = os.path.join(p, url_path)
        if os.path.exists(path):
            break

    if path:
        path = os.sep.join(path.split("/"))
        mimetype = utils.getContentType(path)
        return mimetype, utils.readFile(path, binary=True)
    else:
        raise UrlInvalidError("No file specified")
