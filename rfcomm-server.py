#!/usr/bin/env python3
"""
A simple Python script to receive messages from a client over
Bluetooth using PyBluez (with Python 2).
"""
from __future__ import absolute_import, print_function, unicode_literals
from bluetooth.bluez import PORT_ANY, BluetoothSocket, RFCOMM, advertise_service, SERIAL_PORT_CLASS, SERIAL_PORT_PROFILE


from optparse import OptionParser, make_option
import os
import sys
import uuid
import dbus
import dbus.service
import dbus.mainloop.glib
try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject


class Profile(dbus.service.Object):
    fd = -1

    @dbus.service.method("org.bluez.Profile1",
                         in_signature="", out_signature="")
    def Release(self):
        print("Release")
        mainloop.quit()

    @dbus.service.method("org.bluez.Profile1",
                         in_signature="", out_signature="")
    def Cancel(self):
        print("Cancel")

    @dbus.service.method("org.bluez.Profile1",
                         in_signature="oha{sv}", out_signature="")
    def NewConnection(self, path, fd, properties):
        self.fd = fd.take()
        print("NewConnection(%s, %d)" % (path, self.fd))
        for key in properties.keys():
            if key == "Version" or key == "Features":
                print("  %s = 0x%04x" % (key, properties[key]))
            else:
                print("  %s = %s" % (key, properties[key]))

    @dbus.service.method("org.bluez.Profile1",
                         in_signature="o", out_signature="")
    def RequestDisconnection(self, path):
        print("RequestDisconnection(%s)" % (path))

        if (self.fd > 0):
            os.close(self.fd)
            self.fd = -1


dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

bus = dbus.SystemBus()

manager = dbus.Interface(bus.get_object("org.bluez",
                                        "/org/bluez"), "org.bluez.ProfileManager1")

option_list = [
    make_option("-u", "--uuid", action="store",
                type="string", dest="uuid",
                default=None),
    make_option("-p", "--path", action="store",
                type="string", dest="path",
                default="/foo/bar/profile"),
    make_option("-n", "--name", action="store",
                type="string", dest="name",
                default=None),
    make_option("-s", "--server",
                action="store_const",
                const="server", dest="role"),
    make_option("-c", "--client",
                action="store_const",
                const="client", dest="role"),
    make_option("-a", "--auto-connect",
                action="store_true",
                dest="auto_connect", default=False),
    make_option("-P", "--PSM", action="store",
                type="int", dest="psm",
                default=None),
    make_option("-C", "--channel", action="store",
                type="int", dest="channel",
                default=None),
    make_option("-r", "--record", action="store",
                type="string", dest="record",
                default=None),
    make_option("-S", "--service", action="store",
                type="string", dest="service",
                default=None),
]

parser = OptionParser(option_list=option_list)

(options, args) = parser.parse_args()

profile = Profile(bus, options.path)

mainloop = GObject.MainLoop()

opts = {
    "AutoConnect": options.auto_connect,
}

if (options.name):
    opts["Name"] = options.name

if (options.role):
    opts["Role"] = options.role

if (options.psm is not None):
    opts["PSM"] = dbus.UInt16(options.psm)

if (options.channel is not None):
    opts["Channel"] = dbus.UInt16(options.channel)

if (options.record):
    opts["ServiceRecord"] = options.record

if (options.service):
    opts["Service"] = options.service

if not options.uuid:
    options.uuid = str(uuid.uuid4())

manager.RegisterProfile(options.path, options.uuid, opts)

serverMACAddress = '3C:A0:67:5C:CE:67'

server_sock = BluetoothSocket(RFCOMM)
server_sock.bind(("", PORT_ANY))
server_sock.listen(1)

port = server_sock.getsockname()[1]

service_id = "94f39d29-7d6d-437d-973b-fba39e49d4ee"

advertise_service(server_sock, "SampleServer",
                  service_id=service_id,
                  service_classes=[service_id, SERIAL_PORT_CLASS],
                  profiles=[SERIAL_PORT_PROFILE],
                  #                   protocols = [ OBEX_UUID ]
                  )

print("Waiting for connection on RFCOMM channel %d" % port)

client_sock, client_info = server_sock.accept()
print("Accepted connection from ", client_info)

try:
    while True:
        data = client_sock.recv(1024)
        if len(data) == 0:
            break
        print("received [%s]" % data)
except IOError:
    pass

print("disconnected")

client_sock.close()
server_sock.close()
print("all done")
