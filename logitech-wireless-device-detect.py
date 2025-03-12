"""
I have a number of wireless Logitech devices.
Some of which it would be nice to know when they turn on/off.

For example, I have a wireless keyboard I leave near the TV, if I turn that keyboard on it should switch to the TV.

This script uses Solaar (https://github.com/pwr-Solaar/Solaar) to monitor all Logitech wireless receivers and trigger certain systemd target units accordingly.
"""
import collections
import signal
import sys

import dbus
# Needed for the dbus mainloop
import dbus.mainloop.glib
from gi.repository import GLib
# I could theoretically do the D-Bus stuff myself,
# but this module should make things easier
# This module is only useful for running as a systemd unit to update the state of this unit,
# it doesn't help query systemd's unit status
import systemd.daemon
# I couldn't figure out how to make this module interact with the --user manager
# import pystemd

sys.path.append('/usr/share/solaar/lib')
import solaar.listener

SYSTEMD_UNIT_TYPE = 'target'
SYSTEMD_UNIT_PREFIX = 'logitech-wireless-device'

# FIXME: Use pydantic or dataclass
systemd_unit_info = collections.namedtuple('systemd_unit', field_names=[
    'name',              # The primary unit name as string
    'description',       # The human readable description string
    'load',              # The load state (i.e. whether the unit file has been loaded successfully)
    'active',            # The active state (i.e. whether the unit is currently started or not)
    'sub',               # The sub state (a more fine-grained version of the active state that is specific to the unit type,
                         #                which the active state is not)
    'following_unit',    # A unit that is being followed in its state by this unit, if there is any, otherwise the empty string.
    'unit_object_path',  # The unit object path
    'job_id',            # If there is a job queued for the job unit, the numeric job id, 0 otherwise
    'job_type',          # The job type as string
    'job_object_path'    # The job object path
])

dbus.mainloop.glib.threads_init()
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
session_bus = dbus.SessionBus()
systemd1 = session_bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
systemd1_manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')


def error_callback(*args, **kwargs):
    print("ERROR:", args, kwargs, file=sys.stderr, flush=True)


def status_changed_callback(device, alert=None, reason=None, **kwargs):
    # print('status_changed:', f'd={device.serial}', f'a={alert}', f'r={reason}', kwargs, flush=True)
    if not device.serial:
        # First few callbacks don't have a serial number yet, we can just ignore them
        return
    if not device.isDevice:
        # We don't care about the receivers, only the actual devices
        return
    if device.online:
        systemd1_manager.StartUnit(f'{SYSTEMD_UNIT_PREFIX}@{device.serial}.{SYSTEMD_UNIT_TYPE}', 'fail')
    else:
        systemd1_manager.StopUnit(f'{SYSTEMD_UNIT_PREFIX}@{device.serial}.{SYSTEMD_UNIT_TYPE}', 'fail')


loop = GLib.MainLoop()
solaar.listener.setup_scanner(status_changed_callback=status_changed_callback, error_callback=error_callback)
solaar.listener.start_all()


def cleanup(*args, **kwargs):
    # Stop the solaar threads
    solaar.listener.stop_all()
    # Stop the systemd units
    for unit in systemd1_manager.ListUnitsByPatterns([], [f'{SYSTEMD_UNIT_PREFIX}@*.{SYSTEMD_UNIT_TYPE}']):
        systemd1_manager.StopUnit(unit[0], 'fail')
    loop.quit()


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)
systemd.daemon.notify('READY=1')
try:
    loop.run()
except KeyboardInterrupt:
    systemd.daemon.notify('STOPPING=1')
    cleanup()
