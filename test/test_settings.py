from test import *
import socket

class SettingsTest(TestCase):
    def test_connections(self):
        conn1 = NetworkManager.Settings.Connections
        conn2 = NetworkManager.Settings.ListConnections()
        self.assertIsInstance(conn1, list)
        for conn in conn1:
            self.assertIn(conn, conn2)
        for conn in conn2:
            self.assertIn(conn, conn1)
        conn = NetworkManager.Settings.GetConnectionByUuid(conn1[0].GetSettings()['connection']['uuid'])

    @unittest.skipUnless(os.getuid() == 0, "Must be root to reload connections")
    def test_reload(self):
        self.assertTrue(NetworkManager.Settings.ReloadConnections())

    @unittest.skipUnless(have_permission('settings.modify.hostname'), "don't have permission to modify the hostname")
    def test_hostname(self):
        hn = NetworkManager.Settings.Hostname
        self.assertEqual(hn, socket.gethostname())
        NetworkManager.Settings.SaveHostname(hn + '-test')
        self.assertEqual(NetworkManager.Settings.Hostname, hn + '-test')
        NetworkManager.Settings.SaveHostname(hn)
        self.assertEqual(NetworkManager.Settings.Hostname, hn)

if __name__ == '__main__':
    unittest.main()
