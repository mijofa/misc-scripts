#!/bin/bash
# PROBLEM: vscode does not "understand the +n option for starting the editing on a specified line" like debchange expects.
#          I could ignore this if it weren't for the fact that vscode will try to open a file called '+n' instead
# vscode does have support for similar using the `--goto` argument though.
# This wrapper script just tries to bridge that gap.

# FIXME: Only considers the first argument, what about others?
#        ref: https://github.com/microsoft/vscode/issues/41858#issuecomment-525509983
if [[ $1 =~ ^\+[0-9]+$ ]] && [[ -f "$2" ]]  ; then
    linenum="${1#+}"
    shift
    filename="${1}"
    shift
    exec code --wait --reuse-window --goto "${filename}:${linenum}" "$@"
else
    # Argument(s) not valid for conversion, just pass them through as is.
    exec code --wait --reuse-window "$@"
fi
