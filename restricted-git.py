#!/usr/bin/python3
import os
import shlex
import sys

# According to git-shell's manpage these are the only things git-shell runs out of the box
# FIXME: As far as I can tell, git-upload-archive doesn't get used when push/pulling so I've left that out
forced_cmds = ['git-receive-pack', 'git-upload-pack']


def normalise_git_dir(git_dir):
    """
    Normalises the different representations of:
    * vcs/foo
    * vcs/foo/
    * vcs/foo.git
    * ~/vcs/foo.git
    * ~/vcs/foo.git/
    * /home/user/vcs/foo.git

    Do this so that we can more accurately compare what's requested over SSH with what's supplied via argv[1]
    As they may use different representations of the same path.
    """
    # FIXME: This is me reinventing something git does internally, is there way for me to just ask git to do it?

    # Remove all trailing directory separators
    if git_dir.endswith(os.path.sep):
        git_dir = git_dir.rstrip(os.path.sep)

    # If given a relative path, make it relative to ~, which gets expanded to $HOME later
    if not git_dir.startswith(os.path.sep):
        git_dir = os.path.join('~', git_dir)

    # Expand ~ to $HOME
    if git_dir.startswith('~'):
        git_dir = os.path.expanduser(git_dir)

    # If given a working tree and it doesn't exist, try for a bare git repo
    if not os.path.isdir(git_dir) and not git_dir.endswith('.git'):
        git_dir = git_dir + '.git'

    # At this point, assume we've got the correct directory as we've normalised it as far as we can go
    return git_dir


## Make sure we've been called with the correct lockdown parameters and such
assert 2 <= len(sys.argv) <= 3, "USAGE: {0} [--read-only] GIT_DIR".format(*sys.argv)
if len(sys.argv) == 3:
    assert sys.argv[1] == '--read-only', "ERROR: --read-only is the only supported argument"
    # Don't allow any commands used during 'git-push'
    # NOTE: If git-upload-archive gets enabled, it should also be removed here.
    forced_cmds.remove('git-upload-pack')
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
# NOTE: I'm passing forced_git_dir rather than requested as a defense-in-depth,
#       just in case I've incorrectly identified requested as matching forced when that's not the case
os.execlp(requested_cmd, requested_cmd, forced_git_dir)
