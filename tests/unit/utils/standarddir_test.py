import pytest

from luminos.utils import standarddir

APPNAME = "luminos_test"


class TestStandardDir:

    """Tests for standarddir."""

    @pytest.mark.parametrize('func, varname', [
        (standarddir.data, 'XDG_DATA_HOME'),
        (standarddir.config, 'XDG_CONFIG_HOME'),
        (lambda: standarddir.config(), 'XDG_CONFIG_HOME'),
        (standarddir.cache, 'XDG_CACHE_HOME')
    ])
    @pytest.mark.linux
    def test_linux_explicit(self, monkeypatch, tmpdir, func, varname):
        """Test dirs with XDG environment variables explicitly set.

        Args:
            func: The function to test.
            varname: The environment variable which should be set.
        """
        monkeypatch.setattr(standarddir, 'APPNAME', APPNAME)
        monkeypatch.setenv(varname, str(tmpdir))
        standarddir._init_dirs()
        assert func() == str(tmpdir / APPNAME)
