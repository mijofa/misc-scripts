#!/bin/bash

# Create temporary SSH agent
# FIXME: Is this lifetime good enough?
. <(ssh-agent -s -t 3)

# Import key from password-store
# FIXME: Other extensions seem to do 'gpg' themselves. Should I do the same?
ssh-add <(pass show "$1")

# Run the rest of the command line
shift
"$@"

# Kill the temporary SSH agent
. <(ssh-agent -k)
