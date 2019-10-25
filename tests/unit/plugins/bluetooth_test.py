import pytest
from luminos.plugins.bluetooth import (Bluetooth)

instance = None


@pytest.fixture
def bluetooth():
    global instance
    if instance is None:
        instance = Bluetooth()

    return instance


class TestBluetooth:
    def test_discover_devices(self, bluetooth):

        devices = bluetooth.discoverDevices(None)

        assert devices is not None
