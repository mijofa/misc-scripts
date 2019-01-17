#!/usr/bin/python3
import os
import sys

import json
import argparse
import hashlib
import urllib.request

DIR = os.path.join(os.environ.get('XDG_RUNTIME_DIR', os.environ.get('TMPDIR', '/tmp/')), os.path.basename(sys.argv[0]))
if not os.path.isdir(DIR):
    os.mkdir(DIR)
os.chdir(DIR)

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                 description='Check if a website has updated since last checked')
parser.add_argument('--email', metavar="NOTSUPPORTED", type=str, nargs=1, help="Send an email notifying people there's been an update")
parser.add_argument('URL', type=str, nargs='+', help="The URL to check for updates")
args = parser.parse_args()

new_sums = {}
for url in args.URL:
    with urllib.request.urlopen(url) as req:
        new_sums[url] = hashlib.sha512(req.read()).hexdigest()

if os.path.isfile('checksums.json'):
    with open('checksums.json') as f:
        old_sums = json.load(f)
else:
    old_sums = {}

diff_sums = {}
for url in new_sums.keys():
    if old_sums.get(url) != new_sums.get(url):
        diff_sums[url] = (old_sums.get(url), new_sums.get(url))

with open('checksums.json', 'w') as f:
    json.dump(new_sums, f)

for url in diff_sums:
    print("Detected change at {}".format(url))
    print("Old sha512sum: {0}\nNew sha512sum: {1}".format(*diff_sums[url]))

if diff_sums:
    sys.exit(1)
