#!/usr/bin/python3
"""
Shitty workaround for system not detecting when the wireless headphones are on/off.
"""
import asyncio
import json
import os
import pathlib
import socket
import subprocess
import sys
import time
import traceback
import typing

import evdev
import pyudev
import pulsectl

import gi
gi.require_version('Notify', '0.7')
gi.require_version('Gtk', '3.0')
from gi.repository import Notify  # noqa: E402 "module level import not at top of file"
from gi.repository import Gtk  # noqa: E402 "module level import not at top of file"


VENDOR_PRODUCT = (0x1b1c, 0x0a8f)
DEV_NAME = 'usb-Corsair_CORSAIR_HS55_Wireless_Gaming_Receiver_E215D7D1D48EBC02-00'
# This is the capabalities of the device we are looking for
CAPS = {
    evdev.ecodes.EV_SYN: [evdev.ecodes.SYN_REPORT, evdev.ecodes.SYN_CONFIG, 4],  # FIXME: I have no idea what 4 here actually maps to
    evdev.ecodes.EV_KEY: [evdev.ecodes.KEY_MUTE, evdev.ecodes.KEY_VOLUMEDOWN, evdev.ecodes.KEY_VOLUMEUP, evdev.ecodes.KEY_NEXTSONG, evdev.ecodes.KEY_PLAYPAUSE, evdev.ecodes.KEY_PREVIOUSSONG],
    evdev.ecodes.EV_MSC: [evdev.ecodes.MSC_SCAN]
}


def run_multiple(*args):
    """Run every arg as it's own function."""
    for f in args:
        f()


async def handle_events(dev):
    """Handle events for the given device."""
    print('Registering input device', dev.name)
    notif = Notify.Notification.new(f'{sys.argv[0]} - {dev.name}')
    notif.set_property('summary', 'Headset audio switcher')
    notif.set_timeout(2000)
    notif.set_property('body', 'Switching audio to headset')
    icon_theme = Gtk.IconTheme.get_default()
    notif.set_image_from_pixbuf(icon_theme.load_icon('audio-headphones', 64, 0))
    try:
        async for event in dev.async_read_loop():
            # Don't care what the event is, just change the default audio device

            # Don't actually care to use the card
            with pulsectl.Pulse(client_name=sys.argv[0]) as p:
                # pulsectl doesn't let me set a card as default.
                # pulsectl also doesn't let me get sinks/sources by card.
                # So I have to just assume the names are the same and hope for the best.
                # We also use '.startswith' because if a device gets replugged it can get an incrementing '.1' added to the end.

                # headset_card: pulse.PulseCardInfo, = (c for c in p.card_list() if c.name.startswith(f'alsa_card.{DEV_NAME}'))
                headset_sink, = (s for s in p.sink_list() if s.name.startswith(f'alsa_output.{DEV_NAME}'))
                headset_source, = (s for s in p.source_list() if s.name.startswith(f'alsa_input.{DEV_NAME}'))
                if p.server_info().default_sink_name != headset_sink.name:
                    notif.show()
                    p.default_set(headset_sink)
                if p.server_info().default_source_name != headset_source.name:
                    notif.show()
                    p.default_set(headset_source)
                notif.set_property('body', '')
    except OSError as e:
        if e.errno == 19:
            print("Looks like device was removed, stopping event handling")
        else:
            raise


# ref: https://github.com/pyudev/pyudev/issues/450#issuecomment-1078863332
async def iter_monitor_devices(context: pyudev.Context, **kwargs) -> typing.AsyncGenerator[pyudev.Device, None]:
    """Yield all udev devices and continue monitoring for device changes."""
    for device in context.list_devices(**kwargs):
        yield device

    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(**kwargs)
    monitor.start()
    fd = monitor.fileno()
    read_event = asyncio.Event()
    loop = asyncio.get_event_loop()
    loop.add_reader(fd, read_event.set)
    try:
        while True:
            await read_event.wait()
            while True:
                device = monitor.poll(0)
                if device is not None:
                    yield device
                else:
                    read_event.clear()
                    break
    finally:
        loop.remove_reader(fd)


async def main():
    """Initialize everything and run event loops for each input device as they appear."""
    Notify.init(sys.argv[0])

    udev_context = pyudev.Context()
    async for udev_dev in iter_monitor_devices(udev_context, subsystem='input'):
        if udev_dev.device_node and udev_dev.device_node in evdev.list_devices():
            evdev_dev = evdev.InputDevice(udev_dev.device_node)
            if (evdev_dev.info.vendor, evdev_dev.info.product) == VENDOR_PRODUCT and evdev_dev.capabilities() == CAPS:
                asyncio.ensure_future(handle_events(evdev_dev))
            # if is_device_capable(evdev_dev.capabilities(), GLOBAL_EVENT_MAPPING):
            #     asyncio.ensure_future(handle_events(evdev_dev, GLOBAL_EVENT_MAPPING))


if __name__ == '__main__':
    asyncio.run(main())
    # NOTE: I'm not explicitly closing the used evdev devices, but the garbage collector should take care of them.
