#!/bin/bash
{
    cat ${1:-/dev/stdin} # If a filename is specified as the first argument, use that, otherwise use stdin.
} | {
    url="$(curl --silent --show-error -F 'sprunge=<-' http://sprunge.us)"

    if   [ -n "$1" ] ; then
        str="$1: $url"
    elif [ -z "$1" ] && history 1| grep -q 'sprunge' ; then
        str="$ $(history 1|sed -e 's/[[:digit:]]\+\s\+//') # $url" # This grabs the last line in the history which should be the current command you are running. The sed expression will probably not work as expected if you've customized the history format.
    else
        str="$url"
    fi

    printf "%s\n" "$str"
    if [ -t 1 ] && [ -n "$DISPLAY" ] ; then
        # If stdout is not a terminal then we're probably being piped into something
        # If DISPLAY is not set this won't work anyway
	# Otherwise put the sprunge URL in the X copy-paste buffer.

        # The 3 different selection buffers confuse me, so use all of them.
        # I use nohup here because xclip never actually dies it just orphans itself, although not enough to be able to close a screen window.

        # I redirect to /dev/null because I don't want nohup to create a file, and there is usually no output from xclip so I'll just throw it all away.
        nohup xclip -in -selection primary   <<< "$str" >/dev/null 2>&1
        nohup xclip -in -selection secondary <<< "$str" >/dev/null 2>&1
        nohup xclip -in -selection clipboard <<< "$str" >/dev/null 2>&1
    fi
}
