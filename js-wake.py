#!/usr/bin/python3
import contextlib
import sys
import time

import Xlib.display

# evdev Not available in Debian's repos, must come from pip3
import evdev


VALVE_VENDOR_ID = '28DE'
_TIMEOUT = 10


def find_steam_controller():
    # FIXME: Just make this run asynchronously on *all* controllers?
    # FIXME: Run this from udev on every new JS device and get the path from udev arguments/environment.
    #        Stop forking out to xscreensaver-command first though.
    """Find all connected controllers manufactered by Valve.
    This is just a quick-and-dirty way to only watch the controller I actually care about"""
    controllers = []
    for dev_path in evdev.list_devices():
        with contextlib.closing(evdev.InputDevice(dev_path)) as dev:
            if dev.info.vendor == int(VALVE_VENDOR_ID, 16):
                controllers.append(dev.path)

    return controllers


def watch_controller(dev_path):
    XDisplay = Xlib.display.Display()
    try:
        with contextlib.closing(evdev.InputDevice(dev_path)) as js:
            print("Opened controller {vid:x}:{pid:x} {name}".format(vid=js.info.vendor, pid=js.info.product, name=js.name))
            last_nudge = 0
            for ev in js.read_loop():
                # FIXME: Set _TIMEOUT to half of whatever the current screensaver timeout is
                #        For some reason Xlib.display.Display().get_screen_saver().timeout always returns 0 though.
                if last_nudge + _TIMEOUT <= time.monotonic():  # Don't nudge any more often than every _TIMEOUT seconds
                    last_nudge = time.monotonic()
                    if ev.type in (evdev.ecodes.EV_KEY, evdev.ecodes.EV_ABS, evdev.ecodes.EV_REL):
                        print('.', end='', flush=True)
                        # FIXME: This only resets the screensaver if it's already active, it does not reset the timer.
                        XDisplay.force_screen_saver(Xlib.X.ScreenSaverReset)  # Nudge the screensaver
                    elif ev.type in (evdev.ecodes.EV_SYN, ):
                        # I expect EV_SYN often, but I want to ignore it
                        pass
                    else:
                        # This is mostly just belt-and-braces,
                        # if I don't see this ever trigger I'm going to throw this code-path away.
                        if ev.type in evdev.ecodes.EV:
                            ev_type = evdev.ecodes.EV[ev.type]
                        else:
                            ev_type = ev.type
                        raise NotImplementedError("Unrecognised event type: {}".format(ev_type))
    except OSError as e:
        if e.errno == 19:  # No such device
            print("Device is closed, cleaning up", file=sys.stderr)


if __name__ == '__main__':
    devices = find_steam_controller()
    if len(devices) > 1:
        raise NotImplementedError("Only support 1 Valve event device at a time")
    elif len(devices) < 1:
        raise FileNotFoundError("Can't find any Valve event devices")

    watch_controller(devices[0])
