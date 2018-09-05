#!/usr/bin/python3

## Use Pushjet to send a notification to my phone

# FIXME: Doesn't support unicode emoji. Not sure if this is my fault or Pushjet's.
# UPDATE: Pushjet's api documentation doesn't support it either.

import argparse
import urllib.parse
import urllib.request
import sys
import json
import socket  # Only used for gethostname()  FIXME: Is this overkill?

# FIXME: Get these from a config file
PUSHJET_URL = 'https://api.pushjet.io/'
PUSHJET_SECRET = REPLACEME

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='Send a notification via Pushjet.')
parser.add_argument('-v', '--version',    action='version', version='Version: FIXME')
parser.add_argument('-i', '--importance', metavar='LEVEL', type=int, nargs='?', default=3, choices=range(1, 6), help='Specifies the importance level (1-5)')  # NOTE: range ends at 5
# Despite Android having an importance level 6, Pushjet does not have one
parser.add_argument('-l', '--link',       metavar='URL',   type=str, nargs='?', help='Specifies URL to open when selecting the notification')  # FIXME: Validate this URL, add a default
parser.add_argument('-t', '--title',      metavar='TITLE', type=str, nargs='?',   help='Specifies the title of the notification. Usually this would indicate the name of the application sending the notification', default=socket.gethostname().title())
parser.add_argument('body')
args = parser.parse_args()

pj_data = {
    'title': args.title,
    'message': args.body,
    'level': args.importance,
    'link': args.link,
    'secret': PUSHJET_SECRET,
}

encoded_data = urllib.parse.urlencode(pj_data).encode('utf-8')  # Encode the dict such that urllib.request will accept it
req = urllib.request.Request(PUSHJET_URL+'/message', encoded_data)
resp = urllib.request.urlopen(req)
if resp.getheader('content-type') != 'application/json':
    sys.stderr.write("Unexpected HTTP response type: {}\n\n".format(resp.getheader('content-type')))
    sys.stderr.write(str(resp.info()))
    sys.stderr.write(resp.read().decode())
    sys.exit(1)

response_data = json.loads(resp.read().decode())  # FIXME: Specify the codec?
assert response_data.get('status') == 'ok', response_data

