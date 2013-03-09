"""
Add a connection to NetworkManager. You do this by sending a dict to
AddConnection. The dict below was generated with n-m dump on an existing
connection and then anonymised
"""

import NetworkManager
import uuid

example_connection = {
     '802-11-wireless': {'mode': 'infrastructure',
                         'security': '802-11-wireless-security',
                         'ssid': 'n-m-example-connection'},
     '802-11-wireless-security': {'auth-alg': 'open', 'key-mgmt': 'wpa-eap'},
     '802-1x': {'eap': ['peap'],
                'identity': 'eap-identity-goes-here',
                'password': 'eap-password-goes-here',
                'phase2-auth': 'mschapv2'},
     'connection': {'id': 'nm-example-connection',
                    'type': '802-11-wireless',
                    'uuid': str(uuid.uuid4())},
     'ipv4': {'method': 'auto'},
     'ipv6': {'method': 'auto'}
}

NetworkManager.Settings.AddConnection(example_connection)
