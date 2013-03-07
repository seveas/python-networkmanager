"""
Activate a connection by name
"""

import NetworkManager
import sys

# Find the connection
name = sys.argv[1]
connections = NetworkManager.Settings.ListConnections()
connections = dict([(x.GetSettings()['connection']['id'], x) for x in connections])
conn = connections[name]

# Find a suitable device
ctype = conn.GetSettings()['connection']['type']
if ctype == 'vpn':
    for dev in NetworkManager.NetworkManager.GetDevices():
        if dev.State == NetworkManager.NM_DEVICE_STATE_ACTIVATED and dev.Managed:
            break
    else:
        print("No active, managed device found")
        sys.exit(1)
else:
    dtype = {
        '802-11-wireless': NetworkManager.NM_DEVICE_TYPE_WIFI,
        '802-3-ethernet': NetworkManager.NM_DEVICE_TYPE_ETHERNET,
        'gsm': NetworkManager.NM_DEVICE_TYPE_MODEM,
    }.get(ctype,ctype)
    devices = NetworkManager.NetworkManager.GetDevices()

    for dev in devices:
        if dev.DeviceType == dtype and dev.State == NetworkManager.NM_DEVICE_STATE_DISCONNECTED:
            break
    else:
        print("No suitable and available %s device found" % ctype)
        sys.exit(1)

# And connect
NetworkManager.NetworkManager.ActivateConnection(conn, dev, "/")
