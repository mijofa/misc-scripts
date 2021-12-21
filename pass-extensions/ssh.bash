#!/bin/bash

# The main logic of grabbing the passwords actually needs to be done in an "askpass" command that SSH calls out to.
export SSH_ASKPASS="${BASH_SOURCE[0]%.bash}.askpass-helper"
export SSH_ASKPASS_REQUIRE=force  # NOTE: If there's any extra password prompts, they will appear in a GUI
# Need to somehow get the pass file sent through to the askpass helper,
# and ssh won't allow arguments in the askpass variable (it uses exec()).
# Thankfully it allows environment variables through though, so set one.
export PASSWORD_STORE_SSH_ASKPASS_HELPER_RECORD="$1"

# This helper is what we use when the password file is just an SSH key
ssh_agent_helper="${BASH_SOURCE[0]%/*}/ssh-agent.bash"

# Pass can verify extension file's GPG signatures before sourcing them, so verify the helpers this calls out to as well.
verify_file "$SSH_ASKPASS"
verify_file "$ssh_agent_helper"

# All other arguments should go straight to SSH itself
shift

# FIXME: Allow for a "host: " or "^url: ssh" line
ssh_host="${PASSWORD_STORE_SSH_ASKPASS_HELPER_RECORD##*/}"

first_line=$(pass show "$PASSWORD_STORE_SSH_ASKPASS_HELPER_RECORD" | head -1) || exit $?
if [[ "$first_line" =~ ^-----BEGIN.* ]] ; then
    # Entire file is an ssh key, create a temporary SSH agent and use it
    # FIXME: What if the there's an SSH key in the file *and* a password at the top?
    "$ssh_agent_helper" "$@" ssh "$ssh_host"
#elif [[ "$first_line" =~ ^otpauth:// ]] ; then
#    # First line is an OTP URI, we actually don't need to do anything special here as it's handled in the askpass helper
else
    # First line is a password or OTP URI, use it
    # NOTE: This adds the "@" on the end of the username so that I don't need to add any extra effort to deal with a non-existent 'login:' line
    ssh_user="$(pass show "$PASSWORD_STORE_SSH_ASKPASS_HELPER_RECORD" | sed --quiet '/login:/ s/^.*:\s\+\(.*\)$/\1@/p')"

    ssh "${ssh_user}${ssh_host}" "$@"
fi
