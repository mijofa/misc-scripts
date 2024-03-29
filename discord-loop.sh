#!/bin/bash
# Problem: Discord keeps crashing mid-game, I don't even notice for a minute because all I see is everyone go silent for a minute
# Solution: This horrible loop that restarts it, shoves it to the side, then refocuses the app I want
# Bonus problem: Discord's priority speaker doesn't work with voice activity
# Bonus solution: This horrible xbindkeys shit that effectively inverts the push-to-talk behaviour into push-to-silence

# NOTE: This does not work properly if there's more than one window with "Discord" in the title


while true ; do
#    secondary_screen_position=$(xrandr | sed --silent -E 's/^.* connected ([[:digit:]]+)x([[:digit:]]+)\+([[:digit:]]+)\+([[:digit:]]+) .*$/\3,\4,\1,\2/p')
    active_winid="$(xprop -root -notype -f _NET_ACTIVE_WINDOW 0x " \$0\\n" _NET_ACTIVE_WINDOW)"
    active_winid=${active_winid#_NET_ACTIVE_WINDOW }
    discord & discord_pid=$!
    # For the first 5 seconds, don't let Discord steal focus for more than half a second
    for i in {1..15} ; do 
        sleep 0.5
        # FIXME: Apparently xdotool can do all of this. Use that and reduce the script's dependencies.
        wmctrl -F -r 'Discord' -b add,sticky,above || continue
#        wmctrl -F -r 'Discord' -e 0,2880,400,-1,-1 
        wmctrl -i -a "$active_winid"
    done
    # FIXME: If discord exits cleanly, we should quit the entire script
    wait "$discord_pid" || true  # I expect Discord to crash, don't let it trigger the trap
done
