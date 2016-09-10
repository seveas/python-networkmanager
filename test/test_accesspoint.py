from test import *

class AccessPointTest(TestCase):
    def test_accesspoints(self):
        for dev in NetworkManager.NetworkManager.Devices:
            if isinstance(dev, NetworkManager.Wireless):
                for ap in dev.AccessPoints:
                    self.assertIsInstance(ap.Flags, int)
                    # Frequencies from https://en.wikipedia.org/wiki/List_of_WLAN_channels
                    f = ap.Frequency
                    if not (
                        (f > 2400 and f < 2500) or
                        (f > 3650 and f < 3700) or
                        (f > 4900 and f < 6000)):
                        self.fail("Frequency is not a valid wifi frequency")
                    self.assertIsMacAddress(ap.HwAddress)
                    self.assertIsInstance(ap.LastSeen, int)
                    self.assertIsInstance(ap.MaxBitrate, int)
                    self.assertIsInstance(ap.WpaFlags, int)
                    self.assertIsInstance(ap.RsnFlags, int)
                    self.assertLess(ap.Strength, 100)
                    self.assertIsInstance(ap.Ssid, six.text_type)
                    self.assertIn(ap.Mode, (NetworkManager.NM_802_11_MODE_ADHOC, NetworkManager.NM_802_11_MODE_INFRA, NetworkManager.NM_802_11_MODE_AP))

if __name__ == '__main__':
    unittest.main()
