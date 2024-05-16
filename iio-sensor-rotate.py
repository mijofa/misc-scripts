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

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib
from gi.repository import Gio

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

ROTATION_MAP = {
    'normal': 'normal',
    'bottom-up': 'inverted',
    'left-up': 'left',
    'right-up': 'right',
}


class RotationDaemon(dbus.service.Object):
    """Watch iio-sensor-proxy for accelerometer updates."""

    def __init__(self, main_loop: GLib.MainLoop):
        self.main_loop: GLib.MainLoop = main_loop
        # get buses
        self.bus = dbus.SystemBus()

        # subscribe to sensor
        self.sensor_proxy = self.bus.get_object('net.hadess.SensorProxy', '/net/hadess/SensorProxy')
        self.sensor_interface = dbus.Interface(self.sensor_proxy, dbus_interface='net.hadess.SensorProxy')
        self.sensor_interface.ClaimAccelerometer()
        self.sensor_proxy.connect_to_signal("PropertiesChanged", dbus_interface="org.freedesktop.DBus.Properties", handler_function=self.accelerometer_changed_handler)

    def accelerometer_changed_handler(self, _proxy, args, _signature):
        match args['AccelerometerOrientation']:
            case 'normal':
                x11_rotation = 'normal'
            case 'bottom-up':
                x11_rotation = 'inverted'
            case 'left-up':
                x11_rotation = 'left'
            case 'right-up':
                x11_rotation = 'right'
            case _:
                raise NotImplementedError(f"Unrecognised rotation value: {args['AccelerometerOrientation']}")
        
        self.x11_rotate(x11_rotation)

    def x11_rotate(self, rotation: str):
        return subprocess.check_call(args=['xrandr',
                                           '--output', 'eDP-1',
                                           '--rotation', rotation])


class SubprocDaemon():
    def __init__(self, args: list[str]):
        GLib.idle_add(self.run, args)

    def run(self, args: list[str]):
        self.cancellable = Gio.Cancellable()
        flags = Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE
        self.process = p = Gio.Subprocess.new(args, flags)
        p.wait_check_async(
            cancellable=self.cancellable,
            callback=self._on_finished
        )
        stream = p.get_stdout_pipe()
        self.data_stream = Gio.DataInputStream.new(stream)
        self.queue_read()

    def queue_read(self):
        self.data_stream.read_line_async(
            io_priority=GLib.PRIORITY_DEFAULT,
            cancellable=self.cancellable,
            callback=self._on_data
        )

    def cancel_read(self):
        self.cancellable.cancel()

    def _on_finished(self, proc, results):
        proc.wait_check_finish(results)
        self.cancel_read()

    def _on_data(self, source, result):
        line, length = source.read_line_finish_utf8(result)
        if line:
            event, _, __, state = line.split()
            if event == 'video/tabletmode':
                if int(state) == 0:
                    print('laptop mode')
                elif int(state) == 0:
                    print('tablet mode')
                else:
                    raise NotImplementedError(f"Unknown ACPI state for {event}: {state}")
        self.queue_read()

    def stop(self):
        self.process.send_signal(signal.SIGTERM)

    def kill(self):
        self.cancel_read()
        self.process.send_signal(signal.SIGKILL)



if __name__ == '__main__':
    if 'DISPLAY' not in os.environ:
        raise Exception("Need an X11 session to work with")

    loop = GLib.MainLoop()
    iio_daemon = RotationDaemon(main_loop=loop)
    # tablet_flap_daemon = SubprocDaemon(args=['acpi_listen'])
    loop.run()
