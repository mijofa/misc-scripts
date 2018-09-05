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
    root = dpy.screen().root
    # remote.c called this "kids" but I prefer "children" so I'm giving up on that particular consistency.
    # It's easier to see that children/child are 2 different variables than it is for kids/kid
    children = root.query_tree().children
    # remote.c had some extra error handling in case a child closed while iterating the list,
    # but I think python-xlib does that for me.
    for child in children:
        # remote.c used the equivalent of "get_property", but I don't understand the extra arguments that takes.
        status = child.get_full_property(XA_SCREENSAVER_VERSION, XA_STRING)
        # Only the screensaver windows has this property
        if status:
            # FIXME: Add some error handling for finding multiple screensaver windows?
            #        I don't think remote.c had that at all.
            return child
    # No screensaver window found
    return None


def send_xscreensaver_command(dpy, window, command, arg):
    # There's some whole thing in remote.c that sometimes sets arg1 to a magic number and makes arg2 = arg.
    # I dunno, I'm not using that functionality, but putting this here helps keep a little bit of consistency later.
    arg1 = arg
    arg2 = 0

    event = Xlib.protocol.event.ClientMessage(
        display=dpy,
        window=window,
        client_type=XA_SCREENSAVER,
        # In the C code the last [0, 0] happened implicitly, Python's xlib doesn't cope well with them being left out though.
        data=(32, [command, arg1, arg2, 0, 0]),
    )

    window.send_event(propagate=False,
                      event_mask=0,
                      event=event,
                      onerror=lambda err: print('ERROR:', err, file=sys.stderr, flush=True))


def xscreensaver_command_response(dpy, window):
    window.change_attributes(event_mask=Xlib.X.PropertyChangeMask)
    timeout = time.time() + 1
    while time.time() < timeout:
        if dpy.pending_events():
            ev = dpy.next_event()
            if ev.type == Xlib.X.PropertyNotify and \
               ev.state == Xlib.X.PropertyNewValue and \
               ev.atom == XA_SCREENSAVER_RESPONSE:
                    # NOTE: The C code accepts AnyPropertyType, not just Strings, I'm being more defensive here.
                    # FIXME: Can there be multiple responses all at once? Should we wait the whole second and add them all up?
                    response = window.get_full_property(XA_SCREENSAVER_RESPONSE, XA_STRING)
                    break
    assert response, "No response recieved"
    return response.value


def xscreensaver_command(dpy, command, arg):
    # FIXME: More of this should be run once on startup only.
    #        I only wrote it this way originally because I wanted it to closely match the C code for readability
    window = find_screensaver_window(dpy)
    assert window, "No screensaver window found"

    send_xscreensaver_command(dpy, window, command, arg)
    status = xscreensaver_command_response(dpy, window)
    # Add known messages to this list as they're noticed.
    if status not in ("+not active: idle timer reset.",):
        print('DEBUG, xscreensaver response:', status)


def deactivate_screensaver():
    # xscreensaver-command.c has these specified by the sys.argv[1:1]
    # but I'm hard-coding them because I only care to support DEACTIVATE, for now.
    cmd = XA_DEACTIVATE
    arg = 0
    xscreensaver_command(dpy, cmd, arg)


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


def watch_controller(dev_path):
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
    dpy = Xlib.display.Display()

    # These should really be considered constants, and set just after the imports,
    # but I can't set them until we have the display object, and we can't get a display object if not running in X11.
    # So I'm not quite sure where the line between logic, and preset constants sits with these.
    # FIXME: Note all the other Atom's that xscreensaver-command.c does just for completeness?
    XA_SCREENSAVER = dpy.intern_atom("SCREENSAVER", False)
    XA_SCREENSAVER_VERSION = dpy.intern_atom("_SCREENSAVER_VERSION", False)
    XA_SCREENSAVER_RESPONSE = dpy.intern_atom("_SCREENSAVER_RESPONSE", False)
    XA_DEACTIVATE = dpy.intern_atom("DEACTIVATE", False)
    XA_STRING = Xlib.Xatom.STRING  # Mostly just for consistency

    devices = find_steam_controller()
    if len(devices) > 1:
        raise NotImplementedError("Only support 1 Valve event device at a time")
    elif len(devices) < 1:
        raise FileNotFoundError("Can't find any Valve event devices")

    watch_controller(devices[0])
