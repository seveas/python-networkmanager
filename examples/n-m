#!/usr/bin/python
#
# Command-line tool to interact with NetworkManager. With this tool, you can
# inspect various configuration items and (de-)activate connections.
#
# (C) 2011-2016 Dennis Kaarsemaker
# License: zlib

from __future__ import print_function

usage = """%prog [options] action [arguments]

Actions:
  list       - List all defined and active connections
  activate   - Activate a connection
  deactivate - Deactivate a connection
  offline    - Deactivate all connections
  enable     - Enable specific connection types
  disable    - Disable specific connection types
  info       - Information about a connection"""

import datetime
from dbus.exceptions import DBusException
import NetworkManager
import optparse
import socket
import struct
import sys

PY3 = sys.version_info[0] >= 3

def main():
    p = optparse.OptionParser(usage=usage)
    opts, args = p.parse_args()

    if not args:
        p.print_help()
        sys.exit(1)

    if args[0] == 'list':
        list_()

    elif args[0] == 'offline':
        offline()

    elif args[0] == 'visible':
        visible()

    elif len(args) < 2:
        p.print_help()
        sys.exit(1)

    elif args[0] == 'activate':
        activate(args[1:])

    elif args[0] == 'deactivate':
        deactivate(args[1:])

    elif args[0] == 'enable':
        enable(args[1:])

    elif args[0] == 'disable':
        disable(args[1:])

    elif args[0] == 'info':
        info(args[1:])

    elif args[0] == 'dump':
        dump(args[1:])

    else:
        p.print_help()
        sys.exit(1)

def list_():
    active = [x.Connection.GetSettings()['connection']['id']
              for x in NetworkManager.NetworkManager.ActiveConnections]
    connections = [(x.GetSettings()['connection']['id'], x.GetSettings()['connection']['type'])
                   for x in NetworkManager.Settings.ListConnections()]
    fmt = "%%s %%-%ds    %%s" % max([len(x[0]) for x in connections])
    for conn in sorted(connections):
        prefix = '* ' if conn[0] in active else '  '
        print(fmt % (prefix, conn[0], conn[1]))

def activate(names):
    connections = NetworkManager.Settings.ListConnections()
    connections = dict([(x.GetSettings()['connection']['id'], x) for x in connections])

    if not NetworkManager.NetworkManager.NetworkingEnabled:
        NetworkManager.NetworkManager.Enable(True)
    for n in names:
        if n not in connections:
            print("No such connection: %s" % n, file=sys.stderr)
            sys.exit(1)

        print("Activating connection '%s'" % n)
        conn = connections[n]
        ctype = conn.GetSettings()['connection']['type']
        if ctype == 'vpn':
            for dev in NetworkManager.NetworkManager.GetDevices():
                if dev.State == NetworkManager.NM_DEVICE_STATE_ACTIVATED and dev.Managed:
                    break
            else:
                print("No active, managed device found", file=sys.stderr)
                sys.exit(1)
        else:
            dtype = {
                '802-11-wireless': 'wlan',
                'gsm': 'wwan',
            }
            if dtype in connection_types:
                enable(dtype)
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
                print("No suitable and available %s device found" % ctype, file=sys.stderr)
                sys.exit(1)

        NetworkManager.NetworkManager.ActivateConnection(conn, dev, "/")

def deactivate(names):
    active = NetworkManager.NetworkManager.ActiveConnections
    active = dict([(x.Connection.GetSettings()['connection']['id'], x) for x in active])

    for n in names:
        if n not in active:
            print("No such connection: %s" % n, file=sys.stderr)
            sys.exit(1)

        print("Deactivating connection '%s'" % n)
        NetworkManager.NetworkManager.DeactivateConnection(active[n])

def offline():
    try:
        NetworkManager.NetworkManager.Enable(False)
    except DBusException as e:
        if e.get_dbus_name() != 'org.freedesktop.NetworkManager.AlreadyEnabledOrDisabled':
            raise

connection_types = ['wireless','wwan','wimax']
def enable(names):
    for n in names:
        if n not in connection_types:
            print("No such connection type: %s" % n, file=sys.stderr)
            sys.exit(1)
        setattr(NetworkManager.NetworkManager, n.title() + 'Enabled', True)

def disable(names):
    for n in names:
        if n not in connection_types:
            print("No such connection type: %s" % n, file=sys.stderr)
            sys.exit(1)
        setattr(NetworkManager.NetworkManager, n.title() + 'Enabled', False)

def info(names):
    connections = [x.GetSettings() for x in NetworkManager.Settings.ListConnections()]
    connections = dict([(x['connection']['id'], x) for x in connections])

    for n in names:
        if not PY3:
            n = n.decode('utf-8')
        if n not in connections:
            print("No such connection: %s" % n, file=sys.stderr)
            return

        line = "Info about '%s'" % n
        print(line + "\n" + '=' * len(line))
        conn = connections[n]
        print("Type:", conn['connection']['type'])
        print("Connect automatically:", ["No","Yes"][conn['connection'].get('autoconnect', True)])
        if 'timestamp' in conn['connection']:
            print("Last connected on:", str(datetime.datetime.fromtimestamp(conn['connection']['timestamp'])))
        else:
            print("Never connected")
        print("IPv4 settings (%s)" % conn['ipv4']['method'])
        print("  Address(es):", ', '.join([x[0] for x in conn['ipv4']['addresses']]) or '(Automatic)')
        print("  DNS servers:",  ', '.join(conn['ipv4']['dns']) or '(Automatic)')
        print("  Routes:", ", ".join(["%s/%d -> %s" % x[:3] for x in conn['ipv4']['routes']]))
        print("  Can be default route:", ["Yes","No"][conn['ipv4'].get('never-default', False)])

        if conn['connection']['type'] == '802-3-ethernet':
            print("Physical link")
            print("  MAC address:", conn['802-3-ethernet'].get('mac-address', '(Automatic)'))
        elif conn['connection']['type'] == '802-11-wireless':
            print("Wireless link")
            print("  MAC address:", conn['802-11-wireless'].get('mac-address', '(Automatic)'))
            print("  SSID:", conn['802-11-wireless']['ssid'])
            if 'security' in conn['802-11-wireless']:
                print("  Wireless security:", conn[conn['802-11-wireless']['security']]['key-mgmt'])
        elif conn['connection']['type'] == 'vpn':
            print("VPN")
            print("  Type:", conn['vpn']['service-type'].rsplit('.',1)[-1])
            print("  Remote:", conn['vpn']['data']['remote'])

def dump(names):
    from pprint import pprint
    connections = {}
    for conn in NetworkManager.Settings.ListConnections():
        settings = conn.GetSettings()
        secrets = conn.GetSecrets()
        for key in secrets:
            settings[key].update(secrets[key])
        connections[settings['connection']['id']] = settings

    for n in names:
        if n not in connections:
            print("No such connection: %s" % n, file=sys.stderr)

        pprint(connections[n])

def visible():
    for device in NetworkManager.NetworkManager.GetDevices():
        if device.DeviceType != NetworkManager.NM_DEVICE_TYPE_WIFI:
            continue
        print("Visible on %s" % device.Udi[device.Udi.rfind('/')+1:])
        device = device.SpecificDevice()
        active = device.ActiveAccessPoint
        aps = device.GetAccessPoints()
        for ap in aps:
            prefix = '* ' if ap.object_path == active.object_path else '  '
            print("%s %s" % (prefix, ap.Ssid))

if __name__ == '__main__':
    main()
