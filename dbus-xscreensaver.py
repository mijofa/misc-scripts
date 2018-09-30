#!/usr/bin/env python2
# Replace light-locker DBus service to call xscreensaver, based on the scripts here:
# https://github.com/quequotion/pantheon-bzr-qq/tree/master/EXTRAS/xscreensaver-dbus-screenlock

# The reason I've targetted light-locker instead of gnome-screensaver is because
# * org.freedesktop.ScreenSaver seemed a little more "standard" than org.gnome.ScreenSaver
# * dbus-monitoring Chrome indicated it only targets org.freedesktop.ScreenSaver and that's the main thing I care about.

# FIXME: Currently this only allows controlling xscreensaver, and maybe some status querying.
#        It does NOT support telling DBus when Xscreensaver state updates
#
#        I would like to improve this in future to implement xscreensaver-command's -watch functionality
#        and emit DBus messages accordingly


# FIXME: Can gi.repository.DBus get the same functionality?
#        Should I use that to reduce dependencies?
import dbus
import dbus.service
import dbus.glib  # Needed for the mainloop to work with GObject
import random
from gi.repository import GObject


class DBusListener(dbus.service.Object):
    def __init__(self):
        session_bus = dbus.SessionBus()
        # FIXME: Also trigger for org.gnome.ScreenSaver
        bus_name = dbus.service.BusName("org.freedesktop.ScreenSaver", bus=session_bus)
        # FIXME: Also trigger for /org/gnome/ScreenSaver
        super().__init__(bus_name, '/org/freedesktop/ScreenSaver')

    @dbus.service.method("org.freedesktop.ScreenSaver")
    def GetActive(self):
        """Query the state of the locker"""
        # "grep" xscreenssaver-command -time for "non-blanked" and reverse the bool
        return dbus.Boolean(False)

    @dbus.service.method("org.freedesktop.ScreenSaver")
    def GetActiveTime(self):
        """Query the length of time the locker has been active"""
        # xscreenssaver-command -time
        pass

    @dbus.service.method("org.freedesktop.ScreenSaver")
    def GetSessionIdleTime(self):
        """Query the idle time of the locker"""
        # Doesn't have it's own dedicated light-locker-command argument,
        # but gets called instead of GetActiveTime when GetActive returns False

        # xscreenssaver-command -time ?
        pass

    @dbus.service.method("org.freedesktop.ScreenSaver")
    def Lock(self):
        """Tells the running locker process to lock the screen immediately"""
        # xscreenssaver-command -lock
        pass

    @dbus.service.method("org.freedesktop.ScreenSaver")
    def SetActive(self, activate):
        """Blank or unblank the screensaver"""
        # xscreensaver-command -deactivate or -activate
        return dbus.Boolean(True)  # NOTE: return True for success, not True for "activated"

    @dbus.service.method("org.freedesktop.ScreenSaver")
    def SimulateUserActivity(self):
        """Poke the running locker to simulate user activity"""
        # xscreensaver-command -activate
        pass

    @dbus.service.method("org.freedesktop.ScreenSaver")
    def Inhibit(self, caller, reason):
        """Inhibit the screensaver from activating. Terminate the light-locker-command process to end inhibition."""
        # This gets more complicated with a need to repeatedly "poke" xscreensaver because there is no inhibitor built into it.
        # NOTE: xdg-screensaver already has this working, perhaps just reuse that

        # NOTE: There's something calling itself "My SDL application" calling Inhibit every 20 seconds when there's user input,
        #       with the reason "Playing a game", then immediately calling UnInhibit if it was given an ID.
        #       It's Steam, I don't understand wtf it's doing since it should probably be calling SimulateUserActivity.
        #       I suspect when an actual game is running it won't UnInhibit, but I haven't investigated that.

        # Since DBus uses 32bit integers, make sure isn't any larger than that
        inhibitor_id = random.randint(0, 4294967296)
        print("Inhibit called by", caller, "for reason:", reason)
        return dbus.UInt32(inhibitor_id)

    @dbus.service.method("org.freedesktop.ScreenSaver")
    def UnInhibit(self, inhibitor_id):
        # Kill the inhibitor
        print("UnInhibit called for inhibitor", int(inhibitor_id))


if __name__ == '__main__':
    DBusListener()  # The object this returns is useless to us, it'll get dealt with by GObject
    GObject.MainLoop().run()
