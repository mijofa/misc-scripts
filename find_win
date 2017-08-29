#!/bin/bash
## Finds the window ID that this script is being called from.
## Does horrible things with walking the PID tree to find the first parent that has a window associated with it

winlist=$(wmctrl -pl) # Get all the windows the window manager knows about

pstree -A -s -l -p $$ | grep "$$" | sed 's/[^(]*(\([^)]*\))/\1\n/g' | sort -n | while read pid ; do # Walk the process tree up from current PID
    test -z "$pid" && continue
    pid_win=$(egrep "^0x[[:xdigit:]]+ +[-[:digit:]]+ $pid " <<<"$winlist") # Does this PID have a window?
    if [ -n "$pid_win" ] ; then
        read winid deskid pid host name <<< "$pid_win"
        echo "$winid"
        break
    fi
done
