#!/usr/bin/python3
"""
Watch for monitor/screen output changes to trigger certain actins when needed.

Currently doesn't really know *what* changed, just that a change probably happened,
and it usually gets 3 repeate event triggers every time for some reason.
So whatever it triggers should be made idempotent.
"""
# Based on examples/xrandr.py from python3-xlib
# TODO: React to rotation changes by rotating the tablet too

import sys
# import pprint
import subprocess

import Xlib.X
import Xlib.display
import Xlib.ext.randr

# X11_rotation_to_wacom = {
#     Xlib.ext.randr.Rotate_0: 0,
#     Xlib.ext.randr.Rotate_90: 1,
#     Xlib.ext.randr.Rotate_180: 3,
#     Xlib.ext.randr.Rotate_270: 2,
# }


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

        # Mapping the window makes it visible.
        # We don't want that.
        # self.window.map()

    def map_wacoms_to_output(self, output_name, wacom_prefix='Wacom HID '):
        """Find all the wacom devices and map them to the specified output."""
        # FIXME: python3-xlib 0.29-1 does not seem to support xinput properties or mapping yet.
        #        Once it does, stop calling out to the xinput command and do it internally instead.
        if self.current_outputs[output_name]['crtc']:
            for input_device in self.d.xinput_query_device(Xlib.ext.xinput.AllDevices).devices:
                if input_device.name.startswith(wacom_prefix):
                    subprocess.check_call(['xinput', 'map-to-output', input_device.name, output_name])
                    print(f"* '{input_device.name}' mapped to '{output_name}'")
                    # I thought this was necessary, but it seems xinput automatically does this with the map-to-output
                    # subprocess.check_call(['xinput', 'set-prop', input_device.name, 'Wacom Rotation',
                    #                        str(X11_rotation_to_wacom[self.current_outputs[output_name]['crtc_info']['rotation']])])
        else:
            print(f"* {output_name} not connected, nothing to do")

    def update_current_outputs(self):
        """Populate self.current_outputs with the current state of all outputs."""
        self.current_outputs = {}
        for output in Xlib.ext.randr.get_screen_resources(self.screen.root).outputs:
            output_info = Xlib.ext.randr.get_output_info(self.screen.root, output, config_timestamp=0)._data
#            # FIXME: Current resolution is probably the most useful info, but it takes a bit of digging to get that info
#            #        Should we dig for that info here?
#            if output_info['crtc']:
#                output_info['crtc_info'] = self.d.xrandr_get_crtc_info(output_info['crtc'], config_timestamp=0)._data

            self.current_outputs[output_info['name']] = output_info

    def loop(self):
        """Wait for and handle the X11 events."""
        # FIXME: 'eDP-1' is the internal screen on my laptop. This should be made configurable.
        #        I expect it can't be automatically determined, but do that instead if possible.
        # FIXME: Same goes for the 'Wacom' string, and what happens if I happen to plug in a USB Wacom?

        # Gotta make sure it's all correct before things change just in case we logged in with multiple monitors
        self.update_current_outputs()
        self.map_wacoms_to_output(output_name='eDP-1', wacom_prefix='Wacom HID 5285 ')

        while 1:
            e = self.d.next_event()

            # Window has been destroyed, quit
            if e.type == Xlib.X.DestroyNotify:
                sys.exit(0)

            # Screen information has changed
            elif e.__class__.__name__ == Xlib.ext.randr.ScreenChangeNotify.__name__:
                print('RRScreenChangeNotify recieved.')
                # FIXME: Keep the previous event state and compare for some educated guesses on what the change was.
                #        Probably only useful for logging though
                # pprint.pprint(e._data)

                self.update_current_outputs()
                self.map_wacoms_to_output(output_name='eDP-1', wacom_prefix='Wacom HID 5285 ')

            # Somebody wants to tell us something
            # Probably an instruction from the WM
            elif e.type == Xlib.X.ClientMessage:
                if e.client_type == self.WM_PROTOCOLS:
                    fmt, data = e.data
                    if fmt == 32 and data[0] == self.WM_DELETE_WINDOW:
                        sys.exit(0)


if __name__ == '__main__':
    Window(Xlib.display.Display()).loop()
