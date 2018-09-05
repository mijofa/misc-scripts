Magnet Handler
==============
URL handler for magnet: links.
Simply sends an email including the magnet link in the body, which is then dumped into rtorrent's watch directory on my torrenting server.

I've only used and tested this with an XFCE environment running Google Chrome/Chromium. I believe with Firefox it's easier to install as you don't actually need to incorporate it into your environment, Firefox just asks what you want to do when you click an unrecognised link scheme.

Installation
------------
1. Update the default SMTP-SERVER and RECIPIENT (search for "REPLACEME")
2. Copy magnet-handler to somewhere in your $PATH
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
