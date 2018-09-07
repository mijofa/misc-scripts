#!/usr/bin/python3
import os
import shlex
import sys

def normalise_git_dir(git_dir):
    """
    Normalises the different representations of:
    * vcs/foo
    * vcs/foo.git
    * ~/vcs/foo.git
    * /home/user/vcs/foo.git

    Do this so that we can more accurately compare what's requested over SSH with what's supplied via argv[1]
    As they may use different representations of the same path.
    """
    # Expand ~ to $HOME
    if git_dir.startswith('~'):
        git_dir = os.path.expanduser(git_dir)
    # OR, expand current directory to $HOME
    elif not git_dir.startswith('/'):
        git_dir = os.path.expanduser('~/'+git_dir)

    # If the working tree doesn't exist, try for a bare git repo
    if not os.path.isdir(git_dir) and not git_dir.endswith('.git'):
        git_dir = git_dir.rstrip('/') + '.git'

    # At this point, assume we've got the correct directory as we've normalised it as far as we can go
    return git_dir


## Make sure we've been called with the correct lockdown parameters and such
assert 2 <= len(sys.argv) <= 3, "USAGE: {0} [--read-only] GIT_DIR".format(*sys.argv)
if len(sys.argv) == 3:
    assert sys.argv[1] == '--read-only', "ERROR: --read-only is the only support argument"
    # Don't allow any commands used during 'git-push'
    forced_cmds = ('git-receive-pack',)
else:
    # According to git-shell's manpage these are the only things git-shell runs out of the box
    # FIXME: As far as I can tell, git-upload-archive doesn't get used when push/pulling so I've left that out
    forced_cmds = ('git-receive-pack', 'git-upload-pack')
assert 'SSH_ORIGINAL_COMMAND' in os.environ, "ERROR: This is meant to be run from SSH's AuthorizedKeysCommand"


# FIXME: assert that this directory exists?
#        I'm currently just letting git deal with that later
forced_git_dir = normalise_git_dir(sys.argv[-1])

## Get the intended action
# FIXME: Is shlex necessary or is the normal split good enough?
#        I figured shlex would be more likely to do the right thing with regards to spaces in directory names and similar
requested_cmd, requested_git_dir = shlex.split(os.environ['SSH_ORIGINAL_COMMAND'])

## Confirm it's a reasonable action
assert requested_cmd in forced_cmds, "DENIED: Not a recognised/allowed git-shell command"

## Confirm we're allowed to do it
assert normalise_git_dir(requested_git_dir) == forced_git_dir, "DENIED: Not allowed to use that git directory"

## Just do it
os.execlp(requested_cmd, requested_cmd, forced_git_dir)