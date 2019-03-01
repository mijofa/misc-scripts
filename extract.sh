#!/bin/bash

tmp_extraction=$(mktemp --tmpdir="$PWD" --directory)

archive="${@: -1}"  # Last argument
new_dir="${archive%.*}"  # Remove everything after the last .
new_dir="${new_dir%.tar}"  # Remove .tar from the end (for cases such as .tar.gz)

if [ -d "$new_dir" ] ; then
    echo "ERROR: $new_dir already exists, stopping to avoid possible overwrite"
    exit 2
fi

echo "Extracting $archive"
file-roller --extract-to="$tmp_extraction" "$@"

extraction_count=$(find "$tmp_extraction" -mindepth 1 -maxdepth 1 | wc -l)
if [ "$extraction_count" == 1 ] ; then
    # FIXME: Should I just use "mv $tmp_extraction/* ."?
    #        I'm a bit nervous about . files or similar
    contents="$(find "$tmp_extraction" -mindepth 1 -maxdepth 1)"
    mv "$contents" "$PWD"
    echo "Extracted ${contents##*/}"
    rmdir "$tmp_extraction"
elif [ "$extraction_count" != 0 ] ; then
    mv "$tmp_extraction" "$new_dir"
    echo "Extracted contents to $new_dir"
else
    echo "ERROR: No contents found!" >&2
    rmdir "$tmp_extraction"
    exit 2
fi
