#!/bin/bash
# This is similar to pass-extension-meta, but much simpler and doesn't call out to perl
# (although it does use Grep's Perl parser, I could swap to sed if needed)

meta_key="$1"
shift

pass show "$@" | grep --color=never --only-matching --perl-regexp "^${meta_key}:\s+\K.*$"
