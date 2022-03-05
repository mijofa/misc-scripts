#!/usr/bin/python3
"""
MPC wrapper script that gets the server details from the gmpc config files

Used to use gmpc-remote, but that's been removed in the upgrade to Debian Bullseye.
So lets just use MPC, but then we can't easily change what server mpc talks to via the gmpc GUI.
This should glue the 2 together nicely.
"""
import configparser
import os
import pathlib
import sys

config_dir = pathlib.Path('~/.config/gmpc/').expanduser()

# This config file specifies where what profile is loaded
gmpc_cfg = configparser.ConfigParser()
try:
    gmpc_cfg.read(os.fspath(config_dir / 'gmpc.cfg'))
except configparser.ParsingError:
    # These aren't quite .ini files, so this is expected
    # It's close enough and still works
    pass

# This has the profile definitons that include the actual host & port number
profiles_cfg = configparser.ConfigParser()
try:
    profiles_cfg.read(config_dir / pathlib.Path('profiles.cfg'))
except configparser.ParsingError:
    # These aren't quite .ini files, so this is expected.
    # It's close enough and still works
    pass


currentProfile = gmpc_cfg['connection']['currentProfile'].strip('"')

# Run MPC with the required environment variables and arguments.
os.execvpe('mpc', sys.argv,
           {'MPD_HOST': profiles_cfg[currentProfile]['hostname'].strip('"'),
            'MPD_PORT': profiles_cfg[currentProfile]['portnumber'].strip('"')})
