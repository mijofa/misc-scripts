#!/usr/bin/python3
import json
import math
import os
import subprocess
import sys
import time
import urllib.request

import psutil

# FIXME: Config or cmdline switch this
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


# Thrown behind an if statement because testing & debugging was getting annoying with this
if psutil.Process(psutil.Process().ppid()).cmdline()[0].endswith('redshift'):
    # Redshift eats stdout, but I want some logging via the systemd journal so use stderr instead
    output_file = sys.stderr
    print("Forking light controller", sys.argv, file=output_file)

    # Redshift runs this *before* setting the gamma values in X11, so we need to fork and detach so that Redshift can continue,
    # then wait ~3 seconds for Redshift to finish before querying X11
    # Dual-fork technique adapted from:
    #     https://stackoverflow.com/questions/19369671/launching-a-daemon-from-python-then-detaching-the-parent-from-the-child
    if os.fork() > 0:
        sys.exit()
    os.setsid()
    if os.fork() > 0:
        sys.exit()
    time.sleep(4)
else:
    output_file = sys.stdout

base_color_intensity = 255 / 2
red, green, blue = (
    # Constrain the results between 0 & 255
    max(0, min(255,
               # Apply the percentage to our base colour
               math.floor(base_color_intensity + (base_color_intensity * c)))
        ) for c in get_randr_rgb_diff())
if red > 255 or green > 255 or blue > 255:
    raise NotImplementedError(f"Gamma value {red}:{green}:{blue} too high")
white = math.floor(base_color_intensity / 2)

command = f"Color2 {red},{green},{blue},{white}"
print("Sending command to tastmota:", command, file=output_file)

# NOTE: Tasmota has been told not to power the globe on when setting the color via the SetOption20 config command
# NOTE: "Color2" = Set color adjusted to current Dimmer value
req = urllib.request.Request(f"http://{sonoff_hostname}/cm",
                             data=f"cmnd={command}".encode('ascii'))
print(json.load(urllib.request.urlopen(req)), file=output_file)
