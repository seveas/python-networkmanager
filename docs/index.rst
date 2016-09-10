Python API to talk to NetworkManager
====================================

NetworkManager provides a detailed and capable D-Bus interface on the system
bus. You can use this interface to query NetworkManager about the overall state
of the network and details of network devices like current IP addresses or DHCP
options, and to configure, activate and deactivate network connections.

python-networkmanager takes this D-Bus interface and wraps D-Bus interfaces in
classes and D-Bus methods and properties in their python equivalents.

The :mod:`NetworkManager` module
--------------------------------
.. module:: NetworkManager
   :platform: Linux systems with NetworkManager 0.9 and newer
   :synopsis: Talk to NetworkManager from python

All the code is contained in one module: :mod:`NetworkManager`. Using it is as
simple as you think it is:

.. code-block:: py

  >>> import NetworkManager
  >>> NetworkManager.NetworkManager.Version
  '1.2.0'

NetworkManager exposes a lot of information via D-Bus and also allows full
control of network settings. The full D-Bus interface can be found on
`NetworkManager project website`_. All interfaces listed there have been
wrapped in classes as listed below. With a few exceptions, they behave exactly
like the D-Bus methods. These exceptions are for convenience and limited to
this list:

* IP addresses are returned as strings of the form :data:`1.2.3.4` instead of
  network byte ordered integers.
* Route metrics are returned in host byte order, so you can use them as
  integers.
* Mac addresses and BSSIDs are always returned as strings of the form
  :data:`00:11:22:33:44:55` instead of byte sequences.
* Wireless SSID's are returned as strings instead of byte sequences. They will
  be decoded as UTF-8 data, so using any other encoding for your SSID will
  result in errors.
* DHCP options are turned into integers or booleans as appropriate

.. function:: const(prefix, value)

Many of NetworkManagers D-Bus methods expect or return numeric constants, for
which there are enums in the C source code. These constants, such as
:data:`NM_STATE_CONNECTED_GLOBAL`, can all be found in the
:mod:`NetworkManager` module as well. The :func:`const` function can help you
translate them to text. For example:

.. code-block:: py

  >>> NetworkManager.const('state', 40)
  'connecting'
  >>> NetworkManager.const('device_type', 2)
  'wifi'

.. _`NetworkManager project website`: https://developer.gnome.org/NetworkManager/1.2/spec.html

List of classes
---------------

.. class:: NetworkManager

The main `NetworkManager
<https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.html>`_
object; the `NetworkManager.Networkmanager` object is actually the singleton
instance of this class.

.. class:: Settings

The `Settings
<https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Settings.html>`_
object, which can be used to add connections, list connections or update your
hostname; the `NetworkManager.Settings` object is actually the singleton
instance of this class.

.. class:: AgentManager

The `AgentManager
<https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.AgentManager.html>`_
object, whose methods you'll need to call when implementing a secrets agent;
the `NetworkManager.AgentManager` object is actually the singleton instance of
this class.

.. class:: Connection

`Connection
<https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Settings.Connection.html>`_
objects represent network configurations configured by the user.

.. class:: ActiveConnection
.. class:: VPNConnection

Active connections are represented by `ActiveConnection
<https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Connection.Active.html>`_
objects. `VPNConnection
<https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.VPN.Connection.html>`_
is a subclass for active VPN connection that implements both the
Connection.Active and VPN.Connection interfaces.

.. class:: IP4Config
.. class:: IP6Config
.. class:: DHCP4Config
.. class:: DHCP6Config

Active network connections and devices can all have `IPv4
<https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.IP4Config.html>`_,
`IPv6
<https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.IP6Config.html>`_,
`IPv4 DHCP
<https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.DHCP4Config.html>`_
and `IPv6 DHCP
<https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.DHCP6Config.html>`_
information attached to them, which is represented by instances of these
classes.

.. class:: AccessPoint

Wifi `Accesspoints
<https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.AccessPoint.html>`_,
as visibly by any 802.11 wifi interface.

.. class:: NSP

Wimax `Network Service Providers <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.PPP.html>`_.

.. class:: Device

All device classes implement the `Device
<https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.html>`_
interface, which gives you access to basic device properties. Note that you will never see instances of this class, only of its devicetype-specific subclasses which impletemnt not only the Device interface but also their own specific interface. Supported device types are 
`Adsl <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Adsl.html>`_, 
`Bluetooth <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Bluetooth.html>`_, 
`Bond <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Bond.html>`_, 
`Bridge <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Bridge.html>`_, 
`Generic <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Generic.html>`_, 
`Infiniband <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Infiniband.html>`_, 
`IPTunnel <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.IPTunnel.html>`_, 
`Macvlan <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Macvlan.html>`_, 
`Modem <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Modem.html>`_, 
`OlpcMesh <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.OlpcMesh.html>`_, 
`Team <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Team.html>`_, 
`Tun <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Tun.html>`_, 
`Veth <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Veth.html>`_, 
`Vlan <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Vlan.html>`_, 
`Vxlan <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Vxlan.html>`_, 
`Wimax <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Wimax.html>`_, 
`Wired <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Wired.html>`_ and
`Wireless <https://developer.gnome.org/NetworkManager/1.2/gdbus-org.freedesktop.NetworkManager.Device.Wireless.html>`_

.. toctree::
   :maxdepth: 2
