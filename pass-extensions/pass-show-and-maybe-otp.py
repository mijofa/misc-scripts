#!/usr/bin/python3
"""
Wrapper around password-store to make OTP integrate nicer.

Mostly only created because qtpass is a bit annoying with how it integrates pass-extension-otp.
I recommend adding 'OTP Token' to your template in qtpass when using this.

This does make using qtpass to *edit* secrets with OTP tokens a bit annoying,
but that's easy to work around and doesn't happen nearly as often.
Qtpass's edit does a 'show' then you edit the output of that before it imports the updated version.
So the edit dialog will show the OTP token itself which must be manually removed before saving.
"""
import re
import os
# import subprocess
import sys
import urllib.parse

import pypass
import pyotp

# FIXME: Should I just trust the PATH for this?
REAL_PASS_PATH = '/usr/bin/pass'
assert REAL_PASS_PATH != sys.argv[0]

if len(sys.argv) != 3 or sys.argv[1] != 'show':
    # We do nothing here, just run the normal pass and move on
    # NOTE: The 2nd argument to execlp becomes the zero-th argument to the called binary
    os.execlp(REAL_PASS_PATH, REAL_PASS_PATH, *sys.argv[1:])

# FIXME: Does this honour the PASSWORD_STORE_DIR environment variable?
#        If not, do it yourself
password_store = pypass.PasswordStore()

if sys.argv[2] not in password_store.get_passwords_list():
    # Simulate the same error output 'pass' gives when the entry doesn't exist
    print(f"Error: {sys.argv[2]} is not in the password store.", file=sys.stderr)
    sys.exit(1)  # FIXME: Pretty sure I shouldn't call sys.exit directly, but I don't know how better to do this.

# Finds OTP tokens on a standalone line,
# OR on a line prefixed with 'OTP:'
pass_data = password_store.get_decrypted_password(sys.argv[2])
for line in pass_data.splitlines():
    line = line.strip()
    otp_re = re.fullmatch(r'^(OTP: )?(?P<uri>otpauth://.*)', line)
    if otp_re:
        uri_raw = otp_re.groupdict()['uri']
        otp_uri = urllib.parse.urlparse(uri_raw)
        otp_qs = {k: v for k, (v,) in urllib.parse.parse_qs(otp_uri.query).items()}
        assert otp_uri.scheme == 'otpauth'
        assert otp_uri.netloc in ('totp', 'hotp')
        assert 'secret' in otp_qs
        if otp_uri.netloc == 'hotp':
            assert 'algorithm' not in otp_qs
            assert 'period' not in otp_qs

            raise NotImplementedError("Incrementing HOTP counters not currently supported by this wrapper script")

        otp = pyotp.TOTP(otp_qs['secret'], interval=int(otp_qs.get('period', 30)))
        print(uri_raw)
        print('OTP Token:', otp.now())
    else:
        print(line)
