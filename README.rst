Magnet Handler
==============
URL handler for magnet: links.
Simply sends an email including the magnet link in the body, which is then dumped into rtorrent's watch directory on my torrenting server.

I've only used and tested this with an XFCE environment running Google Chrome/Chromium. I believe with Firefox it's easier to install as you don't actually need to incorporate it into your environment, Firefox just asks what you want to do when you click an unrecognised link scheme.

Installation
------------
1. Update the default SMTP-SERVER and RECIPIENT (search for "REPLACEME")
2. Copy magnet-handler.py to somewhere in your $PATH
   NOTE: Remove the '.py' extension when doing so
4. Install the .desktop file into your environment::

    xdg-desktop-menu install --novendor magnethandler.desktop
    xdg-mime default magnethandler.desktop x-scheme-handler/magnet  # 'magnethandler.desktop' here should never have a path, as it does not refer to the file in current directory but rather the file after installation in the previous line.

find_win (OBSOLETE)
===================
OBSOLETE: When I wrote this script I did not realise $WINDOWID was a thing.
          Turns out it would not have worked for me anyway because screen is bad with ENV, but I'm switching to tmux and it works now.

Find the X window ID for the current shell. This doesn't work too well inside of screen.

The use-case for this was so I could use wmctrl to switch to the window it's being run from without already knowing that.

notify-phone
============
Use pushjet.io to notify my phone, this still requires some work and I intend to set up my own Pushjet server for use with this

Update the PUSHJET_SECRET before using (search for "REPLACEME")

popup-notify
============
Equivalent "zenity --info" that doesn't require installing the overly bloated Zenity

FIXME: Needs to be updated to python3

sprunge
=======
Wrapper script for sprunge.us because I wanted it to automatically add the URL to my X clipboard

timer
=====
What I expect is a highly inefficient wrapper around sleep(1) which includes a countdown. Because I wanted some visibility of how long was left in longer running sleep commands.

restricted-git
==============
This is to be run from in a forced SSH command for a given SSH key so that I can set up a single SSH key that only git on a single repo.

js-wake
=======
This is intended to help solve the problem of Xscreensaver not staying awake when using a joystick/gamepad input.

This script should be kept as minimalistic as possible, the whole point is for it to be running when there's already resource-intensive games running, don't add to that for something that should've been built into the game and/or Steam in the first place.

dbus-xscreensaver
=================
So I refuse to use any lockscreen other than xscreensaver, I'll just link to someone else explaining why that is: https://www.jwz.org/blog/2015/04/i-told-you-so-again/

Problem though is that xscreensaver doesn't implement a way for games/video-players/etc to inhibit or suspend the screensaver in some way so that I can sit back and watch a movie or play a game using non-X11 inputs such as game controllers. The closest solution Xscreensaver implements is the ability to "poke" the screensaver and keep it awake for another minute (or however long the configured timeout is) by simulating user input.

That seems reasonable to me, with that approach if the inhibiting app crashes or loses contact then xscreensaver will lock a minute later, failing safe. However no apps actually bother implementing this because gnome-screensaver, light-locker, and other "alternative" screensavers implement a way of inhibiting the screensaver via DBus calls. Chrome/Chromium was the particular app that was getting on my nerves and triggered me to right this.

This script is intended to be a compatibility layer between the org.freedesktop.ScreenSaver DBus calls and the xscreensaver-command functions, with a primary focus on supporting the Inibit/UnInhibit method by repeatedly simulating user input. It's not very pretty, and I admit that I'm probably reducing the security of my lockscreen by implementing such a thing, but it should still be safer than using an alternative.

FIXME: Somehow get the PID of the D-BUS caller and cancel the inhibitor if that PID dies.

Install as a systemd user service
---------------------------------
NOTE: If you don't have this repo cloned in ~/vcs/misc-scripts then you'll need to change the .service file a little. I'll leave that as an exercise for th reader

* Symlink dbus-xscreensaver.service into ~/.config/systemd/user/
* Then symlink ~/.config/systemd/user/dbus-xscreensaver.service into ~/.config/systemd/user/default.target.wants
  NOTE: You can't skip either of these steps, I know, it's stupid, welcome to systemd
* Reload the systemd user daemon
* Start the systemd service

Or just run this::

    ln -s ~/vcs/misc-scripts/dbus-xscreensaver.service ~/.config/systemd/user/
    ln -s ../dbus-xscreensaver.service ~/.config/systemd/user/default.target.wants
    systemctl --user daemon-reload
    systemctl --user start dbus-xscreensaver

extract
=======
PROBLEMS
--------
1. Remembering the exact arguments for every single different archive extractor tar/zip/rar/etc
2. Not knowing ahead of time whether the archive was a single directory full of stuff, or just a whole bunch of files in the root of the archive

SOLUTION
--------
1. file-roller will "magically" figure out what extractor to use and use it. Downside is that it's a GUI, but I don't care enough.
2. This script will extract into a tmp dir (in current directory to avoid filling /tmp) then count the entries in the root of that tmp dir:
   * If it's more than 1, rename the tmp dir to the name of the archive (minus extension)
   * If it's only 1, move it out to the current directory and delete the tmp dir.
