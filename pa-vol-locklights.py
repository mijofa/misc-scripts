#!/usr/bin/python3
"""
Watch for changes to pulseaudio volumes and send a libnotify message accordingly.

NOTE: Depends on module-dbus-protocol being loaded into PulseAudio
"""
import glob
import os
import subprocess

import dbus
import dbus.mainloop.glib

from gi.repository import GLib


class PulseHandler(object):
    """Handle D-Bus signals from PulseAudio."""

    def _get_bus_address(self):
        """Get the PulseAudio D-Bus session address, either from environment or by asking the normal D-Bus session."""
        if 'PULSE_DBUS_SERVER' in os.environ:
            address = os.environ['PULSE_DBUS_SERVER']
        else:
            bus = dbus.SessionBus()
            server_lookup = bus.get_object("org.PulseAudio1", "/org/pulseaudio/server_lookup1")
            address = server_lookup.Get("org.PulseAudio.ServerLookup1", "Address",
                                        dbus_interface="org.freedesktop.DBus.Properties")
        return address

    def __init__(self):
        """Set up D-Bus listeners."""
        bus_address = self._get_bus_address()
        self.pulse_bus = dbus.connection.Connection(bus_address)
        self.pulse_core = self.pulse_bus.get_object(object_path='/org/pulseaudio/core1')
        self.pulse_core.ListenForSignal('org.PulseAudio.Core1.Device.MuteUpdated',
                                        dbus.Array(signature='o'),
                                        dbus_interface='org.PulseAudio.Core1')

        # Get the initial state of the current fallback devices
        initial_fallback_sink = self.pulse_bus.get_object("org.PulseAudio.Core1.Device",
                                                          self.pulse_core.Get("org.PulseAudio.Core1", "FallbackSink"))
        initial_fallback_source = self.pulse_bus.get_object("org.PulseAudio.Core1.Device",
                                                            self.pulse_core.Get("org.PulseAudio.Core1", "FallbackSource"))

        # Update notification of the initial state
        self.set_mute_output(initial_fallback_sink.Get("org.PulseAudio.Core1.Device", "Mute"))
        self.set_mute_input(initial_fallback_source.Get("org.PulseAudio.Core1.Device", "Mute"))

        # Recieve future updates of the mute state
        # FIXME: Also watch for Fallback updates, because we might switch from a muted device to an unmuted one,
        self.pulse_bus.add_signal_receiver(handler_function=self.mute_update, signal_name='MuteUpdated', path_keyword='dev_path')

    def mute_update(self, new_mute, dev_path):
        """Handle mute state change by determining whether we even care about this device."""
        # Only do something if it's one of the default/fallback devices
        if dev_path == self.pulse_core.Get("org.PulseAudio.Core1", "FallbackSink"):
            self.set_mute_output(bool(new_mute))
        elif dev_path == self.pulse_core.Get("org.PulseAudio.Core1", "FallbackSource"):
            self.set_mute_input(bool(new_mute))
        else:
            print("Don't care about this device", dev_path, new_mute)

    def set_mute_output(self, state):
        """Handle mute statuse change for the default output device."""
        # NOTE: check_call does not allow input=
        subprocess.check_output(['sudo', 'tee'] + glob.glob('/sys/class/leds/*::capslock/brightness'),
                                text=True, input=('1' if state else '0'))

    def set_mute_input(self, state):
        """Handle mute statuse change for the default input device."""
        # NOTE: check_call does not allow input=
        subprocess.check_output(['sudo', 'tee'] + glob.glob('/sys/class/leds/*::numlock/brightness'),
                                text=True, input=('1' if state else '0'))


dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

PulseHandler()
GLib.MainLoop().run()
