import unittest
import pytest  # noqa
import os
from os import environ

from PyQt5.QtTest import QTest  # noqa

from luminos.Application import Application
from luminos.windows.BrowserWindow import BrowserWindow

environ['LUMINOS_DEV'] = "true"


class TestWindow(unittest.TestCase):
    def setUp(self):
        """Call before every test case."""
        self.app = Application(["./luminos.py", "-d"])

    def tearDown(self):
        """Call after every test case."""
        del self.app
        # self.file.close()

    def test_creating_window(self):
        """"""
        window = BrowserWindow(self.app)
        window.deleteLater()
        window.show()
        self.assertTrue(window.isVisible(), "cannot show window.")
        window.close()

    def test_window_load_url(self):
        path = os.path.join(os.getcwd(), "data", "static")
        expectedUrl = "file://" + path + "/index.html"

        window = BrowserWindow(self.app)
        self.app.registerApp(path)
        window.loadUrl(expectedUrl)
        window.show()

        script = window.webview.page().scripts().findScript("QWebChannel API")
        self.assertIsNotNone(script)
        script = window.webview.page().scripts().findScript("Luminos Bridge")
        self.assertIsNotNone(script)

        url = window.webview.url()
        self.assertEqual(url.toDisplayString(), expectedUrl)
        window.close()
