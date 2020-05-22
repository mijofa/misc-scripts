#!/bin/bash
# Problem: Discord keeps crashing mid-game, I don't even notice for a minute because all I see is everyone go silent for a minute
# Solution: This horrible loop that restarts it, shoves it to the side, then refocuses the app I want

# NOTE: This does not work properly if there's more than one window with "Discord" in the title

while true ; do
    active_winid="$(xprop -root -notype -f _NET_ACTIVE_WINDOW 0x " \$0\\n" _NET_ACTIVE_WINDOW)"
    active_winid=${active_winid#_NET_ACTIVE_WINDOW }
    discord-ptb &
    # For the first 5 seconds, don't let Discord steal focus for more than half a second
    for i in {1..10} ; do 
        sleep 0.5
        wmctrl -F -r 'Discord' -b add,sticky,above
        wmctrl -F -r 'Discord' -e 0,2880,400,-1,-1 
        wmctrl -i -a "$active_winid"
    done
    wait
done
