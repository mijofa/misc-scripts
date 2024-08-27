#!/usr/bin/python3
"""
Watch for changes to pulseaudio volumes and send a libnotify message accordingly.

NOTE: Depends on module-dbus-protocol being loaded into PulseAudio
"""
# import glob
import os
# import subprocess

import dbus
import dbus.mainloop.glib
import evdev

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
        # self.output_muted = bool(initial_fallback_sink.Get("org.PulseAudio.Core1.Device", "Mute"))
        # self.input_muted = bool(initial_fallback_source.Get("org.PulseAudio.Core1.Device", "Mute"))
        self._mute_update_handler(new_mute=initial_fallback_sink.Get("org.PulseAudio.Core1.Device", "Mute"),
                                  dev_path=self.pulse_core.Get("org.PulseAudio.Core1", "FallbackSink"))
        self._mute_update_handler(new_mute=initial_fallback_source.Get("org.PulseAudio.Core1.Device", "Mute"),
                                  dev_path=self.pulse_core.Get("org.PulseAudio.Core1", "FallbackSource"))

        # Recieve future updates of the mute state
        # FIXME: Also watch for Fallback updates, because we might switch from a muted device to an unmuted one,
        self.pulse_bus.add_signal_receiver(handler_function=self._mute_update_handler,
                                           signal_name='MuteUpdated', path_keyword='dev_path')

    def _mute_update_handler(self, new_mute, dev_path):
        """Handle mute state change by determining whether we even care about this device."""
        # Only do something if it's one of the default/fallback devices
        if dev_path == self.pulse_core.Get("org.PulseAudio.Core1", "FallbackSink"):
            self.output_muted = bool(new_mute)
            # self.set_mute_output(bool(new_mute))
        elif dev_path == self.pulse_core.Get("org.PulseAudio.Core1", "FallbackSource"):
            self.input_muted = bool(new_mute)
            # self.set_mute_input(bool(new_mute))
        else:
            print("Don't care about this device", dev_path, new_mute)

    def _mute_toggle(self, device_path):
        """Toggle mute state on the given device path."""
        device = self.pulse_bus.get_object("org.PulseAudio.Core1.Device",
                                           device_path)
        old_mute = bool(device.Get("org.PulseAudio.Core1.Device", "Mute"))
        device.Set("org.PulseAudio.Core1.Device", "Mute", dbus.Boolean(not old_mute, variant_level=1))

        self._mute_update_handler(new_mute=device.Get("org.PulseAudio.Core1.Device", "Mute"),
                                  dev_path=device_path)

    def mute_output_toggle(self):
        """Toggle mute state on the the current default output sink."""
        self._mute_toggle(self.pulse_core.Get("org.PulseAudio.Core1", "FallbackSink"))

    def mute_input_toggle(self):
        """Toggle mute state on the the current default input source."""
        self._mute_toggle(self.pulse_core.Get("org.PulseAudio.Core1", "FallbackSource"))


class KeyboardHandler(object):
    """Handle keyboard events for mute state hotkeys."""

    handler_timeout = None

    def __init__(self, dev_path, caps_mapping, pulse_handler):
        """Set up the device event loop if the capabilities match."""
        self.caps_mapping = caps_mapping
        self.pulse_handler = pulse_handler

        self.device = evdev.InputDevice(dev_path)

        if self._is_capable_of(caps_mapping):
            # Every 0.1 seconds is good enough
            self.handler_timeout = GLib.timeout_add(100, self._handle_events)
        else:
            self.device.close()

    def close(self):
        """Remove the timeouts from the main loop."""
        # FIXME: Does this even work?
        if self.handler_timeout:
            GLib.Source.remove(self.handler_timeout)

    def _is_capable_of(self, caps_mapping):
        """
        Compare device capabilities to the required capabilities mapping.

        This looks for any one capability,
        so if you're looking for both vol+ & vol-,
        but the device only has vol+ it will still return True.
        """
        dev_caps = self.device.capabilities()
        for cap_type in caps_mapping:
            if cap_type not in dev_caps.keys():
                continue
            for cap in caps_mapping[cap_type].keys():
                if cap in dev_caps.get(cap_type):
                    return True

        return False

    def _handle_events(self):
        """Handle whatever events are currently in the queue."""
        try:
            for event in self.device.read():
                if event.value == 2:
                    # Key repeat event, we don't care
                    continue
                mapped_cap = self.caps_mapping.get(event.type, {}).get(event.code, None)
                if event.value and mapped_cap:
                    mapped_cap()
        except BlockingIOError:
            # Just means there's nothing to read at the moment
            pass

        self.device.set_led(evdev.ecodes.LED_NUML, self.pulse_handler.output_muted)
        self.device.set_led(evdev.ecodes.LED_CAPSL, self.pulse_handler.input_muted)

        return True  # Needed to make GLib rerun the function on the next timeout


dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

pulse_handler = PulseHandler()

# FIXME: Make all the keyboard handling stuff disablable via command line arguments
caps_mapping = {evdev.ecodes.EV_LED: {evdev.ecodes.LED_NUML: None,
                                      evdev.ecodes.LED_CAPSL: None},
                evdev.ecodes.EV_KEY: {evdev.ecodes.KEY_NUMLOCK: pulse_handler.mute_output_toggle,
                                      evdev.ecodes.KEY_CAPSLOCK: pulse_handler.mute_input_toggle}}
dev_handlers = []
for dev_path in evdev.list_devices():
    dev_handlers.append(KeyboardHandler(dev_path, caps_mapping, pulse_handler))

GLib.MainLoop().run()
