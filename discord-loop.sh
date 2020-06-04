#!/bin/bash
# Problem: Discord keeps crashing mid-game, I don't even notice for a minute because all I see is everyone go silent for a minute
# Solution: This horrible loop that restarts it, shoves it to the side, then refocuses the app I want
# Bonus problem: Discord's priority speaker doesn't work with voice activity
# Bonus solution: This horrible xbindkeys shit that effectively inverts the push-to-talk behaviour into push-to-silence

# NOTE: This does not work properly if there's more than one window with "Discord" in the title


# F15 is configured as the normal push-to-talk button in Discord,
# mouse button 8 is configured for priority push-to-talk in Discord
# Us xbindkeys & xdotool to hold F15 when mouse button 8 or 9 is released.
printf '"%s"\n%s\n' "xdotool keyup F15" 'b:9'    "xdotool keydown F15" 'b:9 + Release'    "xdotool keyup F15" 'b:8'    "xdotool keydown F15" 'b:8 + Release' | \
xbindkeys -n -f /dev/stdin & xbindkeys_pid=$!
# Make sure F15 is released when this script dies
trap "xdotool keyup F15 ; kill $xbindkeys_pid" ERR EXIT

while true ; do
    active_winid="$(xprop -root -notype -f _NET_ACTIVE_WINDOW 0x " \$0\\n" _NET_ACTIVE_WINDOW)"
    active_winid=${active_winid#_NET_ACTIVE_WINDOW }
    discord-ptb & discord_pid=$!
    # For the first 5 seconds, don't let Discord steal focus for more than half a second
    for i in {1..10} ; do 
        sleep 0.5
        # FIXME: Apparently xdotool can do all of this. Use that and reduce the script's dependencies.
        wmctrl -F -r 'Discord' -b add,sticky,above || continue
        wmctrl -F -r 'Discord' -e 0,2880,400,-1,-1 
        wmctrl -i -a "$active_winid"
    done
    # I actually want voice activity, so start the push-to-talk as soon as Discord is back
    xdotool keydown F15
    # FIXME: If discord exits cleanly, we should quit the entire script
    wait "$discord_pid" || true  # I expect Discord to crash, don't let it trigger the trap
    # If discord crashes, release the push-to-talk key
    xdotool keyup F15
done
