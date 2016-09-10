from test import *

class DeviceTest(TestCase):
    def test_devices(self):
        for device in NetworkManager.NetworkManager.Devices:
            self.assertIsStrictSubclass(type(device), NetworkManager.Device)
            if device.Dhcp4Config:
                self.assertIsInstance(device.Dhcp4Config, NetworkManager.DHCP4Config)
            if device.Dhcp6Config:
                self.assertIsInstance(device.Dhcp6Config, NetworkManager.DHCP6Config)
            if device.Ip4Config:
                self.assertIsInstance(device.Ip4Config, NetworkManager.IP4Config)
            if device.Ip6Config:
                self.assertIsInstance(device.Ip6Config, NetworkManager.IP6Config)
            if device.Ip4Address:
                self.assertIsIpAddress(device.Ip4Address)
            if hasattr(device, 'HwAddress') and device.HwAddress:
                self.assertIsMacAddress(device.HwAddress)
            if hasattr(device, 'PermHwAddress') and device.PermHwAddress:
                self.assertIsMacAddress(device.PermHwAddress)
        if device.DeviceType == NetworkManager.NM_DEVICE_TYPE_WIFI:
            for ap in device.AccessPoints:
                self.assertIsInstance(ap, NetworkManager.AccessPoint)
            device.RequestScan({})
        elif device.DeviceType == NetworkManager.NM_DEVICE_TYPE_ETHERNET:
            self.assertIn(device.Carrier, (True, False))
        elif device.DeviceType == NetworkManager.NM_DEVICE_TYPE_GENERIC:
            self.assertIsInstance(device.TypeDescription, six.text_type)
        elif device.DeviceType == NetworkManager.NM_DEVICE_TYPE_TUN:
            if device.Owner != -1:
                import pwd
                pwd.getpwuid(device.Owner)
        else:
            self.fail("I don't know how to test %s devices" % type(device).__name__)

if __name__ == '__main__':
    unittest.main()
