import unittest
from luminos.windows.Window import Window


class WidgetTestCase(unittest.TestCase):
    def setUp(self):
        self.widget = Window(None)

    def tearDown(self):
        # self.widget.dispose()
        self.widget = None

    def testDefaultSize(self):
        assert self.widget.size() == (50, 50), "incorrect default size"

    def testResize(self):
        self.widget.resize(100, 150)
        assert self.widget.size() == (100, 150), "wrong size after resize"
