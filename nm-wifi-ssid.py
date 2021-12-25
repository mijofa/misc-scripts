#!/usr/bin/python3
"""Start/stop sytemd user targets according to Network Manager's current WiFi SSID."""
import signal
import collections

import dbus
# Needed for the dbus mainloop
import dbus.mainloop.glib
from gi.repository import GLib
# I could theoretically do the D-Bus stuff myself,
# but this module should make things easier
import NetworkManager
# This module is only useful for running as a systemd unit to update the state of this unit,
# it doesn't help query systemd's unit status
import systemd.daemon
# I couldn't figure out how to make this module interact with the --user manager
# import pystemd

SYSTEMD_UNIT_TYPE = 'target'
SYSTEMD_UNIT_PREFIX = 'nm-wifi-ssid@'


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
    'job_objet_path'     # The job object path
])


dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
session_bus = dbus.SessionBus()
systemd1 = session_bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
systemd1_manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')


def systemd_escape(string_to_escape):
    """
    Escape unit names for use with systemd.

    Rough attempt to recreate systemd-escape in Python,
    but I couldn't make sense of the source code.
    So this is based on the test functions, and my own anecdotal usage
    """
    # r = unit_name_escape("ab+-c.a/bc@foo.service");
    # assert_se(r);
    # assert_se(streq(r, "ab\\x2b\\x2dc.a-bc\\x40foo.service"));
    assert isinstance(string_to_escape, str)
    escaped_string = []
    for c in string_to_escape:
        if c == '+':
            c = '\\x2b'
        elif c == '/':
            c = '-'
        # Must be careful where these are done
        elif c == '-':
            c = '\\x2d'
        elif c == '@':
            c = '\\x40'
        # Not mentioned in the test cases, but were needed
        elif c == ' ':
            c = '\\x20'
        elif c == '!':
            c = '\\x21'
        escaped_string.append(c)

    return ''.join(escaped_string)


def get_systemd_units(unit_type=None, unit_state=None, startswith=None):
    """Get systemd units with option filtering."""
    all_units = (systemd_unit_info(*u) for u in systemd1_manager.ListUnits())
    for unit in all_units:
        if unit_type and unit.name.rpartition('.')[-1] != unit_type:
            continue
        if unit_state and unit_state not in (unit.load, unit.active, unit.sub):
            continue
        if startswith and not unit.name.startswith(startswith):
            continue
        yield unit


def bulk_update_systemd_targets(SSIDs):
    """Stop/start the necessary systemd targets for the given list of SSIDs."""
    systemd_unit_names = [u.name for u in get_systemd_units(unit_type=SYSTEMD_UNIT_TYPE, startswith=SYSTEMD_UNIT_PREFIX)]
    escaped_SSIDs = [systemd_escape(ssid) for ssid in SSIDs]

    # Start the necessary units that are not already running
    for ssid in escaped_SSIDs:
        if f'{SYSTEMD_UNIT_PREFIX}{ssid}.{SYSTEMD_UNIT_TYPE}' not in systemd_unit_names:
            systemd1_manager.StartUnit(f'{SYSTEMD_UNIT_PREFIX}{systemd_escape(ssid)}.{SYSTEMD_UNIT_TYPE}', 'fail')

    # Stop the running units that should not be running
    for unit_name in systemd_unit_names:
        ssid = unit_name.partition('@')[2].rpartition('.')[0]
        if ssid not in escaped_SSIDs:
            systemd1_manager.StopUnit(unit_name, 'fail')


def get_current_SSIDs():
    """
    Get the connection state of all currently active SSIDs.

    Ignores all ActiveConnections without SSIDs.
    """
    for active_connection in NetworkManager.NetworkManager.ActiveConnections:
        try:
            ssid = active_connection.Connection.GetSettings().get('802-11-wireless', {}).get('ssid')
            if ssid:
                yield (active_connection.State, ssid)
        except NetworkManager.ObjectVanished:
            # ActiveConnection disappeared while we were processing the info.
            # We can't do anything about it, so just ignore it
            pass


def on_network_update(nm, interface, signal, state):
    """Handle the OnStateChanged callback."""
    assert nm is NetworkManager.NetworkManager
    assert interface == 'org.freedesktop.NetworkManager'
    assert signal == 'StateChanged'

    if state in (NetworkManager.NM_STATE_DISCONNECTING,
                 NetworkManager.NM_STATE_CONNECTED_LOCAL,
                 NetworkManager.NM_STATE_CONNECTED_SITE,
                 NetworkManager.NM_STATE_CONNECTED_GLOBAL):
        for connection_state, ssid in get_current_SSIDs():
            if connection_state == NetworkManager.NM_ACTIVE_CONNECTION_STATE_DEACTIVATING:
                systemd1_manager.StopUnit(f'{SYSTEMD_UNIT_PREFIX}{systemd_escape(ssid)}.{SYSTEMD_UNIT_TYPE}', 'fail')
            elif connection_state == NetworkManager.NM_ACTIVE_CONNECTION_STATE_ACTIVATED:
                systemd1_manager.StartUnit(f'{SYSTEMD_UNIT_PREFIX}{systemd_escape(ssid)}.{SYSTEMD_UNIT_TYPE}', 'fail')
            elif connection_state in (NetworkManager.NM_ACTIVE_CONNECTION_STATE_ACTIVATING,
                                      NetworkManager.NM_ACTIVE_CONNECTION_STATE_DEACTIVATED):
                # Don't care about these intermediary connecting state, nor the finished disconnecting state
                # NOTE: We use the the disconnecting state because it's the only time we can see what SSIDs are being disconnected
                # FIXME: I'm only ignoring these because there was what looked like race conditions that I don't understand
                pass
            else:
                raise NotImplementedError(f"Unknown NM_ACTIVE_CONNECTION_STATE {connection_state}")
    elif state in (NetworkManager.NM_STATE_CONNECTING,
                   NetworkManager.NM_STATE_DISCONNECTED):
        # Don't care about these intermediary connecting state, nor the finished disconnecting state
        # NOTE: We use the the disconnecting state because it's the only time we can see what SSIDs are being disconnected
        pass
    else:
        raise NotImplementedError(f"Unknown NM_STATE {state}")


NetworkManager.NetworkManager.OnStateChanged(on_network_update)
bulk_update_systemd_targets(
    (ssid for state, ssid in get_current_SSIDs() if state == NetworkManager.NM_ACTIVE_CONNECTION_STATE_ACTIVATED))
loop = GLib.MainLoop()


def cleanup(*args, **kwargs):
    """Cleanup our mess on exit."""
    bulk_update_systemd_targets([])  # Easiest way to stop all units we control
    loop.quit()


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)
systemd.daemon.notify('READY=1')
try:
    loop.run()
except KeyboardInterrupt:
    systemd.daemon.notify('STOPPING=1')
    cleanup()
