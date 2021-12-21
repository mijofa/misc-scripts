#!/bin/bash
# Just import this file as an SSH key
# FIXME: Ignore the first line?
# FIXME: Treat the first line as the key's passphrase?
ssh-add <(pass show "$1")
