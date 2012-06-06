"""
Display information about everything network-related that network-manager can
say something about.
"""

import NetworkManager
c = NetworkManager.const

print("%-30s %s" % ("Version:", NetworkManager.NetworkManager.Version))
print("%-30s %s" % ("Hostname:", NetworkManager.Settings.Hostname))
print("%-30s %s" % ("Can modify:", NetworkManager.Settings.CanModify))
print("%-30s %s" % ("Networking enabled:", NetworkManager.NetworkManager.NetworkingEnabled))
print("%-30s %s" % ("Wireless enabled:", NetworkManager.NetworkManager.WirelessEnabled))
print("%-30s %s" % ("Wireless hw enabled:", NetworkManager.NetworkManager.WirelessHardwareEnabled))
print("%-30s %s" % ("Wwan enabled:", NetworkManager.NetworkManager.WwanEnabled))
print("%-30s %s" % ("Wwan hw enabled:", NetworkManager.NetworkManager.WwanHardwareEnabled))
print("%-30s %s" % ("Wimax enabled:", NetworkManager.NetworkManager.WimaxEnabled))
print("%-30s %s" % ("Wimax hw enabled:", NetworkManager.NetworkManager.WimaxHardwareEnabled))
print("%-30s %s" % ("Overall state:", c('state', NetworkManager.NetworkManager.State)))

print("")

print("Permissions")
for perm, val in sorted(NetworkManager.NetworkManager.GetPermissions().items()):
    print("%-30s %s" % (perm[31:] + ':', val))

print("")

print("Available network devices")
print("%-10s %-19s %-20s %s" % ("Name", "State", "Driver", "Managed?"))
for dev in NetworkManager.NetworkManager.GetDevices():
    print("%-10s %-19s %-20s %s" % (dev.Interface, c('device_state', dev.State), dev.Driver, dev.Managed))

print("")

print("Available connections")
print("%-30s %s" % ("Name", "Type"))
for conn in NetworkManager.Settings.ListConnections():
    settings = conn.GetSettings()['connection']
    print("%-30s %s" % (settings['id'], settings['type']))

print("")

print("Active connections")
print("%-30s %-20s %-10s %s" % ("Name", "Type", "Default", "Devices"))
for conn in NetworkManager.NetworkManager.ActiveConnections:
    settings = conn.Connection.GetSettings()['connection']
    print("%-30s %-20s %-10s %s" % (settings['id'], settings['type'], conn.Default, ", ".join([x.Interface for x in conn.Devices])))
