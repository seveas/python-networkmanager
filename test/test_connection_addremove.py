from test import *

class ConnectionAddRemoveTest(TestCase):

    def test_activate(self):
        active = NetworkManager.NetworkManager.ActiveConnections[0]
        ap     = active.SpecificObject
        conn   = active.Connection
        dev    = active.Devices[0]

        NetworkManager.NetworkManager.DeactivateConnection(active)
        self.waitForDisconnection()
        NetworkManager.NetworkManager.ActivateConnection(conn, dev, ap)
        self.waitForConnection()

    def test_delete_addactivate(self):
        active = NetworkManager.NetworkManager.ActiveConnections[0]
        ap     = active.SpecificObject
        conn   = active.Connection
        dev    = active.Devices[0]
        settings = conn.GetSettings()
        typ = settings['connection']['type']
        if 'security' in settings[typ]:
            key2 = settings[typ]['security']
            settings[key2].update(conn.GetSecrets(key2)[key2])

        conn.Delete()
        self.waitForDisconnection()
        conn, active = NetworkManager.NetworkManager.AddAndActivateConnection(settings, dev, ap)
        self.assertIsInstance(conn, NetworkManager.Connection)
        self.assertIsInstance(active, NetworkManager.ActiveConnection)
        self.waitForConnection()

    def test_delete_add_activate(self):
        active = NetworkManager.NetworkManager.ActiveConnections[0]
        ap     = active.SpecificObject
        conn   = active.Connection
        dev    = active.Devices[0]
        settings = conn.GetSettings()
        typ = settings['connection']['type']
        if 'security' in settings[typ]:
            key2 = settings[typ]['security']
            settings[key2].update(conn.GetSecrets(key2)[key2])

        conn.Delete()
        self.waitForDisconnection()
        conn = NetworkManager.Settings.AddConnection(settings)
        self.assertIsInstance(conn, NetworkManager.Connection)
        NetworkManager.NetworkManager.ActivateConnection(conn, dev, ap)
        self.waitForConnection()

if __name__ == '__main__':
    unittest.main()
