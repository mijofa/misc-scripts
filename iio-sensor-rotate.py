#!/usr/bin/python3
"""
Auto-rotate the screen based on iio-sensor-proxy readings.
FIXME: monitor-sensor is just a DBUS client,
       figure that shit out and use DBUS directly
"""
import subprocess
import os

ROTATION_MAP = {
    'normal': 'normal',
    'bottom-up': 'inverted',
    'left-up': 'left',
    'right-up': 'right',
}

if __name__ == '__main__':
    if not 'DISPLAY' in os.environ:
        raise Exception("Need an X11 session to work with")

    monitor_sensor = subprocess.Popen(args=['monitor-sensor'],
                                      stdout=subprocess.PIPE,
                                      text=True)
    while line := monitor_sensor.stdout.readline():
        if line.strip().startswith('Accelerometer orientation changed: '):
            new_rotation = line.strip().rsplit(maxsplit=1)[-1]
            subprocess.check_output(args=['xrandr',
                                          '--output', 'eDP-1',
                                          '--rotation', ROTATION_MAP[new_rotation]])
        elif line.strip().startswith('=== Has accelerometer (orientation:'):
            init_rotation = line.strip().rsplit(maxsplit=1)[-1].strip(')')
            subprocess.check_output(args=['xrandr',
                                          '--output', 'eDP-1',
                                          '--rotation', ROTATION_MAP[init_rotation]])
