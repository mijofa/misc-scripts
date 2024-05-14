#!/usr/bin/python3
"""
Auto-rotate the screen based on iio-sensor-proxy readings.

This works along with some acpi config to stop/start this service only when the laptop is folded back into "tablet" mode.

diff --git a/acpi/events/mijofa-tabletmode b/acpi/events/mijofa-tabletmode
new file mode 100644
index 0000000..1f45eb8
--- /dev/null
+++ b/acpi/events/mijofa-tabletmode
@@ -0,0 +1,3 @@
+# Written by mijofa to make the Thinkpad X1 Yoga actually do the Yoga thing
+event=video/tabletmode
+action=/etc/acpi/mijofa-tabletmode.sh %e
diff --git a/acpi/mijofa-tabletmode.sh b/acpi/mijofa-tabletmode.sh
new file mode 100755
index 0000000..db6b5bd
--- /dev/null
+++ b/acpi/mijofa-tabletmode.sh
@@ -0,0 +1,23 @@
+#!/bin/bash
+# I copied some of this from lid.sh since it should be doing similar-ish X11 stuff
+exec &>>/tmp/tabletmode.out
+set -x
+echo "$(date) $@"
+
+# # FIXME: This here should be able to set the XUSER/XAUTHORITY/XRANDR_OUTPUT vars automatically,
+#          but it's taking ages to complete, so I'm just making some assumptions for now.
+# test -f /usr/share/acpi-support/power-funcs || exit 0
+# . /usr/share/acpi-support/power-funcs
+# getXuser
+
+# This laptop belongs to Mike, no one else is going to be using it
+XUSER="mike"
+
+if [ "$4" -eq 0 ] ; then
+    su "$XUSER" -s /bin/sh -c "systemctl --user stop iio-sensor-rotate.service"
+elif [ "$4" -eq 1 ] ; then
+    su "$XUSER" -s /bin/sh -c "systemctl --user start iio-sensor-rotate.service"
+else
+    echo "$0: Invalid value, stopping unit and bailing out" >&2
+    exit 2
+fi
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
    if 'DISPLAY' not in os.environ:
        raise Exception("Need an X11 session to work with")

    # FIXME: monitor-sensor is just a DBUS client,
    #        figure that shit out and use DBUS directly
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
            if init_rotation == 'undefined':
                # Sometimes (most of the time) it takes a moment after initialisation for the accelerometer to provide useful info
                continue
            subprocess.check_output(args=['xrandr',
                                          '--output', 'eDP-1',
                                          '--rotation', ROTATION_MAP[init_rotation]])
