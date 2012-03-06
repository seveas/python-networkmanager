Welcome to python-networkmanager's documentation!
=================================================

python-networkmanager wraps NetworkManagers D-Bus interface so you can be less
verbose when talking to NetworkManager from python. All interfaces have been
wrapped in classes, properties are exposed as python properties and function
calls are forwarded to the correct interface.

I wrote it to reduce a 100-line python script to 50 lines. Not realizing that
the library has more lines than the ones I removed. Oh well 😊

As of version 0.9.2, python-networkmanager also ships a command-line utility
called n-m, which allows you to manipulate NetworkManager's state from the
command line.

:mod:`NetworkManager` -- Easy communication with NetworkManager 
---------------------------------------------------------------
.. module:: NetworkManager
   :platform: Linux systems with NetworkManager 0.90
   :synopsis: Talk to NetworkManager without being verbose

All the code is contained in one module: :mod:`NetworkManager`. Using it is as
simple as you think it is:

.. code-block:: py

  >>> import NetworkManager
  >>> NetworkManager.NetworkManager.Version
  '0.9.1.90'

NetworkManager exposes a lot of information via D-Bus and also allows full
control of network settings. The full D-Bus API can be found on `NetworkManager
project website`_. All interfaces listed there have been wrapped in classes as
listed below.

.. class:: NMDbusInterface

This is the base class for all interface wrappers. It adds a few useful
features to standard D-Bus interfaces:

* All D-Bus properties are exposed as python properties
* Return values are automatically unwrapped (so no more :data:`dbus.String`)
* Object paths in return values are automatically replaced with proxy objects,
  so you don't need to do that manually 
* ...and vice versa when sending
* And also when receiving signals

.. function:: const(prefix, value)

Many of NetworkManagers D-Bus methods expect or return numeric constants, for
which there are enums in teh C sourece code only. These constants, such as
:data:`NM_STATE_CONNECTED_GLOBAL`, can all be found in the
:mod:`NetworkManager` module as well. The :func:`const` function can help you
translate them to text. For example:

.. code-block:: py

  >>> NetworkManager.const('state', 40)
  'connecting'
  >>> NetworkManager.const('device_type', 2)
  'wifi'

.. _`NetworkManager project website`: http://projects.gnome.org/NetworkManager/developers/migrating-to-09/spec.html

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

.. class:: Wimax

.. class:: OlpcMesh

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

These classes represent the various IP configuration interfaces.

.. class:: VPNConnection

This class represents the :data:`org.freedesktop.NetworkManager.VPN.Connection`
interface.

.. toctree::
   :maxdepth: 2

The n-m utility
---------------
n-m is a command-line tool to deal with network-manager. It can connect you to
defined networks and disconnect you again.

Usage: [options] action [arguments]

Actions:
  list       - List all defined and active connections
  activate   - Activate a connection
  deactivate - Deactivate a connection
  offline    - Deactivate all connections
  enable     - Enable specific connection types
  disable    - Disable specific connection types
  info       - Information about a connection
