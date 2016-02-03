Python API to talk to NetworkManager
====================================

NetworkManager provides a detailed and capable D-Bus interface on the system
bus. You can use this interface to query NetworkManager about the overall state
of the network and details of network devices like current IP addresses or DHCP
options, and to activate and deactivate network connections.

python-networkmanager takes this D-Bus interface and wraps D-Bus interfaces in
classes and D-Bus properties in python properties. It also provides a
command-line utility to inspect the configuration and (de-)activate
connections.

The :mod:`NetworkManager` module
--------------------------------
.. module:: NetworkManager
   :platform: Linux systems with NetworkManager 0.9 and 1.0
   :synopsis: Talk to NetworkManager from python

All the code is contained in one module: :mod:`NetworkManager`. Using it is as
simple as you think it is:

.. code-block:: py

  >>> import NetworkManager
  >>> NetworkManager.NetworkManager.Version
  '1.0.4'

NetworkManager exposes a lot of information via D-Bus and also allows full
control of network settings. The full D-Bus API can be found on `NetworkManager
project website`_. All interfaces listed there have been wrapped in classes as
listed below. With a few exceptions, they behave exactly like the D-Bus
methods. These exceptions are for convenience and limited to this list:

* IP addresses are returned as strings of the form :data:`1.2.3.4` instead of
  network byte ordered integers.
* Route metrics are returned in host byte order, so you can use them as
  integers.
* Mac addresses and BSSIDs are always returned as strings of the form
  :data:`00:11:22:33:44:55` instead of byte sequences.
* Wireless SSID's are returned as strings instead of byte sequences. They will
  be decoded as UTF-8 data, so using any other encoding for your SSID will
  result in errors.

.. class:: NMDbusInterface

This is the base class for all interface wrappers. It adds a few useful
features to standard D-Bus interfaces:

* All D-Bus properties are exposed as python properties
* Return values are automatically converted to python basic types (so no more
  :data:`dbus.String`, but simple :data:`str` (python 3) or :data:`unicode`
  (python 2))
* Object paths in return values are automatically replaced with proxy objects,
  so you don't need to do that manually
* ...and vice versa when sending
* And also when receiving signals

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

.. _`NetworkManager project website`: https://developer.gnome.org/NetworkManager/0.9/spec.html

List of classes
---------------

.. class:: NetworkManager

This class represents the :data:`org.freedesktop.NetworkManager` interface.
Note that :data:`NetworkManager.NetworkManager` actually is the singleton
instance of this class.

.. class:: Settings

This class represents the :data:`org.freedesktop.NetworkManager.Settings`
interface.  Note that :data:`NetworkManager.Settings` actually is the singleton
instance of this class.

.. class:: Connection

This class represents the
:data:`org.freedesktop.NetworkManager.Settings.Connection` interface.

.. class:: ActiveConnection

This class represents the
:data:`org.freedesktop.NetworkManager.Connection.Active` interface.

.. class:: AccessPoint

This class represents the :data:`org.freedesktop.NetworkManager.AccessPoint`
interface.

.. class:: Device

.. class:: Wired

.. class:: Wireless

.. class:: Modem

.. class:: Bluetooth

.. class:: OlpcMesh

.. class:: Wimax

.. class:: Infiniband

.. class:: Bond

.. class:: Bridge

.. class:: Vlan

.. class:: Adsl

.. class:: Generic

These classes represent D-Bus interfaces for various types of hardware. Note
that methods such as :data:`NetworkManager.GetDevices()` will only return
:class:`Device` instances. To get the hardware-specific class, you can call the
:func:`Device.SpecificDevice` method.

.. code-block:: py

    >>> [(dev.Interface, dev.SpecificDevice().__class__.__name__)
    ...  for dev in NetworkManager.NetworkManager.GetDevices()]
    [('eth0', 'Wired'), ('wlan0', 'Wireless'), ('wwan0', 'Modem')]

.. class:: IP4Config

.. class:: IP6Config

.. class:: DHCP4Config

.. class:: DHCP6Config

These classes represent the various IP configuration interfaces.

.. class:: AgentManager

.. class:: SecretAgent

Classes that can be used to handle and store secrets. Note that these are not
for querying NetworkManager's exisiting secret stores. For that the
:func:`GetSecrets` method of the :class:`Connection` class can be used.

.. class:: VPNConnection

This class represents the :data:`org.freedesktop.NetworkManager.VPN.Connection`
interface.

.. class:: VPNPlugin

A class that can be used to query VPN plugins.

.. toctree::
   :maxdepth: 2
