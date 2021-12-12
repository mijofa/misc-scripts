#!/usr/bin/python3
"""
Watch for monitor/screen output changes to trigger certain actins when needed.

Currently doesn't really know *what* changed, just that a change probably happened,
and it usually gets 3 repeate event triggers every time for some reason.
So whatever it triggers should be made idempotent.
"""
# Based on examples/xrandr.py from python3-xlib
import sys
# import pprint
import subprocess

import Xlib.X
import Xlib.display
import Xlib.ext.randr

# Just for logging (for now) probably going to replace this with a 'rotation to transform matrix' mapping
rotation_labels = {
    Xlib.ext.randr.Rotate_0: "normal",
    Xlib.ext.randr.Rotate_90: "right",
    Xlib.ext.randr.Rotate_180: "inverted",
    Xlib.ext.randr.Rotate_270: "left",
}


def triggered_event_function():
    """Triggered when the RandR event occurs."""
    for wacom_device in "Wacom HID 5285 Pen stylus", "Wacom HID 5285 Pen eraser", "Wacom HID 5285 Finger touch":
        # FIXME: 'eDP-1' is the internal screen on my laptop. This should be made configurable.
        #        I expect it can't be automatically determined, but do that instead if possible
        subprocess.check_call(['xinput', 'map-to-output', wacom_device, 'eDP-1'])


# Application window (only one)
class Window(object):
    """Just a basic unmapped window so we can recieve events witohut actually showing a window to the user."""

    def __init__(self, display):  # noqa: D107
        self.d = display

        # Check that RandR is even supported before bothering with anything more
        if not self.d.has_extension('RANDR'):
            print(f'{sys.argv[0]}: server does not have the RANDR extension',
                  file=sys.stderr)
            ext = self.d.query_extension('RANDR')
            print(ext)
            print(*self.d.list_extensions(), sep='\n',
                  file=sys.stderr)
            if ext is None:
                sys.exit(1)

        # r = self.d.xrandr_query_version()
        # print('RANDR version %d.%d' % (r.major_version, r.minor_version))

        # Grab the current screen
        self.screen = self.d.screen()

        self.window = self.screen.root.create_window(
            # Xlib doesn't like these being 0
            1, 1, 1, 1, 1,
            self.screen.root_depth,
        )

        # The window never actually gets mapped, but let's set some info on it anyway, just in case
        self.window.set_wm_name('ScreenChangeNotify watcher')
        self.window.set_wm_class('xrandr', 'XlibExample')

        # Let the WM know that we can be instructed to quit (I think)
        self.WM_DELETE_WINDOW = self.d.intern_atom('WM_DELETE_WINDOW')
        self.window.set_wm_protocols([self.WM_DELETE_WINDOW])

        # Enable the one RandR event we're here for
        self.window.xrandr_select_input(Xlib.ext.randr.RRScreenChangeNotifyMask)

#        # Map the window, making it visible
#        #self.window.map()

    def loop(self):
        """Wait for and handle the X11 events."""
        while 1:
            e = self.d.next_event()

            # Window has been destroyed, quit
            if e.type == Xlib.X.DestroyNotify:
                sys.exit(0)

            # Screen information has changed
            elif e.__class__.__name__ == Xlib.ext.randr.ScreenChangeNotify.__name__:
                print('Screen change occured, calling trigger function')
                # FIXME: Keep the previous state and compare for some educated guesses on what the change was.
                #        Probably only useful for logging though
                # FIXME: This data mentions 'rotation', and it seems to match the internal display's rotation, but how?
                #        Why is it mentioned for just this display? Is the window perhaps on this display even though it's hidden?
#                pprint.pprint(e._data)
                print(f"Resolution: {e.width_in_pixels}x{e.height_in_pixels}    Rotation: {rotation_labels[e.rotation]}")
                triggered_event_function()

            # Somebody wants to tell us something
            # Probably an instruction from the WM
            elif e.type == Xlib.X.ClientMessage:
                if e.client_type == self.WM_PROTOCOLS:
                    fmt, data = e.data
                    if fmt == 32 and data[0] == self.WM_DELETE_WINDOW:
                        sys.exit(0)


if __name__ == '__main__':
    Window(Xlib.display.Display()).loop()
