"""
Listen to some available signals from NetworkManager
"""

import dbus.mainloop.glib; dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
from gi.repository import GObject
import NetworkManager

d_args = ('sender', 'destination', 'interface', 'member', 'path')
d_args = dict([(x + '_keyword', 'd_' + x) for x in d_args])

def main():
    NetworkManager.NetworkManager.connect_to_signal('CheckPermissions', display_sig, **d_args)
    NetworkManager.NetworkManager.connect_to_signal('StateChanged', display_sig, **d_args)
    NetworkManager.NetworkManager.connect_to_signal('PropertiesChanged', display_sig, **d_args)
    NetworkManager.NetworkManager.connect_to_signal('DeviceAdded', display_sig, **d_args)
    NetworkManager.NetworkManager.connect_to_signal('DeviceRemoved', display_sig, **d_args)

    print("Waiting for signals")
    print("-------------------")

    loop = GObject.MainLoop()
    loop.run()

def display_sig(*args, **kwargs):
    print("Received signal: %s.%s" % (kwargs['d_interface'], kwargs['d_member']))
    print("Sender:          (%s)%s" % (kwargs['d_sender'], kwargs['d_path']))
    print("Arguments:       (%s)" % ", ".join([str(x) for x in args]))
    print("-------------------")

if __name__ == '__main__':
    main()
