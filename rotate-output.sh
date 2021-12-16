#!/bin/bash
#
# Rotates the specified xrandr output in the relative direction specified.
# Since xrandr will only accept an absolute rotation value I need this for "flip" and "clockwise" rotation operations

output="$1"
new_rotation="$2"

if [ -z "$output" ] || [ -z "$new_rotation" ] ; then
  echo "ERROR: Must specify an output and a rotation value"
  echo "Usage: $0 OUTPUT normal|inverted|left|right|clockwise|flip"
  echo
  exit 1
fi

orig_rotation="$(xrandr --current --verbose | grep "$output connected " | egrep -o '\) (normal|left|inverted|right) \(')"
orig_rotation="${orig_rotation#) }"
orig_rotation="${orig_rotation% (}"

if [ -z "$orig_rotation" ] ; then
    echo "ERROR: Output $output not found or not connected"
    exit 1
fi

# The nested case statements seems inelegant, but it's probably the best way to do this
case "$new_rotation" in
    clockwise)
        case "$orig_rotation" in
            normal)
                desired_rotation="right"
                ;;
            right)
                desired_rotation="inverted"
                ;;
            inverted)
                desired_rotation="left"
                ;;
            left)
                desired_rotation="normal"
                ;;
        esac
        ;;
    flip)
        case "$orig_rotation" in
            normal)
                desired_rotation="inverted"
                ;;
            right)
                desired_rotation="left"
                ;;
            inverted)
                desired_rotation="normal"
                ;;
            left)
                desired_rotation="right"
                ;;
        esac
        ;;
    counterclockwise)
        case "$orig_rotation" in
            normal)
                desired_rotation="left"
                ;;
            right)
                desired_rotation="normal"
                ;;
            inverted)
                desired_rotation="right"
                ;;
            left)
                desired_rotation="inverted"
                ;;
        esac
        ;;
    normal|right|inverted|left)
        desired_rotation="$1"
        ;;
    *)
        echo "ERROR: Unrecognised rotation value: $new_rotation"
        echo "Usage: $0 OUTPUT normal|inverted|left|right|clockwise|flip"
        echo
        exit 1
        ;;
esac

echo "Setting rotate '$desired_rotation' on $output"
xrandr --output "$output" --rotate "$desired_rotation"
