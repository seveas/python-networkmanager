"""
Show and monitor available access points
"""
from gi.repository import GObject
import dbus.mainloop.glib
import NetworkManager

# Cache the ssids, as the SSid property will be unavailable when an AP
# disappears
ssids = {}

def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    # Listen for added and removed access points
    for dev in NetworkManager.Device.all():
        if dev.DeviceType == NetworkManager.NM_DEVICE_TYPE_WIFI:
            dev.OnAccessPointAdded(ap_added)
            dev.OnAccessPointRemoved(ap_removed)
    for ap in NetworkManager.AccessPoint.all():
        try:
            ssids[ap.object_path] = ap.Ssid
            print("* %-30s %s %sMHz %s%%" % (ap.Ssid, ap.HwAddress, ap.Frequency, ap.Strength))
            ap.OnPropertiesChanged(ap_propchange)
        except NetworkManager.ObjectVanished:
            pass
    GObject.MainLoop().run()

def ap_added(dev, interface, signal, access_point):
    ssids[access_point.object_path] = access_point.Ssid
    print("+ %-30s %s %sMHz %s%%" % (access_point.Ssid, access_point.HwAddress, access_point.Frequency, access_point.Strength))
    access_point.OnPropertiesChanged(ap_propchange)

def ap_removed(dev, interface, signal, access_point):
    print("- %-30s" % ssids.pop(access_point.object_path))

def ap_propchange(ap, interface, signal, properties):
    if 'Strength' in properties:
        print("  %-30s %s %sMHz %s%%" % (ap.Ssid, ap.HwAddress, ap.Frequency, properties['Strength']))


if __name__ == '__main__':
    main()
