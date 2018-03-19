# NetworkManager - a library to make interacting with the NetworkManager daemon
# easier.
#
# (C)2011-2017 Dennis Kaarsemaker
# License: zlib

import copy
import dbus
import dbus.service
import os
import six
import socket
import struct
import sys
import time
import warnings
import weakref
import xml.etree.ElementTree as etree

class ObjectVanished(Exception):
    def __init__(self, obj):
        self.obj = obj
        super(ObjectVanished, self).__init__(obj.object_path)

class SignalDispatcher(object):
    def __init__(self):
        self.handlers = {}
        self.args = {}
        self.interfaces = set()
        self.setup = False

    def setup_signals(self):
        if not self.setup:
            bus = dbus.SystemBus()
            for interface in self.interfaces:
                bus.add_signal_receiver(self.handle_signal, dbus_interface=interface, interface_keyword='interface', member_keyword='signal', path_keyword='path')
            self.setup = True
        self.listen_for_restarts()

    def listen_for_restarts(self):
        # If we have a mainloop, listen for disconnections
        if not NMDbusInterface.last_disconnect and dbus.get_default_main_loop():
           dbus.SystemBus().add_signal_receiver(self.handle_restart, 'NameOwnerChanged', 'org.freedesktop.DBus')
           NMDbusInterface.last_disconnect = 1

    def add_signal_receiver(self, interface, signal, obj, func, args, kwargs):
        self.setup_signals()
        key = (interface, signal)
        if key not in self.handlers:
            self.handlers[key] = []
        self.handlers[key].append((obj, func, args, kwargs))

    def handle_signal(self, *args, **kwargs):
        key = (kwargs['interface'], kwargs['signal'])
        skwargs = {}
        sargs = []
        if key not in self.handlers:
            return
        sender = fixups.base_to_python(kwargs['path'])
        for arg, (name, signature) in zip(args, self.args[key]):
            if name:
                skwargs[name] = fixups.to_python(type(sender).__name__, kwargs['signal'], name, arg, signature)
            else:
                # Older NetworkManager versions don't supply attribute names. Hope for the best.
                sargs.append(fixups.to_python(type(sender).__name__, kwargs['signal'], None, arg, signature))
        to_delete = []
        for pos, (match, receiver, rargs, rkwargs) in enumerate(self.handlers[key]):
            try:
                match == sender
            except ObjectVanished:
                to_delete.append(pos)
                continue
            if match == sender:
                rkwargs['interface'] = kwargs['interface']
                rkwargs['signal'] = kwargs['signal']
                rkwargs.update(skwargs)
                receiver(sender, *(sargs + rargs), **rkwargs)
        for pos in reversed(to_delete):
            self.handlers[key].pop(pos)

    def handle_restart(self, name, old, new):
        if str(new) == "" or str(name) != 'org.freedesktop.NetworkManager':
            return
        NMDbusInterface.last_disconnect = time.time()
        for key in self.handlers:
            val, self.handlers[key] = self.handlers[key], []
            for obj, func, args, kwargs in val:
                try:
                    # This resets the object path if needed
                    obj.proxy
                    self.add_signal_receiver(key[0], key[1], obj, func, args, kwargs)
                except ObjectVanished:
                    pass
SignalDispatcher = SignalDispatcher()

# We completely dynamically generate all classes using introspection data. As
# this is done at import time, use a special dbus connection that does not get
# in the way of setting a mainloop and doing async stuff later.
init_bus = dbus.SystemBus(private=True)
xml_cache = {}

class NMDbusInterfaceType(type):
    """Metaclass that generates our classes based on introspection data"""
    dbus_service = 'org.freedesktop.NetworkManager'

    def __new__(type_, name, bases, attrs):
        attrs['dbus_service'] = type_.dbus_service
        attrs['properties'] = []
        attrs['introspection_data'] = None
        attrs['signals'] = []

        # Derive the interface name from the name of the class, but let classes
        # override it if needed
        if 'interface_names' not in attrs and 'NMDbusInterface' not in name:
            attrs['interface_names'] = ['org.freedesktop.NetworkManager.%s' % name]
            for base in bases:
                if hasattr(base, 'interface_names'):
                    attrs['interface_names'] = ['%s.%s' % (base.interface_names[0], name)] + base.interface_names
                    break
        else:
            for base in bases:
                if hasattr(base, 'interface_names'):
                    attrs['interface_names'] += base.interface_names
                    break

        if 'interface_names' in attrs:
            SignalDispatcher.interfaces.update(attrs['interface_names'])

        # If we know where to find this object, let's introspect it and
        # generate properties and methods
        if 'object_path' in attrs and attrs['object_path']:
            proxy = init_bus.get_object(type_.dbus_service, attrs['object_path'])
            attrs['introspection_data'] = proxy.Introspect(dbus_interface='org.freedesktop.DBus.Introspectable')
            root = etree.fromstring(attrs['introspection_data'])
            for element in root:
                if element.tag == 'interface' and element.attrib['name'] in attrs['interface_names']:
                    for item in element:
                        if item.tag == 'property':
                            attrs[item.attrib['name']] = type_.make_property(name, element.attrib['name'], item.attrib)
                            attrs['properties'].append(item.attrib['name'])
                        elif item.tag == 'method':
                            aname = item.attrib['name']
                            if aname in attrs:
                                aname = '_' + aname
                            attrs[aname] = type_.make_method(name, element.attrib['name'], item.attrib, list(item))
                        elif item.tag == 'signal':
                            SignalDispatcher.args[(element.attrib['name'], item.attrib['name'])] = [(arg.attrib.get('name',None), arg.attrib['type']) for arg in item]
                            attrs['On' + item.attrib['name']] = type_.make_signal(name, element.attrib['name'], item.attrib)
                            attrs['signals'].append(item.attrib['name'])

        klass = super(NMDbusInterfaceType, type_).__new__(type_, name, bases, attrs)
        return klass

    @staticmethod
    def make_property(klass, interface, attrib):
        name = attrib['name']
        def get_func(self):
            try:
                data = self.proxy.Get(interface, name, dbus_interface='org.freedesktop.DBus.Properties')
            except dbus.exceptions.DBusException as e:
                if e.get_dbus_name() == 'org.freedesktop.DBus.Error.UnknownMethod':
                    raise ObjectVanished(self)
                raise
            return fixups.to_python(klass, 'Get', name, data, attrib['type'])
        if attrib['access'] == 'read':
            return property(get_func)
        def set_func(self, value):
            value = fixups.to_dbus(klass, 'Set', name, value, attrib['type'])
            try:
                return self.proxy.Set(interface, name, value, dbus_interface='org.freedesktop.DBus.Properties')
            except dbus.exceptions.DBusException as e:
                if e.get_dbus_name() == 'org.freedesktop.DBus.Error.UnknownMethod':
                    raise ObjectVanished(self)
                raise
        return property(get_func, set_func)

    @staticmethod
    def make_method(klass, interface, attrib, args):
        name = attrib['name']
        outargs = [x for x in args if x.tag == 'arg' and x.attrib['direction'] == 'out']
        outargstr = ', '.join([x.attrib['name'] for x in outargs]) or 'ret'
        args = [x for x in args if x.tag == 'arg' and x.attrib['direction'] == 'in']
        argstr = ', '.join([x.attrib['name'] for x in args])
        ret = {}
        code = "def %s(self%s):\n" % (name, ', ' + argstr if argstr else '')
        for arg in args:
            argname = arg.attrib['name']
            signature = arg.attrib['type']
            code += "    %s = fixups.to_dbus('%s', '%s', '%s', %s, '%s')\n" % (argname, klass, name, argname, argname, signature)
        code += "    try:\n"
        code += "        %s = dbus.Interface(self.proxy, '%s').%s(%s)\n" % (outargstr, interface, name, argstr)
        code += "    except dbus.exceptions.DBusException as e:\n"
        code += "        if e.get_dbus_name() == 'org.freedesktop.DBus.Error.UnknownMethod':\n"
        code += "            raise ObjectVanished(self)\n"
        code += "        raise\n"
        for arg in outargs:
            argname = arg.attrib['name']
            signature = arg.attrib['type']
            code += "    %s = fixups.to_python('%s', '%s', '%s', %s, '%s')\n" % (argname, klass, name, argname, argname, signature)
        code += "    return (%s)" % outargstr
        exec(code, globals(), ret)
        return ret[name]

    @staticmethod
    def make_signal(klass, interface, attrib):
        name = attrib['name']
        ret = {}
        code = "def On%s(self, func, *args, **kwargs):" % name
        code += "    SignalDispatcher.add_signal_receiver('%s', '%s', self, func, list(args), kwargs)"  % (interface, name)
        exec(code, globals(), ret)
        return ret['On' + name]

@six.add_metaclass(NMDbusInterfaceType)
class NMDbusInterface(object):
    object_path = None
    last_disconnect = 0
    is_transient = False

    def __new__(klass, object_path=None):
        # If we didn't introspect this one at definition time, let's do it now.
        if object_path and not klass.introspection_data:
            proxy = dbus.SystemBus().get_object(klass.dbus_service, object_path)
            klass.introspection_data = proxy.Introspect(dbus_interface='org.freedesktop.DBus.Introspectable')
            root = etree.fromstring(klass.introspection_data)
            for element in root:
                if element.tag == 'interface' and element.attrib['name'] in klass.interface_names:
                    for item in element:
                        if item.tag == 'property':
                            setattr(klass, item.attrib['name'], type(klass).make_property(klass.__name__, element.attrib['name'], item.attrib))
                            klass.properties.append(item.attrib['name'])
                        elif item.tag == 'method':
                            aname = item.attrib['name']
                            if hasattr(klass, aname):
                                aname = '_' + aname
                            setattr(klass, aname, type(klass).make_method(klass.__name__, element.attrib['name'], item.attrib, list(item)))
                        elif item.tag == 'signal':
                            SignalDispatcher.args[(element.attrib['name'], item.attrib['name'])] = [(arg.attrib.get('name',None), arg.attrib['type']) for arg in item]
                            setattr(klass, 'On' + item.attrib['name'], type(klass).make_signal(klass.__name__, element.attrib['name'], item.attrib))
                            klass.signals.append(item.attrib['name'])

        SignalDispatcher.listen_for_restarts()
        return super(NMDbusInterface, klass).__new__(klass)

    def __init__(self, object_path=None):
        if isinstance(object_path, NMDbusInterface):
            object_path = object_path.object_path
        self.object_path = self.object_path or object_path
        self._proxy = None

    def __eq__(self, other):
        return isinstance(other, NMDbusInterface) and self.object_path and other.object_path == self.object_path

    @property
    def proxy(self):
        if not self._proxy:
            self._proxy = dbus.SystemBus().get_object(self.dbus_service, self.object_path)
            self._proxy.created = time.time()
        elif self._proxy.created < self.last_disconnect:
            if self.is_transient:
                raise ObjectVanished(self)
            obj = type(self)(self.object_path)
            if obj != self:
                self.object_path = obj.object_path
            self._proxy = dbus.SystemBus().get_object(self.dbus_service, self.object_path)
            self._proxy.created = time.time()
        return self._proxy

    # Backwards compatibility interface
    def connect_to_signal(self, signal, handler, *args, **kwargs):
        return getattr(self, 'On' + signal)(handler, *args, **kwargs)

class TransientNMDbusInterface(NMDbusInterface):
    is_transient = True

class NetworkManager(NMDbusInterface):
    interface_names = ['org.freedesktop.NetworkManager']
    object_path = '/org/freedesktop/NetworkManager'

    # noop method for backward compatibility. It is no longer necessary to call
    # this but let's not break code that does so.
    def auto_reconnect(self):
        pass

class Settings(NMDbusInterface):
    object_path = '/org/freedesktop/NetworkManager/Settings'

class AgentManager(NMDbusInterface):
    object_path = '/org/freedesktop/NetworkManager/AgentManager'

class Connection(NMDbusInterface):
    interface_names = ['org.freedesktop.NetworkManager.Settings.Connection']
    has_secrets = ['802-1x', '802-11-wireless-security', 'cdma', 'gsm', 'pppoe', 'vpn']

    def __init__(self, object_path):
        super(Connection, self).__init__(object_path)
        self.uuid = self.GetSettings()['connection']['uuid']

    def GetSecrets(self, name=None):
        if name == None:
            settings = self.GetSettings()
            name = settings['connection']['type']
            name = settings[name].get('security', name)
        try:
            return self._GetSecrets(name)
        except dbus.exceptions.DBusException as e:
            if e.get_dbus_name() != 'org.freedesktop.NetworkManager.AgentManager.NoSecrets':
                raise
            return {}

    @staticmethod
    def all():
        return Settings.ListConnections()

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.uuid == other.uuid

class ActiveConnection(TransientNMDbusInterface):
    interface_names = ['org.freedesktop.NetworkManager.Connection.Active']
    def __new__(klass, object_path):
        if klass == ActiveConnection:
            # Automatically turn this into a VPNConnection if needed
            obj = dbus.SystemBus().get_object(klass.dbus_service, object_path)
            if obj.Get('org.freedesktop.NetworkManager.Connection.Active', 'Vpn', dbus_interface='org.freedesktop.DBus.Properties'):
                return VPNConnection.__new__(VPNConnection, object_path)
        return super(ActiveConnection, klass).__new__(klass, object_path)

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.Uuid == other.Uuid

class VPNConnection(ActiveConnection):
    interface_names = ['org.freedesktop.NetworkManager.VPN.Connection']

class Device(NMDbusInterface):
    def __new__(klass, object_path):
        if klass == Device:
            # Automatically specialize the device
            try:
                obj = dbus.SystemBus().get_object(klass.dbus_service, object_path)
                klass = device_class(obj.Get('org.freedesktop.NetworkManager.Device', 'DeviceType', dbus_interface='org.freedesktop.DBus.Properties'))
                return klass.__new__(klass, object_path)
            except (ObjectVanished, dbus.exceptions.DBusException):
                pass
        return super(Device, klass).__new__(klass, object_path)

    @staticmethod
    def all():
        return NetworkManager.Devices

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.IpInterface == other.IpInterface

    # Backwards compatibility method. Devices now auto-specialize, so this is
    # no longer needed. But code may use it.
    def SpecificDevice(self):
        return self


def device_class(typ):
    return {
        NM_DEVICE_TYPE_ADSL: Adsl,
        NM_DEVICE_TYPE_BOND: Bond,
        NM_DEVICE_TYPE_BRIDGE: Bridge,
        NM_DEVICE_TYPE_BT: Bluetooth,
        NM_DEVICE_TYPE_ETHERNET: Wired,
        NM_DEVICE_TYPE_GENERIC: Generic,
        NM_DEVICE_TYPE_INFINIBAND: Infiniband,
        NM_DEVICE_TYPE_IP_TUNNEL: IPTunnel,
        NM_DEVICE_TYPE_MACVLAN: Macvlan,
        NM_DEVICE_TYPE_MODEM: Modem,
        NM_DEVICE_TYPE_OLPC_MESH: OlpcMesh,
        NM_DEVICE_TYPE_TEAM: Team,
        NM_DEVICE_TYPE_TUN: Tun,
        NM_DEVICE_TYPE_VETH: Veth,
        NM_DEVICE_TYPE_VLAN: Vlan,
        NM_DEVICE_TYPE_VXLAN: Vxlan,
        NM_DEVICE_TYPE_WIFI: Wireless,
        NM_DEVICE_TYPE_WIMAX: Wimax,
    }[typ]

class Adsl(Device): pass
class Bluetooth(Device): pass
class Bond(Device): pass
class Bridge(Device): pass
class Generic(Device): pass
class Infiniband(Device): pass
class IPTunnel(Device): pass
class Macvlan(Device): pass
class Modem(Device): pass
class OlpcMesh(Device): pass
class Team(Device): pass
class Tun(Device): pass
class Veth(Device): pass
class Vlan(Device): pass
class Vxlan(Device): pass
class Wimax(Device): pass
class Wired(Device): pass
class Wireless(Device): pass

class NSP(TransientNMDbusInterface):
    interface_names = ['org.freedesktop.NetworkManager.Wimax.NSP']

class AccessPoint(NMDbusInterface):
    @staticmethod
    def all():
        for device in Device.all():
            if isinstance(device, Wireless):
                for ap in device.AccessPoints:
                    yield ap
    def __eq__(self, other):
        return isinstance(other, type(self)) and self.HwAddress == other.HwAddress

class IP4Config(TransientNMDbusInterface): pass
class IP6Config(TransientNMDbusInterface): pass
class DHCP4Config(TransientNMDbusInterface): pass
class DHCP6Config(TransientNMDbusInterface): pass

# Evil hack to work around not being able to specify a method name in the
# dbus.service.method decorator.
class SecretAgentType(type(dbus.service.Object)):
    def __new__(type_, name, bases, attrs):
        if bases != (dbus.service.Object,):
            attrs['GetSecretsImpl'] = attrs.pop('GetSecrets')
        return super(SecretAgentType, type_).__new__(type_, name, bases, attrs)

@six.add_metaclass(SecretAgentType)
class SecretAgent(dbus.service.Object):
    object_path = '/org/freedesktop/NetworkManager/SecretAgent'
    interface_name = 'org.freedesktop.NetworkManager.SecretAgent'

    def __init__(self, identifier):
        self.identifier = identifier
        dbus.service.Object.__init__(self, dbus.SystemBus(), self.object_path)
        AgentManager.Register(self.identifier)

    @dbus.service.method(dbus_interface=interface_name, in_signature='a{sa{sv}}osasu', out_signature='a{sa{sv}}')
    def GetSecrets(self, connection, connection_path, setting_name, hints, flags):
        settings = fixups.to_python('SecretAgent', 'GetSecrets', 'connection', connection, 'a{sa{sv}}')
        connection = fixups.to_python('SecretAgent', 'GetSecrets', 'connection_path', connection_path, 'o')
        setting_name = fixups.to_python('SecretAgent', 'GetSecrets', 'setting_name', setting_name, 's')
        hints = fixups.to_python('SecretAgent', 'GetSecrets', 'hints', hints, 'as')
        return self.GetSecretsImpl(settings, connection, setting_name, hints, flags)

# These two are interfaces that must be provided to NetworkManager. Keep them
# as comments for documentation purposes.
#
# class PPP(NMDbusInterface): pass
# class VPNPlugin(NMDbusInterface):
#     interface_names = ['org.freedesktop.NetworkManager.VPN.Plugin']

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
    def to_dbus(klass, method, arg, val, signature):
        if arg in ('connection' 'properties') and signature == 'a{sa{sv}}':
            settings = copy.deepcopy(val)
            for key in settings:
                if 'mac-address' in settings[key]:
                    settings[key]['mac-address'] = fixups.mac_to_dbus(settings[key]['mac-address'])
                if 'cloned-mac-address' in settings[key]:
                    settings[key]['cloned-mac-address'] = fixups.mac_to_dbus(settings[key]['cloned-mac-address'])
                if 'bssid' in settings[key]:
                    settings[key]['bssid'] = fixups.mac_to_dbus(settings[key]['bssid'])
                for cert in ['ca-cert', 'client-cert', 'phase2-ca-cert', 'phase2-client-cert', 'private-key']:
                    if cert in settings[key]:
                        settings[key][cert] = fixups.cert_to_dbus(settings[key][cert])
            if 'ssid' in settings.get('802-11-wireless', {}):
                settings['802-11-wireless']['ssid'] = fixups.ssid_to_dbus(settings['802-11-wireless']['ssid'])
            if 'ipv4' in settings:
                if 'address-data' in settings['ipv4']:
                    for item in settings['ipv4']['address-data']:
                        item['prefix'] = dbus.UInt32(item['prefix'])
                    settings['ipv4']['address-data'] = dbus.Array(
                        settings['ipv4']['address-data'],
                        signature=dbus.Signature('a{sv}'))
                if 'addresses' in settings['ipv4']:
                    settings['ipv4']['addresses'] = [fixups.addrconf_to_dbus(addr,socket.AF_INET) for addr in settings['ipv4']['addresses']]
                if 'routes' in settings['ipv4']:
                    settings['ipv4']['routes'] = [fixups.route_to_dbus(route,socket.AF_INET) for route in settings['ipv4']['routes']]
                if 'dns' in settings['ipv4']:
                    settings['ipv4']['dns'] = [fixups.addr_to_dbus(addr,socket.AF_INET) for addr in settings['ipv4']['dns']]
            if 'ipv6' in settings:
                if 'addresses' in settings['ipv6']:
                    settings['ipv6']['addresses'] = [fixups.addrconf_to_dbus(addr,socket.AF_INET6) for addr in settings['ipv6']['addresses']]
                if 'routes' in settings['ipv6']:
                    settings['ipv6']['routes'] = [fixups.route_to_dbus(route,socket.AF_INET6) for route in settings['ipv6']['routes']]
                if 'dns' in settings['ipv6']:
                    settings['ipv6']['dns'] = [fixups.addr_to_dbus(addr,socket.AF_INET6) for addr in settings['ipv6']['dns']]
            # Get rid of empty arrays/dicts. dbus barfs on them (can't guess
            # signatures), and if they were to get through, NetworkManager
            # ignores them anyway.
            for key in list(settings.keys()):
                if isinstance(settings[key], dict):
                    for key2 in list(settings[key].keys()):
                        if settings[key][key2] in ({}, []):
                            del settings[key][key2]
                if settings[key] in ({}, []):
                    del settings[key]
            val = settings
        return fixups.base_to_dbus(val)

    @staticmethod
    def base_to_dbus(val):
        if isinstance(val, NMDbusInterface):
            return val.object_path
        if hasattr(val.__class__, 'mro'):
            for klass in val.__class__.mro():
                if klass.__module__ in ('dbus', '_dbus_bindings'):
                    return val
        if hasattr(val, '__iter__') and not isinstance(val, six.string_types):
            if hasattr(val, 'items'):
                return dict([(x, fixups.base_to_dbus(y)) for x, y in val.items()])
            else:
                return [fixups.base_to_dbus(x) for x in val]
        return val

    @staticmethod
    def to_python(klass, method, arg, val, signature):
        val = fixups.base_to_python(val)
        klass_af = {'IP4Config': socket.AF_INET, 'IP6Config': socket.AF_INET6}.get(klass, socket.AF_INET)
        if method == 'Get':
            if arg == 'Ip4Address':
                return fixups.addr_to_python(val, socket.AF_INET)
            if arg == 'Ip6Address':
                return fixups.addr_to_python(val, socket.AF_INET6)
            if arg == 'Ssid':
                return fixups.ssid_to_python(val)
            if arg == 'Strength':
                return fixups.strength_to_python(val)
            if arg == 'Addresses':
                return [fixups.addrconf_to_python(addr, klass_af) for addr in val]
            if arg == 'Routes':
                return [fixups.route_to_python(route, klass_af) for route in val]
            if arg in ('Nameservers', 'WinsServers'):
                return [fixups.addr_to_python(addr, klass_af) for addr in val]
            if arg == 'Options':
                for key in val:
                    if key.startswith('requested_'):
                        val[key] = bool(int(val[key]))
                    elif val[key].isdigit():
                        val[key] = int(val[key])
                    elif key in ('domain_name_servers', 'ntp_servers', 'routers'):
                        val[key] = val[key].split()

            return val
        if method == 'GetSettings':
            if 'ssid' in val.get('802-11-wireless', {}):
                val['802-11-wireless']['ssid'] = fixups.ssid_to_python(val['802-11-wireless']['ssid'])
            for key in val:
                val_ = val[key]
                if 'mac-address' in val_:
                    val_['mac-address'] = fixups.mac_to_python(val_['mac-address'])
                if 'cloned-mac-address' in val_:
                    val_['cloned-mac-address'] = fixups.mac_to_python(val_['cloned-mac-address'])
                if 'bssid' in val_:
                    val_['bssid'] = fixups.mac_to_python(val_['bssid'])
            if 'ipv4' in val:
                val['ipv4']['addresses'] = [fixups.addrconf_to_python(addr,socket.AF_INET) for addr in val['ipv4']['addresses']]
                val['ipv4']['routes'] = [fixups.route_to_python(route,socket.AF_INET) for route in val['ipv4']['routes']]
                val['ipv4']['dns'] = [fixups.addr_to_python(addr,socket.AF_INET) for addr in val['ipv4']['dns']]
            if 'ipv6' in val:
                val['ipv6']['addresses'] = [fixups.addrconf_to_python(addr,socket.AF_INET6) for addr in val['ipv6']['addresses']]
                val['ipv6']['routes'] = [fixups.route_to_python(route,socket.AF_INET6) for route in val['ipv6']['routes']]
                val['ipv6']['dns'] = [fixups.addr_to_python(addr,socket.AF_INET6) for addr in val['ipv6']['dns']]
            return val
        if method == 'PropertiesChanged':
            for prop in val:
                val[prop] = fixups.to_python(klass, 'Get', prop, val[prop], None)
        return val

    @staticmethod
    def base_to_python(val):
        if isinstance(val, dbus.ByteArray):
            return "".join([str(x) for x in val])
        if isinstance(val, (dbus.Array, list, tuple)):
            return [fixups.base_to_python(x) for x in val]
        if isinstance(val, (dbus.Dictionary, dict)):
            return dict([(fixups.base_to_python(x), fixups.base_to_python(y)) for x,y in val.items()])
        if isinstance(val, dbus.ObjectPath):
            for obj in (NetworkManager, Settings, AgentManager):
                if val == obj.object_path:
                    return obj
            if val.startswith('/org/freedesktop/NetworkManager/'):
                classname = val.split('/')[4]
                classname = {
                   'Settings': 'Connection',
                   'Devices': 'Device',
                }.get(classname, classname)
                return globals()[classname](val)
            if val == '/':
                return None
        if isinstance(val, (dbus.Signature, dbus.String)):
            return six.text_type(val)
        if isinstance(val, dbus.Boolean):
            return bool(val)
        if isinstance(val, (dbus.Int16, dbus.UInt16, dbus.Int32, dbus.UInt32, dbus.Int64, dbus.UInt64)):
            return int(val)
        if isinstance(val, dbus.Byte):
            return six.int2byte(int(val))
        return val

    @staticmethod
    def ssid_to_python(ssid):
        try:
            return bytes().join(ssid).decode('utf-8')
        except UnicodeDecodeError:
            ssid = bytes().join(ssid).decode('utf-8', 'replace')
            warnings.warn("Unable to decode ssid %s properly" % ssid, UnicodeWarning)
            return ssid

    @staticmethod
    def ssid_to_dbus(ssid):
        if isinstance(ssid, six.text_type):
            ssid = ssid.encode('utf-8')
        return [dbus.Byte(x) for x in ssid]

    @staticmethod
    def strength_to_python(strength):
        return struct.unpack('B', strength)[0]

    @staticmethod
    def mac_to_python(mac):
        return "%02X:%02X:%02X:%02X:%02X:%02X" % tuple([ord(x) for x in mac])

    @staticmethod
    def mac_to_dbus(mac):
        return [dbus.Byte(int(x, 16)) for x in mac.split(':')]

    @staticmethod
    def addrconf_to_python(addrconf,family):
        addr, netmask, gateway = addrconf
        return [
            fixups.addr_to_python(addr,family),
            netmask,
            fixups.addr_to_python(gateway,family)
        ]

    @staticmethod
    def addrconf_to_dbus(addrconf,family):
        addr, netmask, gateway = addrconf
        if (family == socket.AF_INET):
            return [
                fixups.addr_to_dbus(addr,family),
                fixups.mask_to_dbus(netmask),
                fixups.addr_to_dbus(gateway,family)
            ]
        else:
            return dbus.Struct(
                (
                    fixups.addr_to_dbus(addr,family),
                    fixups.mask_to_dbus(netmask),
                    fixups.addr_to_dbus(gateway,family)
                ), signature = 'ayuay'
            )

    @staticmethod
    def addr_to_python(addr,family):
        if (family == socket.AF_INET):
            return socket.inet_ntop(family,struct.pack('I', addr))
        else:
            return socket.inet_ntop(family,b''.join(addr))

    @staticmethod
    def addr_to_dbus(addr,family):
        if (family == socket.AF_INET):
            return dbus.UInt32(struct.unpack('I', socket.inet_pton(family,addr))[0])
        else:
            return dbus.ByteArray(socket.inet_pton(family,addr))

    @staticmethod
    def mask_to_dbus(mask):
        return dbus.UInt32(mask)

    @staticmethod
    def route_to_python(route,family):
        addr, netmask, gateway, metric = route
        return [
            fixups.addr_to_python(addr,family),
            netmask,
            fixups.addr_to_python(gateway,family),
            metric
        ]

    @staticmethod
    def route_to_dbus(route,family):
        addr, netmask, gateway, metric = route
        return [
            fixups.addr_to_dbus(addr,family),
            fixups.mask_to_dbus(netmask),
            fixups.addr_to_dbus(gateway,family),
            metric
        ]

    @staticmethod
    def cert_to_dbus(cert):
        if not isinstance(cert, bytes):
            if not cert.startswith('file://'):
                cert = 'file://' + cert
            cert = cert.encode('utf-8') + b'\0'
        return [dbus.Byte(x) for x in cert]

# Turn NetworkManager and Settings into singleton objects
NetworkManager = NetworkManager()
Settings = Settings()
AgentManager = AgentManager()
init_bus.close()
del init_bus
del xml_cache

# Constants below are generated with makeconstants.py. Do not edit manually.
NM_STATE_UNKNOWN = 0
NM_STATE_ASLEEP = 10
NM_STATE_DISCONNECTED = 20
NM_STATE_DISCONNECTING = 30
NM_STATE_CONNECTING = 40
NM_STATE_CONNECTED_LOCAL = 50
NM_STATE_CONNECTED_SITE = 60
NM_STATE_CONNECTED_GLOBAL = 70
NM_CONNECTIVITY_UNKNOWN = 0
NM_CONNECTIVITY_NONE = 1
NM_CONNECTIVITY_PORTAL = 2
NM_CONNECTIVITY_LIMITED = 3
NM_CONNECTIVITY_FULL = 4
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
NM_DEVICE_TYPE_BRIDGE = 13
NM_DEVICE_TYPE_GENERIC = 14
NM_DEVICE_TYPE_TEAM = 15
NM_DEVICE_TYPE_TUN = 16
NM_DEVICE_TYPE_IP_TUNNEL = 17
NM_DEVICE_TYPE_MACVLAN = 18
NM_DEVICE_TYPE_VXLAN = 19
NM_DEVICE_TYPE_VETH = 20
NM_DEVICE_CAP_NONE = 0
NM_DEVICE_CAP_NM_SUPPORTED = 1
NM_DEVICE_CAP_CARRIER_DETECT = 2
NM_DEVICE_CAP_IS_SOFTWARE = 4
NM_WIFI_DEVICE_CAP_NONE = 0
NM_WIFI_DEVICE_CAP_CIPHER_WEP40 = 1
NM_WIFI_DEVICE_CAP_CIPHER_WEP104 = 2
NM_WIFI_DEVICE_CAP_CIPHER_TKIP = 4
NM_WIFI_DEVICE_CAP_CIPHER_CCMP = 8
NM_WIFI_DEVICE_CAP_WPA = 16
NM_WIFI_DEVICE_CAP_RSN = 32
NM_WIFI_DEVICE_CAP_AP = 64
NM_WIFI_DEVICE_CAP_ADHOC = 128
NM_WIFI_DEVICE_CAP_FREQ_VALID = 256
NM_WIFI_DEVICE_CAP_FREQ_2GHZ = 512
NM_WIFI_DEVICE_CAP_FREQ_5GHZ = 1024
NM_WIFI_DEVICE_CAP_IBSS_RSN = 2048
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
NM_802_11_MODE_AP = 3
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
NM_DEVICE_STATE_REASON_MODEM_MANAGER_UNAVAILABLE = 52
NM_DEVICE_STATE_REASON_SSID_NOT_FOUND = 53
NM_DEVICE_STATE_REASON_SECONDARY_CONNECTION_FAILED = 54
NM_DEVICE_STATE_REASON_DCB_FCOE_FAILED = 55
NM_DEVICE_STATE_REASON_TEAMD_CONTROL_FAILED = 56
NM_DEVICE_STATE_REASON_MODEM_FAILED = 57
NM_DEVICE_STATE_REASON_MODEM_AVAILABLE = 58
NM_DEVICE_STATE_REASON_SIM_PIN_INCORRECT = 59
NM_DEVICE_STATE_REASON_NEW_ACTIVATION = 60
NM_DEVICE_STATE_REASON_PARENT_CHANGED = 61
NM_DEVICE_STATE_REASON_PARENT_MANAGED_CHANGED = 62
NM_DEVICE_STATE_REASON_LAST = 65535
NM_ACTIVE_CONNECTION_STATE_UNKNOWN = 0
NM_ACTIVE_CONNECTION_STATE_ACTIVATING = 1
NM_ACTIVE_CONNECTION_STATE_ACTIVATED = 2
NM_ACTIVE_CONNECTION_STATE_DEACTIVATING = 3
NM_ACTIVE_CONNECTION_STATE_DEACTIVATED = 4
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
NM_SECRET_AGENT_ERROR_NOT_AUTHORIZED = 0
NM_SECRET_AGENT_ERROR_INVALID_CONNECTION = 1
NM_SECRET_AGENT_ERROR_USER_CANCELED = 2
NM_SECRET_AGENT_ERROR_AGENT_CANCELED = 3
NM_SECRET_AGENT_ERROR_INTERNAL_ERROR = 4
NM_SECRET_AGENT_ERROR_NO_SECRETS = 5
