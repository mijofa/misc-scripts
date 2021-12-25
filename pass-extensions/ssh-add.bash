#!/bin/bash
# Import all arguments into the ssh-agent as SSH keys
# FIXME: Ignore the first line?
# FIXME: Treat the first line as the key's passphrase?

for key_file in "$@" ; do
    ssh-add <(pass show "$key_file")
done
