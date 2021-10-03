from unittest.mock import Mock
import pytest
from luminos.utils import standarddir
from luminos.utils.config import Configuration


@pytest.fixture
def testfile(tmpdir, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmpdir))
    standarddir._init_dirs()
    tmpfile = tmpdir / 'luminos' / 'test.yml'
    tmpfile.write('name: test')

    return tmpfile


class TestConfig:
    def test_load_config(self, testfile):
        config = Configuration(testfile)
        val = config.get('name')
        assert val == "test"

    def test_nested_config(self, testfile):
        config = Configuration(testfile)
        config.set("plugins.nested.enabled", False)
        val: bool = config.get("plugins.nested.enabled")
        assert val is not None and not val

    def test_change_signal(self, testfile):
        config = Configuration(testfile)
        handler = Mock()
        config.changed.connect(handler)
        key = "plugins.nested.enabled"
        config.set(key, False)
        handler.assert_called_once_with(key, False)
