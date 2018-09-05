#!/usr/bin/python3
import contextlib
import sys
import time

import Xlib.Xatom
import Xlib.display
import Xlib.protocol

# evdev Not available in Debian's repos, must come from pip3
import evdev


VALVE_VENDOR_ID = '28DE'
_TIMEOUT = 10


### Xscreensaver functions ###
def find_screensaver_window(dpy):
    screensavers = [child for child in dpy.screen().root.query_tree().children
                    if child.get_full_property(dpy.intern_atom("_SCREENSAVER_VERSION", False), Xlib.Xatom.STRING)]
    # FIXME: Use actual exceptions
    assert not len(screensavers) > 1, "Can't have multiple screensaver windows!"
    assert not len(screensavers) < 1, "No screensaver window found. Is there a screensaver running?"
    # We don't want actually want a list, it was just the easiest way to loop over the query_tree
    return screensavers[0]


def send_xscreensaver_deactivate(window):
    # FIXME: Set this event object once at start up and re-use it.
    event = Xlib.protocol.event.ClientMessage(
        display=dpy,
        window=window,
        client_type=dpy.intern_atom("SCREENSAVER", False),
        # In the C code the last [0, 0] happened implicitly, Python's xlib doesn't cope well with them being left out though.
        # The first [0, 0] was set according to certain other arguments, but for DEACTIVATE was always [0, 0]
        data=(32, [dpy.intern_atom("DEACTIVATE", False), 0, 0, 0, 0]),
    )

    window.send_event(propagate=False,
                      event_mask=0,
                      event=event,
                      onerror=lambda err: print('ERROR:', err, file=sys.stderr, flush=True))


def xscreensaver_response(window):
    window.change_attributes(event_mask=Xlib.X.PropertyChangeMask)
    timeout = time.time() + 1
    while time.time() < timeout:
        if dpy.pending_events():
            ev = dpy.next_event()
            if ev.type == Xlib.X.PropertyNotify and \
               ev.state == Xlib.X.PropertyNewValue and \
               ev.atom == dpy.intern_atom("_SCREENSAVER_RESPONSE", False):
                    # NOTE: The C code accepts AnyPropertyType, not just Strings, I'm being more defensive here.
                    # FIXME: Can there be multiple responses all at once? Should we wait the whole second and add them all up?
                    # FIXME: Can I just get the property info from the event object?
                    response = window.get_full_property(dpy.intern_atom("_SCREENSAVER_RESPONSE", False), Xlib.Xatom.STRING)
                    break
    assert response, "No response recieved"
    return response.value


def deactivate_screensaver():
    window = find_screensaver_window(dpy)

    send_xscreensaver_deactivate(window)
    response = xscreensaver_response(dpy, window)
    # I don't currently know what's an error and what's not, so add known messages to this list as they're seen.
    # FIXME: Do we even get error responses via this method? If not, stop even checking and wasting resources
    if response not in ("+not active: idle timer reset.",):
        print('DEBUG, xscreensaver response:', response)


### evdev functions ###
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


def watcher(dev_path):
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
                        deactivate_screensaver()
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
    global dpy
    dpy = Xlib.display.Display()

    # FIXME: Take some sort of identifier on the command line, perhaps allow for triggering via udev (perhaps via os.environ)
    #        If using a command-line identifier (not udev) also add the option to wait for the device with a timeout
    # FIXME: Or, use asyncio and handle all currently connected controllers concurrently
    #        NOTE: Would it only handle the ones connected on start up or could it also wait for new devices?
    devices = find_steam_controller()
    if len(devices) > 1:
        raise NotImplementedError("Only support 1 Valve event device at a time")
    elif len(devices) < 1:
        raise FileNotFoundError("Can't find any Valve event devices")

    watcher(devices[0])
