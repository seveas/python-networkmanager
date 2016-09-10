from test import *

class ActiveConnectionTest(TestCase):
    def test_properties(self):
        for conn in NetworkManager.NetworkManager.ActiveConnections:
            self.assertIsInstance(conn.Connection, NetworkManager.Connection)
            for device in conn.Devices:
                self.assertIsInstance(device, NetworkManager.Device)
            if conn.Connection.GetSettings()['connection']['type'] == '802-11-wireless':
                self.assertIsInstance(conn.SpecificObject, NetworkManager.AccessPoint)
            if conn.Vpn:
                self.assertIsInstance(conn, NetworkManager.VPNConnection)
                self.assertIsInstance(conn.Banner, six.text_type)
                self.assertIsInstance(conn.SpecificObject, NetworkManager.ActiveConnection)
            self.assertTrue(conn.State == NetworkManager.NM_ACTIVE_CONNECTION_STATE_ACTIVATED)
            self.assertIsInstance(conn.Ip4Config, NetworkManager.IP4Config)
            self.assertIsInstance(conn.Ip6Config, (NetworkManager.IP6Config, type(None)))
            self.assertIsInstance(conn.Dhcp4Config, (NetworkManager.DHCP4Config, type(None)))
            self.assertIsInstance(conn.Dhcp6Config, (NetworkManager.DHCP6Config, type(None)))
            if conn.Master != None:
                self.assertIsInstance(conn.Master, NetworkManager.Device)
                self.assertEqual(conn.Master, conn.SpecificObject.Devices[0])

if __name__ == '__main__':
    unittest.main()
