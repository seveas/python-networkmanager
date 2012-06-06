import dbus
import sys

if sys.version_info >= (3,0):
    basestring = str

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
            return self.unwrap(self.proxy.Get(self.interface_name, name,
                                  dbus_interface='org.freedesktop.DBus.Properties'))
        def set(self, value):
            return self.proxy.Set(self.interface_name, name, self.wrap(value),
                                  dbus_interface='org.freedesktop.DBus.Properties')
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
            return str(val)
        if isinstance(val, dbus.Boolean):
            return bool(val)
        if isinstance(val, (dbus.Int16, dbus.UInt16, dbus.Int32, dbus.UInt32, dbus.Int64, dbus.UInt64)):
            return int(val)
        return val
    
    def wrap(self, val):
        if isinstance(val, NMDbusInterface):
            return val.object_path
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
            def proxy_call(*args, **kwargs):
                func = getattr(self.interface, name)
                args = self.wrap(args)
                kwargs = self.wrap(kwargs)
                ret = func(*args, **kwargs)
                return self.unwrap(ret)
            return proxy_call

    def connect_to_signal(self, signal, handler, *args, **kwargs):
        def helper(*args, **kwargs):
            args = [self.unwrap(x) for x in args]
            handler(*args, **kwargs)
        args = self.wrap(args)
        kwargs = self.wrap(kwargs)
        return self.proxy.connect_to_signal(signal, helper, *args, **kwargs)

class NetworkManager(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager'
    object_path = '/org/freedesktop/NetworkManager'
NetworkManager = NetworkManager()

class Settings(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Settings'
    object_path = '/org/freedesktop/NetworkManager/Settings'
Settings = Settings()

class Connection(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Settings.Connection'

class ActiveConnection(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Connection.Active'

class Device(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device'

    def SpecificDevice(self):
        return {
            NM_DEVICE_TYPE_ETHERNET: Wired,
            NM_DEVICE_TYPE_WIFI: Wireless,
            NM_DEVICE_TYPE_BT: Bluetooth,
            NM_DEVICE_TYPE_OLPC_MESH: OlpcMesh,
            NM_DEVICE_TYPE_WIMAX: Wimax,
            NM_DEVICE_TYPE_MODEM: Modem,
        }[self.DeviceType](self.object_path)

class AccessPoint(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.AccessPoint'

class Wired(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Wired'

class Wireless(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Wireless'

class Modem(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Modem'

class Bluetooth(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Bluetooth'

class Wimax(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.Wimax'

class OlpcMesh(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.Device.OlpcMesh'

class IP4Config(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.IP4Config'

class IP6Config(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.IP6Config'

class VPNConnection(NMDbusInterface):
    interface_name = 'org.freedesktop.NetworkManager.VPN.Connection'


def const(prefix, val):
    prefix = 'NM_' + prefix.upper() + '_'
    for key, vval in globals().items():
        if 'REASON' in key and 'REASON' not in prefix:
            continue
        if key.startswith(prefix) and val == vval:
            return key.replace(prefix,'').lower()
    raise ValueError("No constant found for %s* with value %d", (prefix, val))

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
