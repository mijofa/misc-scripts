#!/usr/bin/python3 -u
# FIXME: Turn this into a SteamPlay compatibility tool?
# FIXME: I'm getting "TypeError: Must be number, not NoneType" on startup,
#        but everything's working fine and I can't figure out what's causing that.
#        trace isn't working but I've somewhat narrowed down when it's happening [1],
#        however there's none of my code happening between those 2 points
import cairo
import signal
import sys

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio  # noqa: E204


class GLDrawArea(Gtk.GLArea):
    def __init__(self):
        super().__init__()
        self.connect("realize", self.on_realize)
        self.connect("render", self.on_render)

    def on_realize(self, area):
        # Initialise a GLX context so that Steam realises there's a game running
        ctx = self.get_context()
        ctx.make_current()

    def on_render(self, area, ctx):
        # Make sure we rendering something, even though the screen hasn't changed.
        # Because Steam's overlay doesn't handle rendering itself, it just injects draw calls in while this renders itself.
        # FIXME: Is there somewhere more efficient to put this?
        self.queue_render()


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Tell the compositor to use an alpha channel for this window, I think
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        # Set that alpha channel to transparent
        # NOTE: To my own surprise this does not actually stop Steam's overlay from rendering
        self.set_opacity(0.0)

        # Initialise a GLX context otherwise Steam's overlay won't inject itself
        self.area = GLDrawArea()
        self.add(self.area)

        self.connect("draw", self.on_draw)
        self.area.connect("render", self.on_render)

    def on_render(self, area, ctx):
        self.present()

    def on_draw(self, *args):
        # FIXME: This is running constantly, I only want it to run once after window is initialised
        # Tell the window manager to fullscreen this window

        # FIXME [1]: Before this
        self.fullscreen()
        # Tell the window manager to keep this window on every workspace
        self.stick()
        # Tell the window manager to keep this window on top
        self.set_keep_above(True)
        # I'm not sure whether the WM or X11 handles this, but make the window not accept focus
        self.set_accept_focus(False)

        # Tell the Window manager not to show it in the alt-tab menu or taskbar
        self.set_skip_taskbar_hint(True)
        # FIXME: This just don't seem to work
        self.set_skip_pager_hint(True)

        # Tell the compositor that mouse clicks anywhere on the window go through to what's behind it
        # NOTE: This can't be done before the window has been created
        # NOTE: Is there any problem with this happening before the window has been sized?
        self.input_shape_combine_region(cairo.Region(cairo.RectangleInt(0, 0, 1, 1)))


class App(Gtk.Application):
    def __init__(self):
        super().__init__(flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    def do_command_line(self, command_line):
        # Start the game itself
        self.game_proc = Gio.Subprocess.new(command_line.get_arguments()[1:], 0)
        # Handle when the game finishes
        self.game_proc.wait_check_async(callback=self.on_game_end)

        # FIXME: Should I instead be sending a signal to run this?
        self.do_activate()

    def do_activate(self):
        # Create the window for Steam to work with
        self.window = MainWindow(application=self)
        self.window.connect('delete-event', self.on_destroy)
        self.window.show_all()
        # FIXME [1]: After this

    def on_game_end(self, game_proc, results):
        # End this process when the game ends
        self.window.destroy()

    def on_destroy(self, *args):
        # Kill the game when this window gets closed
        self.game_proc.send_signal(signal.SIGTERM)


if __name__ == '__main__':
    sys.exit(App().run(sys.argv) or 0)
