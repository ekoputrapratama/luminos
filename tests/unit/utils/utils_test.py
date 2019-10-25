import sys
import pytest

import luminos
from luminos.utils import utils, standarddir


@pytest.fixture(params=[True, False])
def freezer(request, monkeypatch):
    if request.param and not getattr(sys, 'frozen', False):
        monkeypatch.setattr(sys, 'frozen', True, raising=False)
        monkeypatch.setattr(sys, 'executable', luminos.__file__)
    elif not request.param and getattr(sys, 'frozen', False):
        # Want to test unfrozen tests, but we are frozen
        pytest.skip("Can't run with sys.frozen = True!")


@pytest.fixture
def testfile(tmpdir, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmpdir))
    standarddir._init_dirs()
    tmpfile = tmpdir / 'luminos' / 'testfile'
    tmpfile.write('Hello World!')

    return tmpfile


@pytest.mark.usefixtures('freezer')
class TestReadFile:

    """Test read_file."""

    def test_readfile(self, testfile):
        """Read a test file."""
        content = utils.readResourceFile('testfile')
        assert content.splitlines()[0] == "Hello World!"

    # @pytest.mark.parametrize('filename', ['javascript/scroll.js',
    #                                       'html/error.html'])
    # def test_read_cached_file(self, mocker, filename):
    #     utils.preloadResources()
    #     m = mocker.patch('pkg_resources.resource_string')
    #     utils.readFile(filename)s
    #     m.assert_not_called()

    def test_readfile_binary(self, testfile):
        """Read a test file in binary mode."""
        content = utils.readResourceFile('testfile',
                                         binary=True)
        assert content.splitlines()[0] == b"Hello World!"
