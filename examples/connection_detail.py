"""
Display detailed information about currently active connections.
"""
import NetworkManager

c = NetworkManager.const

for conn in NetworkManager.NetworkManager.ActiveConnections:
    settings = conn.Connection.GetSettings()

    for s in list(settings.keys()):
        if 'data' in settings[s]:
            settings[s + '-data'] = settings[s].pop('data')

    secrets = conn.Connection.GetSecrets()
    for key in secrets:
        settings[key].update(secrets[key])

    devices = ""
    if conn.Devices:
        devices = " (on %s)" % ", ".join([x.Interface for x in conn.Devices])
    print("Active connection: %s%s" % (settings['connection']['id'], devices))
    size = max([max([len(y) for y in list(x.keys()) + ['']]) for x in settings.values()])
    format = "      %%-%ds %%s" % (size + 5)
    for key, val in sorted(settings.items()):
        print("   %s" % key)
        for name, value in val.items():
            print(format % (name, value))
    for dev in conn.Devices:
        print("Device: %s" % dev.Interface)
        print("   Type             %s" % c('device_type', dev.DeviceType))
        # print("   IPv4 address     %s" % socket.inet_ntoa(struct.pack('L', dev.Ip4Address)))
        if hasattr(dev, 'HwAddress'):
            print("   MAC address      %s" % dev.HwAddress)
        print("   IPv4 config")
        print("      Addresses")
        for addr in dev.Ip4Config.Addresses:
            print("         %s/%d -> %s" % tuple(addr))
        print("      Routes")
        for route in dev.Ip4Config.Routes:
            print("         %s/%d -> %s (%d)" % tuple(route))
        print("      Nameservers")
        for ns in dev.Ip4Config.Nameservers:
            print("         %s" % ns)
