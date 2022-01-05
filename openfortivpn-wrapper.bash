#!/bin/bash
# Workaround for https://gitlab.gnome.org/GNOME/NetworkManager-fortisslvpn/-/issues/20
# It has been fixed in https://gitlab.gnome.org/GNOME/NetworkManager-fortisslvpn/-/merge_requests/15
# Which has apparently been merged at https://gitlab.gnome.org/GNOME/NetworkManager-fortisslvpn/-/commit/66d431f18fd4812ed984790c877d965b35b69612
# But it seems that hasn't made it to Debian yet.

# NOTE: Doesn't seem to pick up on search domains, this hasn't been enough of a problem for me to give a shit though.

if ! [[ "$@" =~ " --pppd-use-peerdns" || "$@" =~ " --pppd-no-peerdns" ]] ; then
    if [[ "$@" =~ " --pppd-plugin /usr/lib/pppd/2.4.9/nm-fortisslvpn-pppd-plugin.so" ]] ; then
        set -- "$@" --pppd-use-peerdns=1
    fi
fi

exec /bin/openfortivpn.distrib "$@"
