# Set this variable in your environment if you understand that
#
#    THE TESTS WILL MESS WITH YOUR COMPUTER!
#
# You will repeatedly go offline and it will attempt to add and delete
# connections, change the hostname and more nasty things.

import os
if 'NM_TESTS' not in os.environ:
    print("Cowardly refusing to run tests")
    os._exit(1)

import dbus
import ipaddress
import six
import time
import unittest

import NetworkManager

class TestCase(unittest.TestCase):
    def assertRaisesDBus(self, exception, func, *args, **kwargs):
        if '.' not in exception:
            exception = 'org.freedesktop.NetworkManager.' + exception
        with self.assertRaises(dbus.exceptions.DBusException) as cm:
            func(*args, **kwargs)
        self.assertEqual(cm.exception.get_dbus_name(), exception)

    def assertIsStrictSubclass(self, klass1, klass2):
        self.assertTrue(issubclass(klass1, klass2) and klass1 != klass2)

    def assertIsIpAddress(self, ip):
        try:
            ipaddress.ip_address(six.text_type(ip))
        except ValueError as e:
            raise self.failureException(str(e))

    def assertIsIpNetwork(self, ip, prefix):
        try:
            ipaddress.ip_network((ip, prefix), strict=False)
        except ValueError as e:
            raise self.failureException(str(e))

    def assertIsMacAddress(self, address):
        self.assertRegex(address, '^[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}$', '%s is not a mac address' % address)

    def waitForConnection(self):
        while NetworkManager.NetworkManager.State < NetworkManager.NM_STATE_CONNECTED_LOCAL:
            time.sleep(0.5)

    def waitForDisconnection(self):
        while NetworkManager.NetworkManager.State >= NetworkManager.NM_STATE_CONNECTED_LOCAL:
            time.sleep(0.5)

permissions = NetworkManager.NetworkManager.GetPermissions()
def have_permission(permission):
    permission = 'org.freedesktop.NetworkManager.' + permission
    return permissions.get(permission, None) == 'yes'

