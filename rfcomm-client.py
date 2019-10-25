#!/usr/bin/env python3
"""
A simple Python script to send messages to a sever over Bluetooth
using PyBluez (with Python 2).
"""

import sys
from bluetooth import *
import bluetooth

serverMACAddress = '3C:A0:67:5C:CE:67'

if sys.version < '3':
    input = raw_input

addr = None

if len(sys.argv) < 2:
    print("no device specified.  Searching all nearby bluetooth devices for")
    print("the SampleServer service")
else:
    addr = sys.argv[1]
    print("Searching for SampleServer on %s" % addr)

# search for the SampleServer service
uuid = "8ce255c0-200a-11e0-ac64-0800200c9a66"
service_matches = find_service(uuid=uuid, address=addr)

if len(service_matches) == 0:
    print("couldn't find the SampleServer service =(")
    sys.exit(0)

first_match = service_matches[0]
port = first_match["port"]
name = first_match["name"]
host = first_match["host"]

print("connecting to \"%s\" on %s" % (name, host))

# Create the client socket
sock = BluetoothSocket(RFCOMM)
sock.connect((host, port))

print("connected.  type stuff")
while True:
    data = input()
    if len(data) == 0:
        break
    sock.send(data)

sock.close()
