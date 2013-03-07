"""
I use a VPN that sits behind an SSH host, so I have to tunnel the VPN traffic
over an SSH tunnel. I wanted to do that in one commadn, this prompted me to
learn about the NetworkManager D-Bus API and now resulted in
python-networkmanager.
"""

import dbus.mainloop.glib; dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
import NetworkManager
import socket
import subprocess
import sys

VPN_NAME   = 'MyVpn'
SSH_HOST   = 'my.ssh.bastion.host.com'
VPN_HOST   = 'my.internal.vpn.host.com:1194'
LOCALPORT  = 1195
SSH        = '/usr/bin/ssh'

# Try connecting to LOCALPORT to see if the tunnel is alive
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(3)
try:
    sock.connect(('localhost', LOCALPORT))
except socket.error:
    # Set up the SSH tunnel if it isn't
    print("Connecting to " + SSH_HOST)
    if subprocess.call([SSH, '-L%s:%s' % (LOCALPORT, VPN_HOST), '-f', '-n', '-N', SSH_HOST]) != 0:
        print("SSH to %s failed" % SSH_HOST)
        sys.exit(1)

for conn in NetworkManager.Settings.ListConnections():
    settings = conn.GetSettings()

    if settings['connection']['type'] == 'vpn' and settings['connection']['id'] == VPN_NAME:
        vpn = conn
        uuid = settings['connection']['uuid']
        break
else:
    print("VPN with name %s not found" % VPN_NAME)
    sys.exit(1)

# Bail out of another vpn is active
for conn in NetworkManager.NetworkManager.ActiveConnections:
    if conn.Vpn:
        vid = conn.Connection.GetSettings()['connection']['id']
        print("The vpn %s is already active" % vid)
        sys.exit(1)

# Activate VPN
for dev in NetworkManager.NetworkManager.GetDevices():
    if dev.State == NetworkManager.NM_DEVICE_STATE_ACTIVATED and dev.Managed:
        break
else:
    print("No active, managed device found")
    sys.exit(1)

print("Activating VPN")
NetworkManager.NetworkManager.ActivateConnection(vpn, dev, "/")
