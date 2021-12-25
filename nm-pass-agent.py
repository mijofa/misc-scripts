#!/usr/bin/python3
"""
Get NetworkManager's VPN passwords & OTP tokens from password-store.

FIXME: Doesn't work properly with nm-applet, as nm-applet tries to fill that data before activating the connection.

Based mostly on the otp-agent from python3-networkmanager

NOTE: Logging output is somewhat sparse because I don't want to risk unencrypted passwords going into the logs.
"""

import pathlib
import socket
import sys
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
        found = []
        for entry in self.password_store.get_passwords_list():
            p = pathlib.Path(entry)
            if p.name == file_name:
                found.append(p)

        if len(found) > 1:
            # If we've found more than 1 entry, let's see if there's 1 for use on this specific host.
            # Primarily for WiFi environments that use per-client PSKs and similar.
            hostname = socket.gethostname()
            for p in found:
                if hostname not in p.parts:
                    found.pop(p)

        if len(found) != 1:
            raise FileNotFoundError("Can't find the required entry in the password-store")
        else:
            # NOTE: pypass doesn't support pathlib objects, so we convert it back to a string
            print("Using pass entry:", found[0])
            return str(found[0])

    def pass_show_and_otp(self, entry_name):
        """Get data from pass."""
        raw_data = self.password_store.get_decrypted_password(entry_name).splitlines()
        pass_data = {}

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

        return raw_data[0], pass_data

    def GetSecrets(self, connection, connection_path, setting_name, hints, flags):
        """Respond with the necessary secrets."""
        print(f"NetworkManager is asking us for {setting_name} a secret")
        # import pprint
        # pprint.pprint(connection)
        # print('setting_name', setting_name)
        # print('hints', hints)
        # print('flags', flags)

        if setting_name == 'vpn':
            # FIXME: The code I'm basing this off used 'remote' not 'gateway', why different?
            password, pass_data = self.pass_show_and_otp(self.pass_find(connection[setting_name]['data']['gateway']))

            pass_data['password'] = password
            return {setting_name: pass_data}
        elif setting_name == 'wireguard':
            # FIXME: Don't just grab the first peer, that's lazy.
            #        Although probably valid 90% of the time
            if len(connection[setting_name]['peers']) != 1:
                print(NotImplementedError("Currently only 1 WireGuard peer is supported at a time"), file=sys.stderr)
                raise NotImplementedError("Currently only 1 WireGuard peer is supported at a time")

            # FIXME: How the fuck do I set the peer's preshared-key?
            private_key, pass_data = self.pass_show_and_otp(self.pass_find(
                connection[setting_name]['peers'][0]['endpoint'].partition(':')[0]))

            pass_data['private-key'] = private_key
            return {setting_name: pass_data}
        elif setting_name == '802-11-wireless-security':
            psk, pass_data = self.pass_show_and_otp(self.pass_find(
                b''.join(connection['802-11-wireless']['ssid']).decode()))

            pass_data['psk'] = psk
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
