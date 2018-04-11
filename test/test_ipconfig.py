from test import *

class IpConfigTest(TestCase):
    def test_configs(self):
        for device in NetworkManager.NetworkManager.Devices:
            if device.State != NetworkManager.NM_DEVICE_STATE_ACTIVATED:
                continue
            self.do_check(device)
        for connection in NetworkManager.NetworkManager.ActiveConnections:
            self.do_check(connection)

    def do_check(self, thing):
        if thing.Dhcp4Config:
            self.assertIsInstance(thing.Dhcp4Config, NetworkManager.DHCP4Config)
            self.assertIsInstance(thing.Dhcp4Config.Options, dict)
            o = thing.Dhcp4Config.Options
            self.assertIsInstance(o['domain_name_servers'], list)
            self.assertIsInstance(o['ntp_servers'], list)
            self.assertIsIpAddress(o['ip_address'])
            for key in o:
                if key.endswith('_requested'):
                    self.assertTrue(o[key])
        if thing.Dhcp6Config:
            self.assertIsInstance(thing.Dhcp6Config, NetworkManager.DHCP6Config)
            self.assertIsInstance(thing.Dhcp6Config.Options, dict)
        for c in (thing.Ip4Config, thing.Ip6Config):
            if not c:
                continue
            for addr, prefix, gateway in c.Addresses:
                self.assertIsIpAddress(addr)
                self.assertIsIpAddress(gateway)
                self.assertIsIpNetwork(addr, prefix)
            for data in c.AddressData:
                self.assertIsIpAddress(data['address'])
                self.assertIsIpNetwork(data['address'], data['prefix'])
                if 'peer' in data:
                    self.assertIsIpAddress(data['peer'])
            if c.Gateway:
                self.assertIsIpAddress(c.Gateway)
            for addr in c.Nameservers:
                self.assertIsIpAddress(addr)
            for addr in getattr(c, 'WinsServers', []):
                self.assertIsIpAddress(addr)
            for dest, prefix, next_hop, metric in c.Routes:
                self.assertIsIpNetwork(dest, prefix)
                self.assertIsIpAddress(next_hop)
                self.assertLessEqual(metric, 1000)
            for data in c.RouteData:
                self.assertIsIpNetwork(data['dest'], data['prefix'])
                if 'next-hop' in data:
                    self.assertIsIpAddress(data['next-hop'])
                self.assertLessEqual(data['metric'], 1000)

if __name__ == '__main__':
    unittest.main()
