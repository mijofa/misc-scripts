#!/usr/bin/python3
import sys
import pathlib
import argparse
import subprocess
import configparser
import shlex
import re

# FIXME: Check system path too? Subdirectories? $XDG_..._DIR?
user_apps_path = pathlib.Path('~/.local/share/applications/').expanduser()

argparser = argparse.ArgumentParser()
argparser.add_argument('url', nargs='+')
args, other_args = argparser.parse_known_args()

# FIXME: Extend this to other URI schemes?
mime_handlers = {}
mimeinfo = configparser.ConfigParser(interpolation=None)
mimeinfo.read_string((user_apps_path / 'mimeinfo.cache').read_text())
for key in mimeinfo['MIME Cache'].keys():
    if key in ('x-scheme-handler/https', 'x-scheme-handler/http'):
        # Value is ';' separated, and usually ends with a ';', so strip & split it.
        mime_handlers[key.split('/', 1)[1]] = mimeinfo['MIME Cache'].get(key).strip(';').split(';')

# Compile dict of {regexp: command line}
# FIXME: Is there really no "run this .desktop file with this URI" command?
#        I've found plenty for "run this .desktop file" (`gio launch` was my favourite) but none of them pass arguments through.
regexp_handlers = {}
# FIXME: Behaviour is undetermined if 2 .desktop files have the same regexp
for handler in set(h for sublist in mime_handlers.values() for h in sublist):
    if not (user_apps_path / handler).exists(): continue
    handler_config = configparser.ConfigParser(interpolation=None, allow_no_value=True)
    handler_config.read_string((user_apps_path / handler).read_text())
    for section in handler_config.sections():
        if handler_config.has_option(section, 'X-Mijofa-URL-regexps') and handler_config.has_option(section, 'Exec'):
            for r in handler_config.get(section, 'X-Mijofa-URL-regexps').strip(';').split(';'):
                regexp_handlers[re.compile(r)] = shlex.split(handler_config.get(section, 'Exec'))

subprocesses = []
for url in args.url:
    # Sort by length of regexp, longest first
    for regexp in sorted(regexp_handlers, key=lambda r: len(r.pattern), reverse=True):
        if regexp.match(url):
            args = regexp_handlers[regexp].copy()
            args[args.index('%u')] = url
            subprocesses.append(subprocess.Popen(args))
            break

# Wait for all subprocesses to return
for p in subprocesses:
    p.wait()
