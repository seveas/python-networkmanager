from test import *

class ConnectionTest(TestCase):
    def test_settings(self):
        for connection in NetworkManager.Settings.ListConnections():
            settings = connection.GetSettings()
            self.assertIn(settings['connection']['type'], settings)

            secrets = connection.GetSecrets()
            for key in settings:
                self.assertIn(key, secrets)

            if 'ipv4' in settings:
                for address, prefix, gateway in settings['ipv4']['addresses']:
                    self.assertIsIpAddress(address)
                    self.assertIsIpAddress(gateway)
            if 'ipv6' in settings:
                for address, prefix, gateway in settings['ipv6']['addresses']:
                    self.assertIsIpAddress(address)
                    self.assertIsIpAddress(gateway)

    def test_update(self):
        active = [x.Connection for x in NetworkManager.NetworkManager.ActiveConnections]
        for connection in NetworkManager.Settings.Connections:
            if connection in active:
                continue
            settings = connection.GetSettings()
            connection.Update(settings)
            # FIXME: this causes assertion failures in n-m, which cause the dbus call to hang
            #settings['connection']['timestamp'] -= 1
            #connection.UpdateUnsaved(settings)
            #self.assertTrue(connection.Unsaved)
            #print("Saving")
            #connection.Save()
            #print("Saved")
            #self.assertFalse(connection.Unsaved)
            break

    def test_secrets(self):
        active = [x.Connection for x in NetworkManager.NetworkManager.ActiveConnections]
        key = '802-11-wireless-security' 
        for connection in NetworkManager.Settings.Connections:
            if connection in active:
                continue
            settings = connection.GetSettings()
            if key not in settings:
                continue
            secrets = connection.GetSecrets()
            if not secrets[key]:
                continue
            settings[key].update(secrets[key])

            connection.ClearSecrets()
            secrets = connection.GetSecrets()
            self.assertEqual(secrets[key], {})

            connection.Update(settings)
            secrets = connection.GetSecrets()
            self.assertNotEqual(secrets[key], {})
            break

if __name__ == '__main__':
    unittest.main()
