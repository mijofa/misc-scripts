#!/usr/bin/python3
"""
Get NetworkManager's VPN passwords & OTP tokens from password-store.

FIXME: Doesn't work properly with nm-applet, as nm-applet tries to fill that data before activating the connection.

Based mostly on the otp-agent from python3-networkmanager

NOTE: Logging output is somewhat sparse because I don't want to risk unencrypted passwords going into the logs.
"""

import sys
import pathlib
import urllib.parse

import dbus.mainloop.glib
from gi.repository import GLib
import NetworkManager

import pypass
import pyotp


class PassAgent(NetworkManager.SecretAgent):
    """Secret Agent for Network Manager."""

    def __init__(self, *args, password_store, **kwargs):
        """FIXME: Why does __init__ need a docstring specifically."""
        self.password_store = password_store
        super().__init__(*args, **kwargs)

    def pass_find(self, file_name):
        """Find pass entries matching file_name, similar to 'pass find'."""
        # NOTE: Using a generator makes this function much simpler,
        #       but I pretty much always want a re-usable list out of it
        for entry in self.password_store.get_passwords_list():
            p = pathlib.Path(entry)
            if file_name in p.name:
                yield entry

    def pass_show_and_otp(self, entry_name):
        """Get data from pass."""
        raw_data = self.password_store.get_decrypted_password(entry_name).splitlines()
        pass_data = {}

        if raw_data[0]:
            pass_data['password'] = raw_data[0]

        for line in raw_data[1:]:
            if not line:
                # Ignore blank lines
                pass
            elif line.startswith('otpauth://'):
                print("Found OTP line")
                otp_uri = urllib.parse.urlparse(line)
                otp_qs = {k: v for k, (v,) in urllib.parse.parse_qs(otp_uri.query).items()}
                assert otp_uri.scheme == 'otpauth'
                assert otp_uri.netloc in ('totp', 'hotp')
                assert 'secret' in otp_qs
                if otp_uri.netloc == 'hotp':
                    assert 'algorithm' not in otp_qs
                    assert 'period' not in otp_qs
                    raise NotImplementedError("Incrementing HOTP counters not currently supported")

                pass_data['otp'] = pyotp.TOTP(otp_qs['secret'], interval=int(otp_qs.get('period', 30))).now()
            else:
                if ':' in line:
                    k, _, v = line.partition(':')
                    if k == 'login':
                        k = 'user'
                    pass_data[k] = v.strip()

        return pass_data

    def GetSecrets(self, connection, connection_path, setting_name, hints, flags):
        """Respond with the necessary secrets."""
        print("NetworkManager is asking us for a secret")
        import pprint
        pprint.pprint(connection)
        print('setting_name', setting_name)
        print('hints', hints)
        print('flags', flags)

        if setting_name == 'vpn':
            # FIXME: The code I'm basing this off used 'remote' not 'gateway', why different?
            pass_entries = list(self.pass_find(connection[setting_name]['data']['gateway']))

            if len(pass_entries) == 1:
                print("Using pass entry:", pass_entries[0])
                return {setting_name: self.pass_show_and_otp(pass_entries[0])}
        elif setting_name == 'wireguard':
            # FIXME: Don't just grab the first peer, that's lazy.
            #        Although probably valid 90% of the time
            if len(connection[setting_name]['peers']) != 1:
                print(NotImplementedError("Currently only 1 WireGuard peer is supported at a time"), file=sys.stderr)
                raise NotImplementedError("Currently only 1 WireGuard peer is supported at a time")
            pass_entries = list(self.pass_find(connection[setting_name]['peers'][0]['endpoint'].partition(':')[0]))

            if len(pass_entries) == 1:
                print("Using pass entry:", pass_entries[0])
                # FIXME: How the fuck do I set the peer's preshared-key?
                pass_data = self.pass_show_and_otp(pass_entries[0])
                pass_data['private-key'] = pass_data.pop('password')
                return {setting_name: pass_data}
        else:
            # FIXME: What about WiFi PSKs?
            print(NotImplementedError(f"Unrecognised setting_name: {setting_name}"), file=sys.stderr)
            raise NotImplementedError(f"Unrecognised setting_name: {setting_name}")

        return {}

    # Useful for debugging  FIXME: Make this actually work?
    # @dbus.service.method(dbus_interface='org.freedesktop.NetworkManager.SecretAgent', in_signature='a{sa{sv}}o')
    # def SaveSecrets(self, connection, connection_path):
    #     """Print secret data to stdout for debugging."""
    #     print("NetworkManageer is asking to save a secret")
    #     import pprint
    #     pprint.pprint(connection)
    #     return True


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    loop = GLib.MainLoop()
    # FIXME: Does this automatically use $PASSWORD_STORE_DIR?
    PassAgent('mijofa.py.nm-pass-agent', password_store=pypass.PasswordStore())
    loop.run()
