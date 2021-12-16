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
import subprocess
import sys
import urllib.parse

REAL_PASS_PATH = '/usr/bin/pass'
assert REAL_PASS_PATH != sys.argv[0]

if len(sys.argv) <= 1 or sys.argv[1] != 'show':
    # We do nothing here, just run the normal pass and move on
    # NOTE: The 2nd argument to execlp becomes the zero-th argument to the called binary
    os.execlp(REAL_PASS_PATH, REAL_PASS_PATH, *sys.argv[1:])

# Finds OTP tokens on a standalone line,
# OR on a line prefixed with 'OTP:'
# FIXME: What happens with multiple lines?
# FIXME: Don't call out to shell.
#        I figured this out for bash, then quickly realised it should be Python but CBFed fixing this part
real_pass = subprocess.Popen([REAL_PASS_PATH, *sys.argv[1:]], stdout=subprocess.PIPE, universal_newlines=True)
for line in real_pass.stdout.readlines():
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

        token = subprocess.check_output(['oathtool', '--base32',
                                         f'--{otp_uri.netloc}{"="+otp_qs["algorithm"].lower() if "algorithm" in otp_qs else ""}',
                                         *([f'--time-step-size={otp_qs["period"]}'] if 'period' in otp_qs else []),
                                         *([f'--digits={otp_qs["digits"]}'] if 'digits' in otp_qs else []),
                                         '-'
                                         ], input=otp_qs['secret'], universal_newlines=True)
        print(uri_raw)
        print('OTP Token:', token.strip())
    else:
        print(line)
