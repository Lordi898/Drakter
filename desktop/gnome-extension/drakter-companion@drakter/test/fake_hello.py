# Caller-check probe for client.js: calls Hello(token) from this python process and
# prints OK or the D-Bus error name. client.js copies it to <ROOT>/fake/hands/helper/main.py
# so that its command line looks like the hands helper's.
# usage: /usr/bin/python3 -I <path> <token>
import sys

from gi.repository import Gio, GLib

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
try:
    bus.call_sync("org.drakter.Companion", "/org/drakter/Companion", "org.drakter.Companion1", "Hello",
                  GLib.Variant("(s)", (sys.argv[1],)), None, Gio.DBusCallFlags.NONE, 5000, None)
    print("OK", flush=True)
except GLib.Error as e:
    print(Gio.DBusError.get_remote_error(e) or e.message, flush=True)
