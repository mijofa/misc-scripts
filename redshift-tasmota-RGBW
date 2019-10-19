#!/usr/bin/python3
import json
import math
import os
import subprocess
import sys
import time
import urllib.request

print("Updating temperature of lights", sys.argv, file=sys.stderr, flush=True)
# Redshift runs this *before* setting the gamma values in X11, so we need to fork and detach so that Redshift can continue,
# then wait ~3 seconds for Redshift to finish before querying X11
#
# Dual-fork technique adapted from: https://stackoverflow.com/questions/19369671/launching-a-daemon-from-python-then-detaching-the-parent-from-the-child
if os.fork() > 0:
    sys.exit()
os.setsid()
if os.fork() > 0:
    sys.exit()

time.sleep(4)

sonoff_hostname = 'sonoff-6810'


def get_randr_rgb_diff():
    xrandr_stdout = subprocess.check_output(['xrandr', '--verbose'], universal_newlines=True)

    found_gamma = False
    for line in xrandr_stdout.splitlines():
        if line.strip().startswith('Gamma:'):
            if found_gamma:
                raise NotImplementedError("Can't handle multiple gamma results")
            else:
                found_gamma = True
            # At this point line is something like this:
            # "\tGamma:       0.80:1.0:1.2\n"
            r, g, b = (1 - float(g) for g in line.replace(' ', '').split(':')[1:])

    # FIXME: Return a dict or named tuple
    return r, g, b


base_color_intensity = 160
red, green, blue = (math.floor(base_color_intensity + (base_color_intensity * c)) for c in get_randr_rgb_diff())
if red > 255 or green > 255 or blue > 255:
    raise NotImplementedError("Gamma value too high")

print(red, green, blue, file=sys.stderr, flush=True)

orig_power_state = json.load(urllib.request.urlopen(
    urllib.request.Request(f"http://{sonoff_hostname}/cm",
                           data=f"cmnd=Power".encode('ascii'))))
if orig_power_state.get('POWER', None) != 'OFF':
    ## FIXME: Set the colours but keep it off, so that when it turns on it gets the new colours.
    req = urllib.request.Request(f"http://{sonoff_hostname}/cm",
                                 data=f"cmnd=color {red},{green},{blue}".encode('ascii'))
    print(urllib.request.urlopen(req).read(), file=sys.stderr, flush=True)

