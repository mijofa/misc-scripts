#!/usr/bin/env python3
# Replace light-locker DBus service to call xscreensaver, based on the scripts here:
# https://github.com/quequotion/pantheon-bzr-qq/tree/master/EXTRAS/xscreensaver-dbus-screenlock

# The reason I've targetted light-locker instead of gnome-screensaver is because
# * org.freedesktop.ScreenSaver seemed a little more "standard" than org.gnome.ScreenSaver
# * dbus-monitoring Chrome indicated it only targets org.freedesktop.ScreenSaver and that's the main thing I care about.

# FIXME: Turn this into either a dbus or systemd service so that it starts up only when the relevant dbus interface is used.

# FIXME: Currently this only allows controlling xscreensaver, and maybe some status querying.
#        It does NOT support telling DBus when Xscreensaver state updates
#
#        I would like to improve this in future to implement xscreensaver-command's -watch functionality
#        and emit DBus messages accordingly

import random
import sys
import time

# FIXME: Can gi.repository.DBus get the same functionality?
#        Should I use that to reduce dependencies?
import dbus
import dbus.service
import dbus.glib  # Needed for the mainloop to work with GObject
from gi.repository import GObject

# FIXME: Xlib is obsolete and should be replaced.
#        I guess technically it'd be replaced by DBus,
#        so maybe it's completely valid for me to use it here as a compatibility layer
import Xlib.Xatom
import Xlib.display
import Xlib.protocol


class XSS_worker():
    def __init__(self):
        self.inhibitors = []  # Must be set in the __init__ function because of list immutability

        self.display = Xlib.display.Display()

        ## Find the xscreensaver window.
        screensavers = [child for child in self.display.screen().root.query_tree().children
                        if child.get_full_property(self.display.intern_atom("_SCREENSAVER_VERSION", False), Xlib.Xatom.STRING)]
        # FIXME: Use actual exceptions
        assert not len(screensavers) > 1, "Can't have multiple screensaver windows!"
        assert not len(screensavers) < 1, "No screensaver window found. Is there a screensaver running?"
        # Don't actually want a list, it was just the easiest way to loop over the query_tree and assert only 1 window
        self.xss_window = screensavers[0]

        ## Set the event_mask se that responses can be caught
        self.xss_window.change_attributes(event_mask=Xlib.X.PropertyChangeMask)

    def _get_xscreensaver_response(self):
        # NOTE: I've already set the necessary event mask for the xscreensaver window object to include Xlib.X.PropertyChangeMask
        response = None  # So the assert below actually triggers rather than a UnboundLocalError
        timeout = time.monotonic() + 1
        while time.monotonic() < timeout:  # If there hasn't been a response in 1 second, there won't be one
            if self.display.pending_events():
                ev = self.display.next_event()
                if ev.type == Xlib.X.PropertyNotify and \
                   ev.state == Xlib.X.PropertyNewValue and \
                   ev.atom == self.display.intern_atom("_SCREENSAVER_RESPONSE", False):
                        # NOTE: The C code accepts AnyPropertyType, not just Strings, I'm being more defensive here.
                        # FIXME: Can there be multiple responses all at once? Should we wait the whole second and add them all up?
                        # FIXME: Can I just get the property info from the event object?
                        response = ev.window.get_full_property(
                            self.display.intern_atom("_SCREENSAVER_RESPONSE", False),
                            Xlib.Xatom.STRING)
                        break
        assert response, "No response recieved"
        return response.value

    def send_command(self, atom_name):
        Xevent = Xlib.protocol.event.ClientMessage(
            display=self.display,
            window=self.xss_window,
            client_type=self.display.intern_atom("SCREENSAVER", False),
            # In the C code the last [0, 0] happened implicitly, Python's xlib doesn't cope well with them being left out though.
            # The first [0, 0] was set according to certain other arguments, but for DEACTIVATE was always [0, 0]
            data=(32, [self.display.intern_atom(atom_name, False), 0, 0, 0, 0]),
        )
        self.display.send_event(destination=Xevent.window,
                                propagate=False,
                                event_mask=0,
                                event=Xevent,
                                # FIXME: Should raise an exception here
                                onerror=lambda err: print('ERROR:', err, file=sys.stderr, flush=True))

        print("Sent XSS command", atom_name)
        response = self._get_xscreensaver_response()
        print("XSS response:", response)
        return response

    def add_inhibitor(self, inhibitor_id):
        assert inhibitor_id not in self.inhibitors, "Already working on that inhibitor"
        self.inhibitors.append(inhibitor_id)
        if len(self.inhibitors) <= 1:
            # If it's only 1 now, then there was none running before, better start one.

            # AIUI the minimum xscreensaver timeout is 60s, so poke it every 50s.
            # NOTE: This is exactly what xdg-screensaver does
            GObject.timeout_add_seconds(50, self._inhibitor_func)
            # Because of Steam (at least) being stupid and constantly Inhibitting then UnInhibiting,
            # I'm not going to poke the screensaver immediatly because I don't want it to happen before the UnInhibit
            # # GObject's first run will be after the timeout has run once,
            # # so run it once immediately as well
            # self._inhibitor_func()

    def del_inhibitor(self, inhibitor_id):
        assert inhibitor_id in self.inhibitors, "Already removed that inhibitor"
        self.inhibitors.remove(inhibitor_id)

    def _inhibitor_func(self):
        print("Inhibitor running")
        if len(self.inhibitors) == 0:
            return False  # Stops the GObject timer
        else:
            self.send_command("DEACTIVATE")
            return True


class DBusListener(dbus.service.Object):
    def __init__(self, action_handler):
        self.action_handler = action_handler

        session_bus = dbus.SessionBus()
        # FIXME: Also trigger for org.gnome.ScreenSaver
        bus_name = dbus.service.BusName("org.freedesktop.ScreenSaver", bus=session_bus)
        # FIXME: Also trigger for /org/gnome/ScreenSaver
        super().__init__(bus_name, '/org/freedesktop/ScreenSaver')

    # FIXME: Status querying of Xscreensaver is differently complicated, solve that another time
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
        self.action_handler.send_command("LOCK")

    @dbus.service.method("org.freedesktop.ScreenSaver")
    def SetActive(self, activate):
        """Blank or unblank the screensaver"""
        # xscreensaver-command -deactivate or -activate
        activate = bool(activate)  # DBus booleans turn into ints, I want bools
        resp = self.action_handler.send_command("ACTIVATE" if activate else "DEACTIVATE")
        return dbus.Boolean(  # NOTE: return True for success, not True for "activated"
            resp == ('+activating.' if activate else '+deactivating.')
        )

    @dbus.service.method("org.freedesktop.ScreenSaver")
    def SimulateUserActivity(self):
        """Poke the running locker to simulate user activity"""
        self.action_handler.send_command("DEACTIVATE")

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
        # NOTE: I could start at 0, but I've decided not to for easier debugging
        inhibitor_id = random.randint(1, 4294967296)
        self.action_handler.add_inhibitor(inhibitor_id)
        print('Inhibit called by {caller} for reason "{reason}". Given ID {ID}'.format(
            caller=caller, reason=reason, ID=inhibitor_id))
        return dbus.UInt32(inhibitor_id)

    @dbus.service.method("org.freedesktop.ScreenSaver")
    def UnInhibit(self, inhibitor_id):
        self.action_handler.del_inhibitor(inhibitor_id)
        print("UnInhibit called for inhibitor", int(inhibitor_id))


if __name__ == '__main__':
    DBusListener(XSS_worker())  # The object this returns is useless because it'll get dealt with by GObject
    GObject.MainLoop().run()
