#!/usr/bin/python3
from Xlib import X, display
from Xlib.ext import record
from Xlib.protocol import rq
import subprocess

# The media keys don't have string names, so have to just hardcode the keysyms
VOLDOWN = 269025041
VOLUP = 269025043
VOLMUTE = 269025042


def processevents(dpy, reply):
    # I don't understand why all these IFs are here, I stole it from:
    # https://github.com/chrisspen/freekey/blob/master/freekey/pyxhook.py
    if reply.category != record.FromServer:
        return
    if reply.client_swapped:
        return
#    if not len(reply.data) or ord(reply.data[0]) < 2: return

    data = reply.data
    if len(data):
        (event, _) = rq.EventField(None).parse_binary_value(data, dpy.display, None, None)
        if event.type == X.KeyPress:
            keysym = dpy.keycode_to_keysym(event.detail, 0)
            if keysym in (VOLDOWN, VOLUP, VOLMUTE):
                if keysym == VOLDOWN:
                    change = -0.05
                if keysym == VOLUP:
                    change = 0.05
                if keysym == VOLMUTE:
                    change = None
                subprocess.check_output([
                    'pactl', '--',
                    'set-sink-{}'.format('volume' if change else 'mute'),
                    # NOTE: This could result in an argument of '+-0.5%' but they cancel sufficiently
                    '0', '+{0:.0%}'.format(change) if change else 'toggle'
                ])


dpy = display.Display()
assert dpy.has_extension("RECORD")

ctx = dpy.record_create_context(0, [record.AllClients], [{
    'core_requests': (0, 0),
    'core_replies': (0, 0),
    'ext_requests': (0, 0, 0, 0),
    'ext_replies': (0, 0, 0, 0),
    'delivered_events': (0, 0),
    'device_events': (X.KeyPress, X.MotionNotify),
    'errors': (0, 0),
    'client_started': False,
    'client_died': False
}])
dpy.record_enable_context(ctx, lambda r: processevents(dpy, r))
