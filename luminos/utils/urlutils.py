import re
import ipaddress

from PyQt5.QtCore import QUrl, QUrlQuery

from luminos.utils import log

WEBENGINE_SCHEMES = [
    "about",
    "data",
    "file",
    "ftp",
    "http",
    "https",
    "javascript",
    "ws",
    "wss",
]


def _has_explicit_scheme(url: QUrl):
    """Check if a url has an explicit scheme given.

    Args:
        url: The URL as QUrl.
    """
    # Note that generic URI syntax actually would allow a second colon
    # after the scheme delimiter. Since we don't know of any URIs
    # using this and want to support e.g. searching for scoped C++
    # symbols, we treat this as not a URI anyways.
    return (
        url.isValid() and
        url.scheme() and
        (url.host() or url.path()) and
        " " not in url.path() and
        not url.path().startswith(":")
    )


def is_special_url(url):
    """Return True if url is an about:... or other special URL.

    Args:
        url: The URL as QUrl.
    """
    if not url.isValid():
        return False
    special_schemes = ("about", "luminos", "file")
    return url.scheme() in special_schemes


def is_url(urlstr: str):
    """Check if url seems to be a valid URL.

    Args:
        urlstr: The URL as string.

    Return:
        True if it is a valid URL, False otherwise.
    """
    # autosearch = config.val.url.auto_search

    log.url.debug(
        "Checking if {!r} is a URL (autosearch={}).".format(urlstr)
    )

    urlstr = urlstr.strip()
    qurl = QUrl(urlstr)
    qurl_userinput = qurl_from_user_input(urlstr)

    if not qurl_userinput.isValid():
        # This will also catch URLs containing spaces.
        return False

    if _has_explicit_scheme(qurl):
        # URLs with explicit schemes are always URLs
        log.url.debug("Url contains explicit scheme")
        url = True
    elif qurl_userinput.host() in ["localhost", "127.0.0.1", "::1"]:
        log.url.debug("Url is localhost.")
        url = True
    elif is_special_url(qurl):
        # Special URLs are always URLs, even with autosearch=never
        log.url.debug("Url is a special URL.")
        url = True
    log.url.debug("url = {}".format(url))
    return url


def qurl_from_user_input(urlstr):
    """Get a QUrl based on a user input. Additionally handles IPv6 addresses.

    QUrl.fromUserInput handles something like '::1' as a file URL instead of an
    IPv6, so we first try to handle it as a valid IPv6, and if that fails we
    use QUrl.fromUserInput.

    WORKAROUND - https://bugreports.qt.io/browse/QTBUG-41089
    FIXME - Maybe https://codereview.qt-project.org/#/c/93851/ has a better way
            to solve this?
    https://github.com/qutebrowser/qutebrowser/issues/109

    Args:
        urlstr: The URL as string.

    Return:
        The converted QUrl.
    """
    # First we try very liberally to separate something like an IPv6 from the
    # rest (e.g. path info or parameters)
    match = re.fullmatch(r"\[?([0-9a-fA-F:.]+)\]?(.*)", urlstr.strip())
    if match:
        ipstr, rest = match.groups()
    else:
        ipstr = urlstr.strip()
        rest = ""
    # Then we try to parse it as an IPv6, and if we fail use
    # QUrl.fromUserInput.
    try:
        ipaddress.IPv6Address(ipstr)
    except ipaddress.AddressValueError:
        return QUrl.fromUserInput(urlstr)
    else:
        return QUrl("http://[{}]{}".format(ipstr, rest))


def query_string(qurl):
    """Get a query string for the given URL.

    This is a WORKAROUND for:
    https://www.riverbankcomputing.com/pipermail/pyqt/2017-November/039702.html
    """
    try:
        return qurl.query()
    except AttributeError:  # pragma: no cover
        return QUrlQuery(qurl).query()
