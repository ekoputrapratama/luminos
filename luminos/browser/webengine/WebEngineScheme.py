"""QtWebEngine specific luminos://* and custom uri handlers and glue code."""
import os
import mimetypes

from PyQt5.QtCore import QBuffer, QIODevice, QUrl
from PyQt5.QtWebEngineCore import QWebEngineUrlSchemeHandler, QWebEngineUrlRequestJob

try:
    from PyQt5.QtWebEngineCore import QWebEngineUrlScheme  # type: ignore
except ImportError:
    # Added in Qt 5.12
    QWebEngineUrlScheme = None

from luminos.browser import Scheme
from luminos.utils import qtutils, log


class LSchemeHandler(QWebEngineUrlSchemeHandler):
    schemes: dict = None
    """Handle requests on luminos:// and user defined scheme in QtWebEngine."""

    def install(self, profile, schemes):
        self.schemes = schemes
        """Install the handler for luminos:// URLs on the given profile."""
        if QWebEngineUrlScheme is not None:
            assert QWebEngineUrlScheme.schemeByName(b"luminos").name()

        profile.installUrlSchemeHandler(b"luminos", self)

        for scheme in schemes.keys():
            if QWebEngineUrlScheme.schemeByName(scheme.encode("ascii")).name():
                profile.installUrlSchemeHandler(scheme.encode("ascii"), self)

        if qtutils.version_check("5.11", compiled=False) and not qtutils.version_check(
            "5.12", compiled=False
        ):
            # WORKAROUND for https://bugreports.qt.io/browse/QTBUG-63378
            profile.installUrlSchemeHandler(b"chrome-error", self)
            profile.installUrlSchemeHandler(b"chrome-extension", self)

    def _check_initiator(self, job):
        """Check whether the initiator of the job should be allowed.

        Only the browser itself or luminos:// pages should access any of those
        URLs. The request interceptor further locks down luminos://settings/set.

        Args:
            job: QWebEngineUrlRequestJob

        Return:
            True if the initiator is allowed, False if it was blocked.
        """
        try:
            initiator = job.initiator()
            request_url = job.requestUrl()
        except AttributeError:
            # Added in Qt 5.11
            return True

        # https://codereview.qt-project.org/#/c/234849/
        is_opaque = initiator == QUrl("null")
        target = request_url.scheme(), request_url.host()

        if is_opaque and not qtutils.version_check("5.12"):
            # WORKAROUND for https://bugreports.qt.io/browse/QTBUG-70421
            # When we don't register the luminos:// scheme, all requests are
            # flagged as opaque.
            return True

        if (
            target == ("luminos", "testdata") and is_opaque and qtutils.version_check("5.12")
        ):
            # Allow requests to qute://testdata, as this is needed in Qt 5.12
            # for all tests to work properly. No qute://testdata handler is
            # installed outside of tests.
            return True

        if initiator.isValid() and initiator.scheme() != "luminos" and initiator.scheme() not in self.schemes.keys():
            log.webview.warning(
                "Blocking malicious request from {} to {}".format(
                    initiator.toDisplayString(), request_url.toDisplayString()
                )
            )
            job.fail(QWebEngineUrlRequestJob.RequestDenied)
            return False

        return True

    def requestStarted(self, job: QWebEngineUrlRequestJob):
        """Handle a request for all scheme.

        This method must be reimplemented by all custom URL scheme handlers.
        The request is asynchronous and does not need to be handled right away.

        Args:
            job: QWebEngineUrlRequestJob
        """
        url: QUrl = job.requestUrl()

        if url.scheme() in ["chrome-error", "chrome-extension"]:
            # WORKAROUND for https://bugreports.qt.io/browse/QTBUG-63378
            job.fail(QWebEngineUrlRequestJob.UrlInvalid)
            return

        # if not self._check_initiator(job):
        #     return

        if job.requestMethod() != b"GET":
            job.fail(QWebEngineUrlRequestJob.RequestDenied)
            return

        log.webview.debug("Got request for {}".format(url.toDisplayString()))
        if url.scheme() == "luminos":
            try:
                mimetype, data = Scheme.data_for_url(url)
            except Scheme.Error as e:
                errors = {
                    Scheme.NotFoundError: QWebEngineUrlRequestJob.UrlNotFound,
                    Scheme.UrlInvalidError: QWebEngineUrlRequestJob.UrlInvalid,
                    Scheme.RequestDeniedError: QWebEngineUrlRequestJob.RequestDenied,
                    Scheme.SchemeOSError: QWebEngineUrlRequestJob.UrlNotFound,
                    Scheme.Error: QWebEngineUrlRequestJob.RequestFailed,
                }
                exctype = type(e)
                log.webview.error("{} while handling luminos://* URL".format(exctype.__name__))
                job.fail(errors[exctype])
            except Scheme.Redirect as e:
                qtutils.ensure_valid(e.url)
                job.redirect(e.url)
            else:
                log.webview.debug("Returning {} data".format(mimetype))

                # We can't just use the QBuffer constructor taking a QByteArray,
                # because that somehow segfaults...
                # https://www.riverbankcomputing.com/pipermail/pyqt/2016-September/038075.html
                buf = QBuffer(parent=self)
                buf.open(QIODevice.WriteOnly)
                buf.write(data)
                buf.seek(0)
                buf.close()
                job.reply(mimetype.encode("ascii"), buf)
        else:
            """
            If it's not our internal scheme then this probably user defined scheme
            """

            try:
                mimetype, data = Scheme.data_for_custom_scheme(url)
            except Scheme.NotFoundError:
                log.webview.debug("handling custom uri scheme for : {}".format(url.toDisplayString()))
                """
                If it's throw error it can mean that user doesn't add their own handler,
                we will try to handle it ourselves here.
                """
                scheme = url.scheme()

                if self.schemes is None or not scheme in self.schemes.keys():
                    job.fail(QWebEngineUrlRequestJob.UrlNotFound)
                    return

                base_path = self.schemes[scheme]
                path = os.path.join(base_path, url.host(), url.path()[1:])

                if not os.path.exists(path):
                    job.fail(QWebEngineUrlRequestJob.UrlNotFound)
                    return

                try:
                    with open(path, 'rb') as file:

                        content_type = mimetypes.guess_type(path)
                        buff = QBuffer(parent=self)
                        buff.open(QIODevice.WriteOnly)
                        buff.write(file.read())
                        buff.seek(0)
                        buff.close()

                        job.reply(content_type[0].encode(), buff)
                except Exception as e:
                    raise e
            else:
                log.webview.debug("Returning {} data".format(mimetype))

                # We can't just use the QBuffer constructor taking a QByteArray,
                # because that somehow segfaults...
                # https://www.riverbankcomputing.com/pipermail/pyqt/2016-September/038075.html
                buf = QBuffer(parent=self)
                buf.open(QIODevice.WriteOnly)
                buf.write(data)
                buf.seek(0)
                buf.close()
                job.reply(mimetype.encode("ascii"), buf)
