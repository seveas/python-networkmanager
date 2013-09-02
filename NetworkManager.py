# NetworkManager - a library to make interacting with the NetworkManager daemon
# easier.
#
# (C)2011-2013 Dennis Kaarsemaker
# License: GPL3+

import dbus
import os
import socket
import struct
import sys

PY3 = sys.version_info >= (3,0)
if PY3:
    basestring = str
    unicode = str
elif not hasattr(__builtins__, 'bytes'):
    bytes = lambda x, y=None: chr(x[0]) if x else x

try:
    debuglevel = int(os.environ['NM_DEBUG'])
    def debug(msg, data):
        sys.stderr.write(msg + "\n")
        sys.stderr.write(repr(data)+"\n")
except:
    debug = lambda *args: None

class NMDbusInterface(object):
    bus = dbus.SystemBus()
    dbus_service = 'org.freedesktop.NetworkManager'
    object_path = None

    def __init__(self, object_path=None):
        if isinstance(object_path, NMDbusInterface):
            object_path = object_path.object_path
        self.object_path = self.object_path or object_path
        self.proxy = self.bus.get_object(self.dbus_service, self.object_path)
        self.interface = dbus.Interface(self.proxy, self.interface_name)

        properties = []
        try:
            properties = self.proxy.GetAll(self.interface_name,
                                           dbus_interface='org.freedesktop.DBus.Properties')
        except dbus.exceptions.DBusException as e:
            if e.get_dbus_name() != 'org.freedesktop.DBus.Error.UnknownMethod':
                raise
        for p in properties:
            p = str(p)
            if not hasattr(self.__class__, p):
                setattr(self.__class__, p, self._make_property(p))

    def _make_property(self, name):
        def get(self):
            data = self.proxy.Get(self.interface_name, name, dbus_interface='org.freedesktop.DBus.Properties')
            debug("Received property %s.%s" % (self.interface_name, name), data)
            return self.postprocess(name, self.unwrap(data))
        def set(self, value):
            data = self.wrap(self.preprocess(name, data))
            debug("Setting property %s.%s" % (self.interface_name, name), value)
            return self.proxy.Set(self.interface_name, name, value, dbus_interface='org.freedesktop.DBus.Properties')
        return property(get, set)

    def unwrap(self, val):
        if isinstance(val, dbus.ByteArray):
            return "".join([str(x) for x in val])
        if isinstance(val, (dbus.Array, list, tuple)):
            return [self.unwrap(x) for x in val]
        if isinstance(val, (dbus.Dictionary, dict)):
            return dict([(self.unwrap(x), self.unwrap(y)) for x,y in val.items()])
        if isinstance(val, dbus.ObjectPath):
            if val.startswith('/org/freedesktop/NetworkManager/'):
                classname = val.split('/')[4]
                classname = {
                   'Settings': 'Connection',
                   'Devices': 'Device',
                }.get(classname, classname)
                return globals()[classname](val)
        if isinstance(val, (dbus.Signature, dbus.String)):
            return unicode(val)
        if isinstance(val, dbus.Boolean):
            return bool(val)
        if isinstance(val, (dbus.Int16, dbus.UInt16, dbus.Int32, dbus.UInt32, dbus.Int64, dbus.UInt64)):
            return int(val)
        if isinstance(val, dbus.Byte):
            return bytes([int(val)])
        return val

    def wrap(self, val):
        if isinstance(val, NMDbusInterface):
            return val.object_path
        if hasattr(val, 'mro'):
            for klass in val.mro():
                if klass.__module__ == '_dbus_bindings':
                    return val
        if hasattr(val, '__iter__') and not isinstance(val, basestring):
            if hasattr(val, 'items'):
                return dict([(x, self.wrap(y)) for x, y in val.items()])
            else:
                return [self.wrap(x) for x in val]
        return val

    def  __getattr__(self, name):
        try:
            return super(NMDbusInterface, self).__getattribute__(name)
        except AttributeError:
            return self.make_proxy_call(name)

    def make_proxy_call(self, name):
        def proxy_call(*args, **kwargs):
            func = getattr(self.interface, name)
            args, kwargs = self.preprocess(name, args, kwargs)
            args = self.wrap(args)
            kwargs = self.wrap(kwargs)
            debug("Calling function %s.%s" % (self.interface_name, name), (args, kwargs))
            ret = func(*args, **kwargs)
            debug("Received return value for %s.%s" % (self.interface_name, name), ret)
            return self.postprocess(name, self.unwrap(ret))
        return proxy_call

    def connect_to_signal(self, signal, handler, *args, **kwargs):
        def helper(*args, **kwargs):
            args = [self.unwrap(x) for x in args]
            handler(*args, **kwargs)
        args = self.wrap(args)
        kwargs = self.wrap(kwargs)
        return self.proxy.connect_to_signal(signal, helper, *args, **kwargs)

    def postprocess(self, name, val):
        return val

    def preprocess(self, name, args, kwargs):
        return args, kwargs

class NetworkManager(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager'
    object_path = '/org/freedesktop/NetworkManager'

    def preprocess(self, name, args, kwargs):
        if name in ('AddConnection', 'Update', 'AddAndActivateConnection'):
            settings = args[0]
            for key in settings:
                if 'mac-address' in settings[key]:
                    settings[key]['mac-address'] = fixups.mac_to_dbus(settings[key]['mac-address'])
                if 'bssid' in settings[key]:
                    settings[key]['bssid'] = fixups.mac_to_dbus(settings[key]['mac-address'])
            if 'ssid' in settings.get('802-11-wireless', {}):
                settings['802-11-wireless']['ssid'] = fixups.ssid_to_dbus(settings['802-11-wireless']['ssid'])
            if 'ipv4' in settings:
                if 'addresses' in settings['ipv4']:
                    settings['ipv4']['addresses'] = [fixups.addrconf_to_dbus(addr) for addr in settings['ipv4']['addresses']]
                if 'routes' in settings['ipv4']:
                    settings['ipv4']['routes'] = [fixups.route_to_dbus(route) for route in settings['ipv4']['routes']]
                if 'dns' in settings['ipv4']:
                    settings['ipv4']['dns'] = [fixups.addr_to_dbus(addr) for addr in settings['ipv4']['dns']]
        return args, kwargs
NetworkManager = NetworkManager()

class Settings(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Settings'
    object_path = '/org/freedesktop/NetworkManager/Settings'
    preprocess = NetworkManager.preprocess
Settings = Settings()

class Connection(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Settings.Connection'
    has_secrets = ['802-1x', '802-11-wireless-security', 'cdma', 'gsm', 'pppoe', 'vpn']

    def GetSecrets(self, name=None):
        if name == None:
            settings = self.GetSettings()
            for key in self.has_secrets:
                if key in settings:
                    name = key
                    break
            else:
                return {}
        return self.make_proxy_call('GetSecrets')(name)

    def postprocess(self, name, val):
        if name == 'GetSettings':
            if 'ssid' in val.get('802-11-wireless', {}):
                val['802-11-wireless']['ssid'] = fixups.ssid_to_python(val['802-11-wireless']['ssid'])
            for key in val:
                val_ = val[key]
                if 'mac-address' in val_:
                    val_['mac-address'] = fixups.mac_to_python(val_['mac-address'])
                if 'bssid' in val_:
                    val_['bssid'] = fixups.mac_to_python(val_['bssid'])
            if 'ipv4' in val:
                val['ipv4']['addresses'] = [fixups.addrconf_to_python(addr) for addr in val['ipv4']['addresses']]
                val['ipv4']['routes'] = [fixups.route_to_python(route) for route in val['ipv4']['routes']]
                val['ipv4']['dns'] = [fixups.addr_to_python(addr) for addr in val['ipv4']['dns']]
        return val
    preprocess = NetworkManager.preprocess

class ActiveConnection(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Connection.Active'

class Device(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device'

    def SpecificDevice(self):
        return {
            NM_DEVICE_TYPE_ETHERNET: Wired,
            NM_DEVICE_TYPE_WIFI: Wireless,
            NM_DEVICE_TYPE_MODEM: Modem,
            NM_DEVICE_TYPE_BT: Bluetooth,
            NM_DEVICE_TYPE_OLPC_MESH: OlpcMesh,
            NM_DEVICE_TYPE_WIMAX: Wimax,
            NM_DEVICE_TYPE_INFINIBAND: Infiniband,
            NM_DEVICE_TYPE_BOND: Bond,
            NM_DEVICE_TYPE_VLAN: Vlan,
            NM_DEVICE_TYPE_ADSL: Adsl,
        }[self.DeviceType](self.object_path)

    def postprocess(self, name, val):
        if name == 'Ip4Address':
            return fixups.addr_to_python(val)
        return val

class AccessPoint(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.AccessPoint'

    def postprocess(self, name, val):
        if name == 'Ssid':
            return fixups.ssid_to_python(val)
        return val

class Wired(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Wired'

class Wireless(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Wireless'

class Modem(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Modem'

class Bluetooth(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Bluetooth'

class OlpcMesh(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.OlpcMesh'

class Wimax(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Wimax'

class Infiniband(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Infiniband'

class Bond(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Bond'

class Bridge(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Bridge'

class Vlan(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Vlan'

class Adsl(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.adsl'

class NSP(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Wimax.NSP'

class IP4Config(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.IP4Config'

    def postprocess(self, name, val):
        if name == 'Addresses':
            return [fixups.addrconf_to_python(addr) for addr in val]
        if name == 'Routes':
            return [fixups.route_to_python(route) for route in val]
        if name in ('Nameservers', 'WinsServers'):
            return [fixups.addr_to_python(addr) for addr in val]
        return val

class IP6Config(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.IP6Config'

class DHCP4Config(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.DHCP4Config'

class DHCP6Config(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.DHCP6Config'

class AgentManager(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.AgentManager'

class SecretAgent(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.SecretAgent'

class VPNConnection(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.VPN.Connection'

    def preprocess(self, name, args, kwargs):
        conf = args[0]
        conf['addresses'] = [fixups.addrconf_to_python(addr) for addr in conf['addresses']]
        conf['routes'] = [fixups.route_to_python(route) for route in conf['routes']]
        conf['dns'] = [fixups.addr_to_python(addr) for addr in conf['dns']]
        return args, kwargs

class VPNPlugin(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.VPN.Plugin'

def const(prefix, val):
    prefix = 'NM_' + prefix.upper() + '_'
    for key, vval in globals().items():
        if 'REASON' in key and 'REASON' not in prefix:
            continue
        if key.startswith(prefix) and val == vval:
            return key.replace(prefix,'').lower()
    raise ValueError("No constant found for %s* with value %d", (prefix, val))

# Several fixer methods to make the data easier to handle in python
# - SSID sent/returned as bytes (only encoding tried is utf-8)
# - IP, Mac address and route metric encoding/decoding
class fixups(object):
    @staticmethod
    def ssid_to_python(ssid):
        return bytes("",'ascii').join(ssid).decode('utf-8')

    @staticmethod
    def ssid_to_dbus(ssid):
        if isinstance(ssid, unicode):
            ssid = ssid.encode('utf-8')
        return [dbus.Byte(x) for x in ssid]

    @staticmethod
    def mac_to_python(mac):
        return "%02X:%02X:%02X:%02X:%02X:%02X" % tuple([ord(x) for x in mac])

    @staticmethod
    def mac_to_dbus(mac):
        return [dbus.Byte(int(x, 16)) for x in mac.split(':')]

    @staticmethod
    def addrconf_to_python(addrconf):
        addr, netmask, gateway = addrconf
        return [
            fixups.addr_to_python(addr),
            netmask,
            fixups.addr_to_python(gateway)
        ]

    @staticmethod
    def addrconf_to_dbus(addrconf):
        addr, netmask, gateway = addrconf
        return [
            fixups.addr_to_dbus(addr),
            fixups.mask_to_dbus(netmask),
            fixups.addr_to_dbus(gateway)
        ]

    @staticmethod
    def addr_to_python(addr):
        return socket.inet_ntoa(struct.pack('I', addr))

    @staticmethod
    def addr_to_dbus(addr):
        return dbus.UInt32(struct.unpack('I', socket.inet_aton(addr))[0])

    @staticmethod
    def mask_to_dbus(mask):
        return dbus.UInt32(mask)

    @staticmethod
    def route_to_python(route):
        addr, netmask, gateway, metric = route
        return [
            fixups.addr_to_python(addr),
            netmask,
            fixups.addr_to_python(gateway),
            socket.ntohl(metric)
        ]

    @staticmethod
    def route_to_dbus(route):
        addr, netmask, gateway, metric = route
        return [
            fixups.addr_to_dbus(addr),
            fixups.mask_to_dbus(netmask),
            fixups.addr_to_dbus(gateway),
            socket.htonl(metric)
        ]

# Constants below are generated with makeconstants.py. Do not edit manually.
NM_STATE_UNKNOWN = 0
NM_STATE_ASLEEP = 10
NM_STATE_DISCONNECTED = 20
NM_STATE_DISCONNECTING = 30
NM_STATE_CONNECTING = 40
NM_STATE_CONNECTED_LOCAL = 50
NM_STATE_CONNECTED_SITE = 60
NM_STATE_CONNECTED_GLOBAL = 70
NM_DEVICE_TYPE_UNKNOWN = 0
NM_DEVICE_TYPE_ETHERNET = 1
NM_DEVICE_TYPE_WIFI = 2
NM_DEVICE_TYPE_UNUSED1 = 3
NM_DEVICE_TYPE_UNUSED2 = 4
NM_DEVICE_TYPE_BT = 5
NM_DEVICE_TYPE_OLPC_MESH = 6
NM_DEVICE_TYPE_WIMAX = 7
NM_DEVICE_TYPE_MODEM = 8
NM_DEVICE_TYPE_INFINIBAND = 9
NM_DEVICE_TYPE_BOND = 10
NM_DEVICE_TYPE_VLAN = 11
NM_DEVICE_TYPE_ADSL = 12
NM_DEVICE_CAP_NONE = 0
NM_DEVICE_CAP_NM_SUPPORTED = 1
NM_DEVICE_CAP_CARRIER_DETECT = 2
NM_WIFI_DEVICE_CAP_NONE = 0
NM_WIFI_DEVICE_CAP_CIPHER_WEP40 = 1
NM_WIFI_DEVICE_CAP_CIPHER_WEP104 = 2
NM_WIFI_DEVICE_CAP_CIPHER_TKIP = 4
NM_WIFI_DEVICE_CAP_CIPHER_CCMP = 8
NM_WIFI_DEVICE_CAP_WPA = 16
NM_WIFI_DEVICE_CAP_RSN = 32
NM_WIFI_DEVICE_CAP_AP = 64
NM_WIFI_DEVICE_CAP_IBSS_RSN = 128
NM_802_11_AP_FLAGS_NONE = 0
NM_802_11_AP_FLAGS_PRIVACY = 1
NM_802_11_AP_SEC_NONE = 0
NM_802_11_AP_SEC_PAIR_WEP40 = 1
NM_802_11_AP_SEC_PAIR_WEP104 = 2
NM_802_11_AP_SEC_PAIR_TKIP = 4
NM_802_11_AP_SEC_PAIR_CCMP = 8
NM_802_11_AP_SEC_GROUP_WEP40 = 16
NM_802_11_AP_SEC_GROUP_WEP104 = 32
NM_802_11_AP_SEC_GROUP_TKIP = 64
NM_802_11_AP_SEC_GROUP_CCMP = 128
NM_802_11_AP_SEC_KEY_MGMT_PSK = 256
NM_802_11_AP_SEC_KEY_MGMT_802_1X = 512
NM_802_11_MODE_UNKNOWN = 0
NM_802_11_MODE_ADHOC = 1
NM_802_11_MODE_INFRA = 2
NM_BT_CAPABILITY_NONE = 0
NM_BT_CAPABILITY_DUN = 1
NM_BT_CAPABILITY_NAP = 2
NM_DEVICE_MODEM_CAPABILITY_NONE = 0
NM_DEVICE_MODEM_CAPABILITY_POTS = 1
NM_DEVICE_MODEM_CAPABILITY_CDMA_EVDO = 2
NM_DEVICE_MODEM_CAPABILITY_GSM_UMTS = 4
NM_DEVICE_MODEM_CAPABILITY_LTE = 8
NM_DEVICE_STATE_UNKNOWN = 0
NM_DEVICE_STATE_UNMANAGED = 10
NM_DEVICE_STATE_UNAVAILABLE = 20
NM_DEVICE_STATE_DISCONNECTED = 30
NM_DEVICE_STATE_PREPARE = 40
NM_DEVICE_STATE_CONFIG = 50
NM_DEVICE_STATE_NEED_AUTH = 60
NM_DEVICE_STATE_IP_CONFIG = 70
NM_DEVICE_STATE_IP_CHECK = 80
NM_DEVICE_STATE_SECONDARIES = 90
NM_DEVICE_STATE_ACTIVATED = 100
NM_DEVICE_STATE_DEACTIVATING = 110
NM_DEVICE_STATE_FAILED = 120
NM_DEVICE_STATE_REASON_NONE = 0
NM_DEVICE_STATE_REASON_UNKNOWN = 1
NM_DEVICE_STATE_REASON_NOW_MANAGED = 2
NM_DEVICE_STATE_REASON_NOW_UNMANAGED = 3
NM_DEVICE_STATE_REASON_CONFIG_FAILED = 4
NM_DEVICE_STATE_REASON_IP_CONFIG_UNAVAILABLE = 5
NM_DEVICE_STATE_REASON_IP_CONFIG_EXPIRED = 6
NM_DEVICE_STATE_REASON_NO_SECRETS = 7
NM_DEVICE_STATE_REASON_SUPPLICANT_DISCONNECT = 8
NM_DEVICE_STATE_REASON_SUPPLICANT_CONFIG_FAILED = 9
NM_DEVICE_STATE_REASON_SUPPLICANT_FAILED = 10
NM_DEVICE_STATE_REASON_SUPPLICANT_TIMEOUT = 11
NM_DEVICE_STATE_REASON_PPP_START_FAILED = 12
NM_DEVICE_STATE_REASON_PPP_DISCONNECT = 13
NM_DEVICE_STATE_REASON_PPP_FAILED = 14
NM_DEVICE_STATE_REASON_DHCP_START_FAILED = 15
NM_DEVICE_STATE_REASON_DHCP_ERROR = 16
NM_DEVICE_STATE_REASON_DHCP_FAILED = 17
NM_DEVICE_STATE_REASON_SHARED_START_FAILED = 18
NM_DEVICE_STATE_REASON_SHARED_FAILED = 19
NM_DEVICE_STATE_REASON_AUTOIP_START_FAILED = 20
NM_DEVICE_STATE_REASON_AUTOIP_ERROR = 21
NM_DEVICE_STATE_REASON_AUTOIP_FAILED = 22
NM_DEVICE_STATE_REASON_MODEM_BUSY = 23
NM_DEVICE_STATE_REASON_MODEM_NO_DIAL_TONE = 24
NM_DEVICE_STATE_REASON_MODEM_NO_CARRIER = 25
NM_DEVICE_STATE_REASON_MODEM_DIAL_TIMEOUT = 26
NM_DEVICE_STATE_REASON_MODEM_DIAL_FAILED = 27
NM_DEVICE_STATE_REASON_MODEM_INIT_FAILED = 28
NM_DEVICE_STATE_REASON_GSM_APN_FAILED = 29
NM_DEVICE_STATE_REASON_GSM_REGISTRATION_NOT_SEARCHING = 30
NM_DEVICE_STATE_REASON_GSM_REGISTRATION_DENIED = 31
NM_DEVICE_STATE_REASON_GSM_REGISTRATION_TIMEOUT = 32
NM_DEVICE_STATE_REASON_GSM_REGISTRATION_FAILED = 33
NM_DEVICE_STATE_REASON_GSM_PIN_CHECK_FAILED = 34
NM_DEVICE_STATE_REASON_FIRMWARE_MISSING = 35
NM_DEVICE_STATE_REASON_REMOVED = 36
NM_DEVICE_STATE_REASON_SLEEPING = 37
NM_DEVICE_STATE_REASON_CONNECTION_REMOVED = 38
NM_DEVICE_STATE_REASON_USER_REQUESTED = 39
NM_DEVICE_STATE_REASON_CARRIER = 40
NM_DEVICE_STATE_REASON_CONNECTION_ASSUMED = 41
NM_DEVICE_STATE_REASON_SUPPLICANT_AVAILABLE = 42
NM_DEVICE_STATE_REASON_MODEM_NOT_FOUND = 43
NM_DEVICE_STATE_REASON_BT_FAILED = 44
NM_DEVICE_STATE_REASON_GSM_SIM_NOT_INSERTED = 45
NM_DEVICE_STATE_REASON_GSM_SIM_PIN_REQUIRED = 46
NM_DEVICE_STATE_REASON_GSM_SIM_PUK_REQUIRED = 47
NM_DEVICE_STATE_REASON_GSM_SIM_WRONG = 48
NM_DEVICE_STATE_REASON_INFINIBAND_MODE = 49
NM_DEVICE_STATE_REASON_DEPENDENCY_FAILED = 50
NM_DEVICE_STATE_REASON_BR2684_FAILED = 51
NM_DEVICE_STATE_REASON_LAST = 65535
NM_ACTIVE_CONNECTION_STATE_UNKNOWN = 0
NM_ACTIVE_CONNECTION_STATE_ACTIVATING = 1
NM_ACTIVE_CONNECTION_STATE_ACTIVATED = 2
NM_ACTIVE_CONNECTION_STATE_DEACTIVATING = 3
NM_VPN_SERVICE_STATE_UNKNOWN = 0
NM_VPN_SERVICE_STATE_INIT = 1
NM_VPN_SERVICE_STATE_SHUTDOWN = 2
NM_VPN_SERVICE_STATE_STARTING = 3
NM_VPN_SERVICE_STATE_STARTED = 4
NM_VPN_SERVICE_STATE_STOPPING = 5
NM_VPN_SERVICE_STATE_STOPPED = 6
NM_VPN_CONNECTION_STATE_UNKNOWN = 0
NM_VPN_CONNECTION_STATE_PREPARE = 1
NM_VPN_CONNECTION_STATE_NEED_AUTH = 2
NM_VPN_CONNECTION_STATE_CONNECT = 3
NM_VPN_CONNECTION_STATE_IP_CONFIG_GET = 4
NM_VPN_CONNECTION_STATE_ACTIVATED = 5
NM_VPN_CONNECTION_STATE_FAILED = 6
NM_VPN_CONNECTION_STATE_DISCONNECTED = 7
NM_VPN_CONNECTION_STATE_REASON_UNKNOWN = 0
NM_VPN_CONNECTION_STATE_REASON_NONE = 1
NM_VPN_CONNECTION_STATE_REASON_USER_DISCONNECTED = 2
NM_VPN_CONNECTION_STATE_REASON_DEVICE_DISCONNECTED = 3
NM_VPN_CONNECTION_STATE_REASON_SERVICE_STOPPED = 4
NM_VPN_CONNECTION_STATE_REASON_IP_CONFIG_INVALID = 5
NM_VPN_CONNECTION_STATE_REASON_CONNECT_TIMEOUT = 6
NM_VPN_CONNECTION_STATE_REASON_SERVICE_START_TIMEOUT = 7
NM_VPN_CONNECTION_STATE_REASON_SERVICE_START_FAILED = 8
NM_VPN_CONNECTION_STATE_REASON_NO_SECRETS = 9
NM_VPN_CONNECTION_STATE_REASON_LOGIN_FAILED = 10
NM_VPN_CONNECTION_STATE_REASON_CONNECTION_REMOVED = 11
NM_VPN_PLUGIN_FAILURE_LOGIN_FAILED = 0
NM_VPN_PLUGIN_FAILURE_CONNECT_FAILED = 1
NM_VPN_PLUGIN_FAILURE_BAD_IP_CONFIG = 2
