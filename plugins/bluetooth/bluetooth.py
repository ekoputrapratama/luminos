from . import gatt
from luminos.core.Bridge import BridgeObject, Bridge, Variant

# dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)


class ServiceBridge(BridgeObject):
    serviceResolved = Bridge.signal()
    _service = None

    def __init__(self, service, name='service', *args, **kwargs):
        super().__init__(name=name, *args, **kwargs)
        self._service = service


class DeviceBridge(BridgeObject):
    noop_signal = Bridge.signal()
    _services = {}
    _cached_services = {}
    servicesResolved = Bridge.signal()
    aliasChanged = Bridge.signal(str)
    macAddressChanged = Bridge.signal(str)
    deviceConnected = Bridge.signal()
    deviceDisconnected = Bridge.signal()

    def __init__(self, device, name='device', *args, **kwargs):
        super().__init__(name=name, *args, **kwargs)
        print(f"initialize device bridge : {device.alias()} {device.mac_address}")
        self.device = device
        device.servicesResolved.connect(self._servicesResolved)
        device.connected.connect(self._connected)
        device.disconnected.connect(self._disconnected)
        self.aliasChanged.emit(str(self.device.alias()))
        self.macAddressChanged.emit(str(self.device.mac_address))

    def _connected(self):
        self.deviceConnected.emit()

    def _disconnected(self):
        self.deviceDisconnected.emit()

    def _servicesResolved(self):

        for s in self.device.services:
            self._services[s.uuid] = s
            self._cached_services = ServiceBridge(s)

        self.servicesResolved.emit()

    @Bridge.property(str, notify=macAddressChanged)
    def macAddress(self):
        return str(self.device.mac_address)

    @Bridge.property(str, notify=aliasChanged)
    def alias(self):
        return str(self.device.alias())

    @Bridge.method()
    def connectDevice(self):
        self.device.connect()

    @Bridge.method()
    def disconnectDevice(self):

        self.device.disconnect()

    @Bridge.method(str, result=Variant)
    def getServiceByUUID(self, uuid: str):
        if not hasattr(self._cached_services, uuid):
            self._cached_services[uuid] = self._services[uuid]

        return self._cached_services[uuid]

    @Bridge.property(Variant, notify=servicesResolved)
    def services(self):
        results = []
        for key, s in self._services.items():
            results.append(ServiceBridge(s))

        return results


class BluetoothGatt(BridgeObject):
    discovering: bool = False
    connected = Bridge.signal()
    deviceManager = gatt.DeviceManager(adapter_name='hci0')
    noop_signal = Bridge.signal(Variant)
    _devices = {}
    _cached_devices = {}
    deviceDiscovered = Bridge.signal(Variant)

    def __init__(self, name='bluetooth', *args, **kwargs):
        super().__init__(name=name, *args, **kwargs)
        self.deviceManager.deviceDiscovered.connect(self._deviceDiscovered)

    def _deviceDiscovered(self, device):
        print("device discovered", str(device.alias()))
        alias = str(device.alias())
        self._devices[alias] = device

        if not hasattr(self._cached_devices, alias):
            d = DeviceBridge(device)
            self._cached_devices[alias] = d
        else:
            d = self._cached_devices[alias]

        self.deviceDiscovered.emit(d)
        self.noop_signal.emit(d)

    @Bridge.method(Variant, result=Variant)
    def requestDevices(self, options):
        """"""
        print("requestDevices called with arguments", options)
        self.deviceManager.update_devices()

        results = []
        if hasattr(options, "acceptAllDevices"):
            print("accepAllDevices result")
            for d in self.deviceManager._devices:
                results.append({'alias': d.alias(), 'macAddress': d.mac_address})

        return results

    @Bridge.method(Variant)
    def startDiscovery(self, options):
        """[summary]
        """
        uuids = []
        print("start discovery", options)
        if hasattr(options, "filters") and options.filters is list:
            uuids = options.filters
        try:
            self.discovering = True
            self.deviceManager.start_discovery(uuids)
            self.deviceManager.run()
        except gatt.NotReady:
            print("Please check your bluetooth if it's already turned on")

    @Bridge.method(str, result=Variant)
    def getDeviceByAlias(self, alias: str):
        print("getting device by alias", alias)

        if hasattr(self._cached_devices, alias):
            return self._cached_devices[alias]

        device = DeviceBridge(self._devices[alias])
        self._cached_devices[alias] = device
        return device

    @Bridge.property(Variant, notify=noop_signal)
    def devices(self):
        ""
        results = []
        for key, d in self._devices.items():
            results.append(DeviceBridge(d))

        return results


instance = None


def beforeLoad(channel, page):
    """[summary]
    """
    global instance
    print("register Gatt object")
    channel.registerObject("BLE", instance)


def activate():
    """[summary]
    """
    print("plugin activated")
    global instance
    if instance is None:
        instance = BluetoothGatt()


def deactivate():
    """[summary]
    """
