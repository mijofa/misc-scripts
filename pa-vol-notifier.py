#!/usr/bin/python3
"""
Watch for changes to pulseaudio volumes and send a libnotify message accordingly.

NOTE: Depends on module-dbus-protocol being loaded into PulseAudio
"""
import os
import sys

import dbus
import dbus.mainloop.glib

import gi
from gi.repository import GLib
# FIXME: I don't actually know what versions I require, I just picked the current ones at time of writing
gi.require_version('Notify', '0.7')
gi.require_version('Gtk', '3.0')
from gi.repository import Notify  # noqa: E402 "module level import not at top of file"
from gi.repository import Gtk  # noqa: E402 "module level import not at top of file"


ICON_SIZE = 64
NOTIFICATION_TIMEOUT = 2000  # Same as xfce4-pulseaudio-plugin


# FIXME: "Note that you probably want to listen for icon theme changes and update the icon"
icon_theme = Gtk.IconTheme.get_default()
icons = {
    'sink': {
        'muted': icon_theme.load_icon('notification-audio-volume-muted', ICON_SIZE, 0).copy(),
        'low': icon_theme.load_icon('notification-audio-volume-low', ICON_SIZE, 0).copy(),
        'medium': icon_theme.load_icon('notification-audio-volume-medium', ICON_SIZE, 0).copy(),
        'high': icon_theme.load_icon('notification-audio-volume-high', ICON_SIZE, 0).copy(),
    },
    'source': {
        'muted': icon_theme.load_icon('notification-microphone-sensitivity-muted', ICON_SIZE, 0).copy(),
        'low': icon_theme.load_icon('notification-microphone-sensitivity-low', ICON_SIZE, 0).copy(),
        'medium': icon_theme.load_icon('notification-microphone-sensitivity-medium', ICON_SIZE, 0).copy(),
        'high': icon_theme.load_icon('notification-microphone-sensitivity-high', ICON_SIZE, 0).copy(),
    },
}


class NotificationController(object):
    """Control the notification for volume & mute status."""

    def __init__(self, icons: dict):
        """Initialise the notification."""
        self.icons = icons

        self._notif = Notify.Notification.new("Volume status")
        self._notif.set_timeout(NOTIFICATION_TIMEOUT)

    def _set_icon(self, device_type, icon_name):
        self._notif.set_image_from_pixbuf(self.icons[icon_name])

    def _get_icon_name_for_volume(self, muted, vol_percentage):
        if muted:
            return 'muted'
        elif vol_percentage >= ((1 / 3) * 2):
            return 'high'
        elif vol_percentage >= (1 / 3):
            return 'medium'
        else:
            return 'low'

    def update(self, muted, vol_percentage):
        """Set the notification's volume & mute status, and reset the timeout."""
        self._set_icon('sink', self._get_icon_name_for_volume(muted, vol_percentage))
        self._notif.set_property('summary', f'Volume: {vol_percentage:.0%}')
        self._notif.set_property('body', 'MUTED' if muted else '')
        self._notif.set_hint('value', GLib.Variant.new_int32(vol_percentage * 100))

        self._notif.show()

    def close(self):
        """Close."""
        self._notif.close()


class DeviceHandler(object):
    """Handle device specific D-Bus signals from PulseAudio."""

    def __init__(self, pulse_bus, dev_path, notifier):
        """Set up the listeners."""
        self._path = dev_path

        self.device = pulse_bus.get_object("org.PulseAudio.Core1.Device", dev_path)

        # Is this even a device we should be monitoring
        if not bool(self.device.Get("org.PulseAudio.Core1.Device", "HasHardwareVolume")) and \
                not bool(self.device.Get("org.PulseAudio.Core1.Device", "HasHardwareMute")):
            # FIXME: This should probably raise an exception that gets handled
            self.device = None
            return None

        # Prepopulate the initial state
        self._MuteUpdated(self.device.Get("org.PulseAudio.Core1.Device", "Mute"), quiet=True)
        self._VolumeUpdated(self.device.Get("org.PulseAudio.Core1.Device", "Volume"), quiet=True)

        # Set up relevant event listeners
        # if bool(self.device.Get("org.PulseAudio.Core1.Device", "HasHardwareMute")):
        pulse_bus.add_signal_receiver(handler_function=self._MuteUpdated, signal_name='MuteUpdated', path=dev_path)
        # if bool(self.device.Get("org.PulseAudio.Core1.Device", "HasHardwareVolume")):
        pulse_bus.add_signal_receiver(handler_function=self._VolumeUpdated, signal_name='VolumeUpdated', path=dev_path)

#        self.notifier = NotificationController(icons[dev_type])
        self.notifier = notifier
        self.pulse_bus = pulse_bus

    def _MuteUpdated(self, new_mute, quiet=False):
        self._muted = bool(new_mute)

        if not quiet:
            self.notifier.update(muted=self._muted, vol_percentage=self._volume)

    def _VolumeUpdated(self, new_volumes, quiet=False):
        if len(new_volumes) > 1:
            # When we have multiple channels, just average the volume across each of them.
            vol = sum(new_volumes) / len(new_volumes)
        else:
            vol = new_volumes[0]
        self._volume = vol / 65536

        if not quiet:
            self.notifier.update(muted=self._muted, vol_percentage=self._volume)

    def close(self):
        """Close the device handler."""
        if self.device:
            self.pulse_bus.remove_signal_receiver(self._VolumeUpdated)
            self.pulse_bus.remove_signal_receiver(self._MuteUpdated)
#            self.notifier.close()


class PulseHandler(object):
    """Handle D-Bus signals from PulseAudio."""

    devices = {}

    def _get_bus_address(self):
        if 'PULSE_DBUS_SERVER' in os.environ:
            address = os.environ['PULSE_DBUS_SERVER']
        else:
            bus = dbus.SessionBus()
            server_lookup = bus.get_object("org.PulseAudio1", "/org/pulseaudio/server_lookup1")
            address = server_lookup.Get("org.PulseAudio.ServerLookup1", "Address",
                                        dbus_interface="org.freedesktop.DBus.Properties")
        return address

    def __init__(self, bus_address=None):
        """Set up D-Bus listeners."""
        if not bus_address:
            bus_address = self._get_bus_address()
        self.pulse_bus = dbus.connection.Connection(bus_address)
        pulse_core = self.pulse_bus.get_object(object_path='/org/pulseaudio/core1')
        for signal in ("NewSink", "SinkRemoved", "NewSource", "SourceRemoved", 'Device.MuteUpdated', 'Device.VolumeUpdated'):
            pulse_core.ListenForSignal(f'org.PulseAudio.Core1.{signal}',
                                       dbus.Array(signature='o'),
                                       dbus_interface='org.PulseAudio.Core1')

        self.input_notifier = NotificationController(icons['source'])
        self.output_notifier = NotificationController(icons['sink'])

        # Prepulate with the devices already connected
        for dev_path in pulse_core.Get("org.PulseAudio.Core1", "Sinks"):
            self.add_sink(dev_path)
            # self.devices[dev_path] = DeviceHandler(self.pulse_bus, dev_path, dev_type='sink')
        for dev_path in pulse_core.Get("org.PulseAudio.Core1", "Sources"):
            self.add_source(dev_path)  # DeviceHandler(self.pulse_bus, dev_path, dev_type='source')

        # FIXME: Add a signal handler for new sinks/sources, create new listeners for each
        #         def f(*args, **kwargs):
        #             print('device', args, kwargs)
        #         self.pulse_bus.add_signal_receiver(f, 'DeviceUpdated')

        # FIXME: Not working
        self.pulse_bus.add_signal_receiver(handler_function=self.add_sink, signal_name='NewSink')
        self.pulse_bus.add_signal_receiver(handler_function=self.add_source, signal_name='NewSource')
        self.pulse_bus.add_signal_receiver(handler_function=self.remove_device, signal_name='SinkRemoved')
        self.pulse_bus.add_signal_receiver(handler_function=self.remove_device, signal_name='SourceRemoved')

    def add_sink(self, sink_path):
        """Add new sink device handler."""
        print("Adding sink", sink_path)
        assert sink_path not in self.devices
        self.devices[sink_path] = DeviceHandler(self.pulse_bus, sink_path, notifier=self.output_notifier)

    def add_source(self, source_path):
        """Add new source device handler."""
        print("Adding source", source_path)
        assert source_path not in self.devices
        self.devices[source_path] = DeviceHandler(self.pulse_bus, source_path, notifier=self.input_notifier)

    def remove_device(self, dev_path):
        """Remove device handler."""
        print("Removing dev", dev_path)
        assert dev_path in self.devices
        self.devices.pop(dev_path).close()


dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
Notify.init(sys.argv[0])

pulse = PulseHandler()

GLib.MainLoop().run()
