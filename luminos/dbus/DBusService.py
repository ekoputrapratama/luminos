import sys

from luminos.utils import log

from gi.repository import Gio, GLib


class DBusService:
    def __init__(self, bus_name, interface_name, path, bus_type):
        self._bus = Gio.bus_get_sync(bus_type)
        if bus_name:
            Gio.bus_own_name(bus_type, bus_name, Gio.BusNameOwnerFlags.NONE, None, None, None)
