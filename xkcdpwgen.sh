#!/bin/bash
set -eEu -o pipefail
shopt -s failglob
trap 'echo >&2 "${BASH_SOURCE:-$0}:${LINENO}: unknown error"' ERR

# qtpass doesn't support xkcdpass
# qtpass *does* support pwgen
# This hacks xkcdpass into looking kinda like pwgen

# But only if the '--secure' agrument is not being passed in.
# QTPass calls that "Generate easy to memorize but less secure passwords".
if [[ " $* " =~ " --secure " ]] ; then
    pwgen "$@"
else
    ## In order to keep many websites happy there's some other annoyances we have to work with,
    ## QTPass and pwgen already kinda handle this, so I can re-use those arguments:
    # Default to CamelCased passphrases unless told otherwise
    case="first"
    # Always using including some digits unless told otherwise.
    # Many websites don't like space characters, so just don't do that.
    delim_number="8"
    delim_symbol=""

    getopt_string="$(getopt -n "${0##*/}" --options 0Ay --long no-numerals,no-capitalize,symbols -- "$@")" || exit $?
    declare -a "getopt_array=($getopt_string)"
    set -- "${getopt_array[@]}"

    while [[ $# -gt 0 ]] ; do
      case "$1" in
        # FIXME: -y -0 will result in no delimiters at all
        -0 | --no-numerals)   delim_number=""     ; shift   ;;
        -A | --no-capitalize) case="lower"        ; shift   ;;
        # Include some "special" symbols if told to
        -y | --symbols)       delim_symbol+="#"   ; shift 2 ;;
        --) shift; break ;;
        # This should not be possible because it will be caught by the `exit $?` on getopt above.
        # NOTE: This error doesn't look the same as getopt's error above, but this will quote better.
        *) printf "${0##*/}: unrecognized option %q\n" "$1" ; exit 1 ;;
      esac
    done
    if [[ $# -gt 2 ]] ; then
        printf "${0##*/}: Too many non-option arguments: %q\n" "$@"
        exit 2
    fi
    pw_length=${1:-8}
    if ! [[ $pw_length =~ ^[0-9]+$ ]] ; then
        printf "${0##*/}: pw_length argument must be a number not %q\n" "$pw_length"
        exit 2
    fi
    num_pw=${2:-1}
    if ! [[ $num_pw =~ ^[0-9]+$ ]] ; then
        printf "${0##*/}: num_pw argument must be a number not %q\n" "$num_pw"
        exit 2
    fi

    # pwgen has a "length" argument that specifies the number of characters
    # QTPass doesn't let that be less than '8'
    # Using this as number of words results in some very long passphrases that many websites don't support.
    # So let's halve it as well, giving us a minimum of 4 words, but I think that's reasonable.
    numwords=$(($pw_length / 2))

    xkcdpass --delimiter "${delim_number}${delim_symbol}" --case "$case" --numwords "$numwords" --count "$num_pw"
fi
