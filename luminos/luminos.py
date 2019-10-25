import sys
import dbus.mainloop.glib
from luminos.utils import utils


def main():
    # Enable glib main loop support
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    dbus.mainloop.glib.threads_init()
    parser = utils.get_argparser()
    argv = sys.argv[1:]
    args = parser.parse_args(argv)

    from luminos.utils import earlyinit
    earlyinit.early_init(args)

    import luminos.Application as app
    return app.run(args)
