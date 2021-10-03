import dbus


class Example(dbus.service.Object):
    def __init__(self, object_path):
        dbus.service.Object.__init__(self, dbus.SystemBus(), "/io/gitlab/fisma/luminos")

    @dbus.service.method(
        dbus_interface="com.example.Sample",
        in_signature="",
        out_signature="s",
        sender_keyword="sender",
    )
    def SayHello(self, sender=None):
        return "Hello, %s!" % sender
        # -> something like 'Hello, :1.1!'
    @dbus.service.signal(dbus_interface='com.example.Sample',
                         signature='us')
    def NumberOfBottlesChanged(self, number, contents):
        print("%d bottles of %s on the wall".format())
