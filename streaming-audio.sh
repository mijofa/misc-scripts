#!/bin/bash

## Cleanup
## FIXME: This cleans up too much, what if loopback and null sinks are used for other reasons?
pactl unload-module module-loopback
pactl unload-module module-null-sink

REAL_INPUT=alsa_input.pci-0000_00_1b.0.analog-stereo
REAL_OUTPUT=alsa_output.pci-0000_00_1b.0.analog-stereo


## Make 2 virtual sinks
# MicAndGame: Mic+Game
pactl load-module module-null-sink sink_name=MicAndGame sink_properties=device.description=MicAndGame >/dev/null
# GameOnly: Game
pactl load-module module-null-sink sink_name=GameOnly sink_properties=device.description=GameOnly >/dev/null

## Set defaults
## NOTE: Needs to be done before connecting the loopbacks because otherwise it will change those connections
# Set default input to MicAndGame output
pactl set-default-source MicAndGame.monitor
# Set default output to GameOnly output
pactl set-default-sink GameOnly

## Link loopbacks/etc together
# Connect Mic input to MicAndGame input
pactl load-module module-loopback latency_msec=1 sink=MicAndGame source="$REAL_INPUT" >/dev/null
# Connect GameOnly output to MicAndGame input
pactl load-module module-loopback latency_msec=1 sink=MicAndGame source=GameOnly.monitor >/dev/null
# Connect GameOnly output to actual output sink
pactl load-module module-loopback latency_msec=1 sink="$REAL_OUTPUT" source=GameOnly.monitor >/dev/null

## Set Volumes
pactl set-sink-volume "$REAL_OUTPUT" 100%
pactl set-sink-volume MicAndGame 100%
pactl set-sink-volume GameOnly 20%
pactl set-source-volume "$REAL_INPUT" 30%
pactl set-source-volume MicAndGame.monitor 100%
pactl set-source-volume GameOnly.monitor 100%

printf '%s\n' "Make sure the game's output is 'GameOnly'" "Make sure Discord's output is set to 'Built-in Audio Analog Stereo'"

# Undo all this with:
#     pactl unload-module module-loopback ; pactl unload-module module-null-sink
# Make sure they run in that order, and both immediately, otherwise you might end up with bad (& loud) feedback
