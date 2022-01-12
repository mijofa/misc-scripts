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
SYSTEMD_VPN_UNIT_PREFIX = 'nm-vpn-id@'
SYSTEMD_WIFI_UNIT_PREFIX = 'nm-wifi-ssid@'


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


def get_systemd_units(unit_type=None, unit_state=(), startswith=()):
    """Get systemd units with option filtering."""
    all_units = (systemd_unit_info(*u) for u in systemd1_manager.ListUnits())
    for unit in all_units:
        if unit_type and unit.name.rpartition('.')[-1] != unit_type:
            continue
        if unit_state and not any(s in (unit.load, unit.active, unit.sub) for s in unit_state):
            continue
        if startswith and not any((unit.name.startswith(prefix) for prefix in startswith)):
            continue
        yield unit


def bulk_update_systemd_targets(*connections):
    """Stop/start the necessary systemd targets for the given list of SSIDs."""
    systemd_unit_names = [u.name for u in get_systemd_units(unit_type=SYSTEMD_UNIT_TYPE,
                                                            unit_state=('active',),
                                                            startswith=(SYSTEMD_WIFI_UNIT_PREFIX, SYSTEMD_VPN_UNIT_PREFIX))]

    # Start any units that might need starting, and keep track of which ones got started
    needed_unit_names = []
    for conn in connections:
        if unit_name := update_target_for_connection(*conn):
            needed_unit_names.append(unit_name)

    # Stop the running units that should not be running
    for unit_name in systemd_unit_names:
        if unit_name not in needed_unit_names:
            print("Stopping unit", unit_name)
            systemd1_manager.StopUnit(unit_name, 'fail')


def update_target_for_connection(conn_type, conn_state, conn_id):
    """
    Start/stop the associated systemd unit for the given connection.

    NOTE: This doesn't care whether the unit is currently running or not,
          since systemd ensures nothing happens if I tell it to go to the state it's already in.
    """
    if conn_type in ('wireguard', 'vpn'):
        prefix = SYSTEMD_VPN_UNIT_PREFIX
    else:
        # FIXME: There's a type for this, use an elif for it, then raise NotImplementedError on else
        prefix = SYSTEMD_WIFI_UNIT_PREFIX

    unit_name = f'{prefix}{systemd_escape(conn_id)}.{SYSTEMD_UNIT_TYPE}'

    if conn_state in (NetworkManager.NM_ACTIVE_CONNECTION_STATE_ACTIVATING,
                      NetworkManager.NM_ACTIVE_CONNECTION_STATE_ACTIVATED):
        print("Starting unit", unit_name)
        systemd1_manager.StartUnit(unit_name, 'fail')
        return unit_name
    else:
        print("Stopping unit", unit_name)
        systemd1_manager.StopUnit(unit_name, 'fail')
        return False


def get_current_connections(active_connections=None):
    """
    Get the connection state of all currently active WiFi & VPN connections.

    Ignores any that it can't find the identifier.
    """
    if active_connections is None:
        active_connections = NetworkManager.NetworkManager.ActiveConnections

    for conn in active_connections:
        try:
            settings = conn.Connection.GetSettings()
            ssid = settings.get('802-11-wireless', {}).get('ssid')
            conn_id = settings.get('connection', {}).get('id')

            if ssid:
                yield (settings.get('connection', {}).get('type'), conn.State, ssid)
            elif 'vpn' in settings or 'wireguard' in settings:
                # Not a WiFi connection, maybe VPN though
                yield (settings.get('connection', {}).get('type'), conn.State, conn_id)
        except NetworkManager.ObjectVanished:
            # ActiveConnection disappeared while we were processing the info.
            # We can't do anything about it, so just ignore it
            pass


def on_properties_change(nm, interface, signal, properties):
    """Handle the OnStateChanged callback."""
    assert nm is NetworkManager.NetworkManager
    assert interface == 'org.freedesktop.NetworkManager'
    assert signal == 'PropertiesChanged'

    # I only care about this one property
    if properties.get('ActiveConnections'):
        bulk_update_systemd_targets(*get_current_connections(properties['ActiveConnections']))
    # if properties.get('ActivatingConnection'):
    #     print(get_current_connections([properties['ActivatingConnection']]))


NetworkManager.NetworkManager.OnPropertiesChanged(on_properties_change)
bulk_update_systemd_targets(*get_current_connections())
loop = GLib.MainLoop()


def cleanup(*args, **kwargs):
    """Cleanup our mess on exit."""
    bulk_update_systemd_targets()  # Easiest way to stop all units we control
    loop.quit()


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)
systemd.daemon.notify('READY=1')
try:
    loop.run()
except KeyboardInterrupt:
    systemd.daemon.notify('STOPPING=1')
    cleanup()
