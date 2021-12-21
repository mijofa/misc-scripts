#!/bin/bash
# Grab *just* the password from the given file
# Basically the opposite of pass-extension-tail
#
# Similar to 'show -c1' but for use in piping scripts together such as::
#     ldapsearch -y <(pass head ldap.lan)

pass show "$@" | head -n 1 | tr -d '\n'
