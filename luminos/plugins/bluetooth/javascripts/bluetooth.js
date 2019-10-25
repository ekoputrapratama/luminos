

document.addEventListener('ready', () => {
  console.log("ready")
  const devices = {}
  BLE.startDiscovery({
    acceptAllDevices: true,
    filters: ['fb59e6d4-f6bc-11e9-802a-5aa538984bd8']
  })
  let connected = false
  BLE.deviceDiscovered.connect((device) => {
    if (!devices[device.alias]) {
      console.log('device discovered', device)
      devices[device.alias] = device
    }
    if (!connected) {
      connected = true
      devices[device.alias].deviceConnected.connect(() => {
        console.log('device connected')
      })
      devices[device.alias].deviceDisconnected.connect(() => {
        console.log("device disconnected")
      })
      devices[device.alias].connectDevice()
    }
  });
  setInterval(() => {
    console.log('devices', BLE.devices)
  }, 2000)

  class Bluetooth {
    get devices() {
      return BLE.devices
    }

    startDiscovery(uuids) {
      BLE.startDiscovery(uuids)
    }

    requestDevice(options) {
      return new Promise((resolve, reject) => {
        BLE.requestDevices(options, resolve)
      }).then(devices => devices[0])
    }
  }
  navigator.blueetooth = new Bluetooth()

})
