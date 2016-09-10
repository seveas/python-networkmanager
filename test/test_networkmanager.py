from test import *

class NetworkManagerTest(TestCase):
    def test_properties(self):
        self.assertIsInstance(NetworkManager.NetworkManager.NetworkingEnabled, bool)
        self.assertIsInstance(NetworkManager.NetworkManager.Metered, int)
        self.assertIsInstance(NetworkManager.NetworkManager.Version, six.string_types)
        self.assertIsInstance(NetworkManager.NetworkManager.ActiveConnections, list)
        for conn in NetworkManager.NetworkManager.ActiveConnections:
            self.assertIsInstance(conn, NetworkManager.ActiveConnection)
        self.assertIsInstance(NetworkManager.NetworkManager.Devices, list)
        for dev in NetworkManager.NetworkManager.Devices:
            self.assertIsInstance(dev, NetworkManager.Device)
        self.assertIsInstance(NetworkManager.NetworkManager.PrimaryConnection, NetworkManager.ActiveConnection)

    @unittest.skipUnless(have_permission('sleep-wake'), "Not allowed to make networkmanager sleep")
    def test_sleep(self):
        NetworkManager.NetworkManager.Sleep(True)
        self.assertRaisesDBus('AlreadyAsleepOrAwake', NetworkManager.NetworkManager.Sleep, True)
        NetworkManager.NetworkManager.Sleep(False)
        self.assertRaisesDBus('AlreadyAsleepOrAwake', NetworkManager.NetworkManager.Sleep, False)
        self.waitForConnection()

    def test_enable(self):
        NetworkManager.NetworkManager.Enable(False)
        self.assertRaisesDBus('AlreadyEnabledOrDisabled', NetworkManager.NetworkManager.Enable, False)
        NetworkManager.NetworkManager.Enable(True)
        self.assertRaisesDBus('AlreadyEnabledOrDisabled', NetworkManager.NetworkManager.Enable, True)
        self.waitForConnection()

    @unittest.skipUnless(os.getuid() == 0, "Must be root to modify logging")
    def test_logging(self):
        level1, domains = NetworkManager.NetworkManager.GetLogging()
        self.assertIn(level1, ['ERR', 'WARN', 'INFO', 'DEBUG', 'TRACE'])
        self.assertIn('PLATFORM', domains)
        NetworkManager.NetworkManager.SetLogging("KEEP", "PLATFORM:DEBUG")
        level2, domains = NetworkManager.NetworkManager.GetLogging()
        self.assertEqual(level1, level2)
        self.assertIn('PLATFORM:DEBUG', domains)
        self.assertIn('CORE', domains)
        NetworkManager.NetworkManager.SetLogging("KEEP", "PLATFORM:" + level1)
        level2, domains = NetworkManager.NetworkManager.GetLogging()
        self.assertIn('PLATFORM', domains)
        self.assertNotIn('PLATFORM:DEBUG', domains)

    def test_permissions(self):
        permissions = NetworkManager.NetworkManager.GetPermissions()
        self.assertIsInstance(permissions, dict)
        for key in permissions:
            self.assertTrue(key.startswith('org.freedesktop.NetworkManager.'))
            self.assertIn(permissions[key], ('yes', 'no', 'auth'))

    def test_devices(self):
        dev1 = NetworkManager.NetworkManager.GetDevices()
        dev2 = NetworkManager.NetworkManager.GetAllDevices()
        for dev in dev1:
            self.assertIsInstance(dev, NetworkManager.Device)
            self.assertIsStrictSubclass(dev.__class__, NetworkManager.Device)
            self.assertIn(dev, dev2)
        dev = NetworkManager.NetworkManager.GetDeviceByIpIface(dev1[0].IpInterface)
        self.assertEqual(dev, dev1[0])

if __name__ == '__main__':
    unittest.main()
