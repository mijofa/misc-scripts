#!/bin/bash
set -x

if [[ "$#" -eq 0 ]] ; then
    echo "No arguments, launching as-is"
    exec firefox-esr "$@"
fi

private_urls=()
session_urls=()
for arg in "$@" ; do
    if [[ ! "$arg" =~ ^https?:// ]] ; then
        echo "Argument is not a http(s) URL, launching with unmodified arguments"
        exec firefox-esr "$@"
    else
        if grep -xEf "${0%/*}/private-browser-with-exceptions.grep" <<<"$arg" ; then
            session_urls+=("$arg")
        else
            private_urls+=("$arg")
        fi
    fi
done
# I started with something like this:
#     [[ "${#private_urls[@]}" -gt 0 ]] && firefox-esr --private-window "${private_urls[@]}"
#     [[ "${#session_urls[@]}" -gt 0 ]] && firefox-esr "${session_urls[@]}"
# But only one '--private-window' arg is allowed at a time.

for url in "${private_urls[@]}" ; do
    firefox-esr --private-window "${url}"
done
# FIXME: This will open in a new tab if there's only 1 URL, but new window if more than one
#        Using '--new-window' when there's exactly 2 URLs causes the 2nd to open in existing window and 1st to open in new window.
[[ "${#session_urls[@]}" -gt 0 ]] && firefox-esr "${session_urls[@]}"
