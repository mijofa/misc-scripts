#!/bin/bash
set -eEu -o pipefail
shopt -s failglob
trap 'echo >&2 "${BASH_SOURCE:-$0}:${LINENO}: unknown error"' ERR

# FIXME: This script is obsolete, replace it with a simple alias
file-roller --extract-here "$@"

# actually_do_extraction () {
#     archive="$1"
#     new_dir="${archive##*/}"  # Basename it
#     new_dir="${new_dir%.*}"  # Remove everything after the last .
#     new_dir="${new_dir%.tar}"  # Remove .tar from the end (for cases such as .tar.gz)
# 
#     if [ -d "$new_dir" ] ; then
#         echo "$archive: ERROR: $new_dir already exists, stopping to avoid possible overwrite"
#         exit 2
#     fi
# 
#     tmp_extraction=$(mktemp --tmpdir="$PWD" --directory)
# 
#     echo "$archive: Extracting"
#     file-roller --extract-to="$tmp_extraction" "$@"
# 
#     extraction_count=$(find "$tmp_extraction" -mindepth 1 -maxdepth 1 | wc -l)
#     if [ "$extraction_count" == 1 ] ; then
#         find "$tmp_extraction" -mindepth 1 -maxdepth 1 -execdir mv -vt "$PWD" "{}" \;
#         rmdir "$tmp_extraction"
#     elif [ "$extraction_count" != 0 ] ; then
#         mv "$tmp_extraction" "$new_dir"
#         echo "$archive: Extracted to $new_dir"
#     else
#         echo "$archive: ERROR: No contents found!" >&2
#         rmdir "$tmp_extraction"
#         exit 2
#     fi
# }
# 
# for f ; do
#     # FIXME: Run them in parallel then wait for all of them to finish.
#     #        Problem is that file-roller sends instructions to the existing session if it's already running and returns instantly.
#     actually_do_extraction "$f"
# done
