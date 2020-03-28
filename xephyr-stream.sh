#!/bin/bash
export PULSE_SINK="Remap_sink"

if ! pacmd list-sinks | grep "$PULSE_SINK" ; then
    pacmd load-module module-remap-sink sink_name="$PULSE_SINK" master=0 channels=2 remix=no
fi
export PULSE_SOURCE="$PULSE_SINK.monitor"

# FIXME: Enable GLX somehow?
#        Using glamor made things slower
Xephyr -output DVI-D-0 ":1" &
export DISPLAY=:1

sleep 2  # Wait for the Xephyr server to actually be ready
xfwm4 &  # Some things need a window manager

twitch () {
    # This mostly came straight from https://wiki.archlinux.org/index.php/Streaming_to_twitch.tv#Ffmpeg_solutions
    # I have made a couple small changes though

    INRES="$(xdpyinfo  | sed --quiet 's/^\s*dimensions:\s*\(.\+\) pixels.*$/\1/p')" # input resolution
    #OUTRES="854x480" # output resolution
    OUTRES="352x240" # output resolution
    FPS="30" # target FPS
    GOP="60" # i-frame interval, should be double of FPS, 
    GOPMIN="30" # min i-frame interval, should be equal to fps, 
    THREADS="$(grep '^processor' /proc/cpuinfo | wc -l)" # max 6
    CBR="1000k" # constant bitrate (should be between 1000k - 3000k)
    QUALITY="ultrafast"  # one of the many FFMPEG preset
    AUDIO_RATE="44100"

    ffmpeg -loglevel warning \
      -f x11grab -s "$INRES" -r "$FPS" -i "$DISPLAY" \
      -f pulse -i "${PULSE_SOURCE-default}" -f flv -ac 2 -ar $AUDIO_RATE \
      -vcodec libx264 -g $GOP -keyint_min $GOPMIN -b:v $CBR -minrate $CBR -maxrate $CBR -pix_fmt yuv420p\
      -s $OUTRES -preset $QUALITY -tune film \
      -acodec aac -threads $THREADS -strict normal \
      -bufsize $CBR "$1"
}
show_time () {
    while sleep 1 ; do
        date +'%T'
    done | osd_cat --lines=1 --align right -f -*-*-bold-*-*-*-30-*-*-*-*-*-*-*
}

twitch "$1" &
shift # Remove $1

show_time &

"$@"

# Now that whatever requested app is exited, kill everything else
kill $(jobs -p)
