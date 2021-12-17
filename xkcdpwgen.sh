#!/bin/bash

# qtpass doesn't support xkcdpass
# qtpass *does* support pwgen
# This hacks xkcdpass into looking kinda like pwgen

# But only if the '--secure' agrument is not being passed in.
# QTPass calls that "Generate easy to memorize but less secure passwords".
if [[ " $* " =~ " --secure " ]] ; then
    pwgen "$@"
else
    # pwgen has a "length" argument that specifies the number of characters
    # QTPass doesn't let that be less than '8'
    # This results in some very long passphrases that many websites don't support,
    # so let's halve it and use it as number of words
    # Giving us a minimum of 4 words, but I think that's reasonable.
    length="${@: -1}"
    length=$(($length / 2))

    ## In order to keep many websites happy there's some other annoyances we have to work with,
    ## QTPass and pwgen already kinda handle this, so I can re-use those arguments:
    # Default to CamelCased passphrases unless told otherwise
    case="first"
    [[ " $* " =~ " --no-capitalize " ]] && case="lower"
    # Always using including some digits unless told otherwise.
    # Many websites don't like space characters, so just don't do that.
    delimiter="8"
    [[ " $* " =~ " --no-numerals " ]] && delimiter=""
    # Include some "special" symbols if told to
    [[ " $* " =~ " --symbols " ]] && delimiter+="#"

    xkcdpass --delimiter "$delimiter" --case "$case" --numwords "$length"
fi
