#!/usr/bin/python3
"""
Get NetworkManager's VPN passwords & OTP tokens from password-store.

FIXME: Doesn't work properly with nm-applet, as nm-applet tries to fill that data before activating the connection.

Based mostly on the otp-agent from python3-networkmanager

NOTE: Logging output is somewhat sparse because I don't want to risk unencrypted passwords going into the logs.
"""

import errno
import os
import pathlib
import socket
import subprocess
import sys
import urllib.parse

import systemd.daemon

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
        found = []
        for entry in self.password_store.get_passwords_list():
            p = pathlib.Path(entry)
            if p.name == file_name:
                found.append(p)

        if len(found) > 1:
            # If we've found more than 1 entry, let's see if there's 1 for use on this specific host.
            # Primarily for WiFi environments that use per-client PSKs and similar.
            hostname = socket.gethostname()
            # We can't just loop over found and remove each entry that's bogus because then the loop would go wrong,
            # Redefining the list is easier than trying to make a separate exceptions list or something trying to avoid conflict.
            found = [p for p in found if hostname in p.parts]

        if len(found) != 1:
            raise FileNotFoundError(errno.ENOENT, "File not found in password store", file_name)
        else:
            # NOTE: pypass doesn't support pathlib objects, so we convert it back to a string
            print("Found pass entry:", found[0])
            return str(found[0])

    def get_otp_token(self, otp_uri):
        """Get OTP token from a otpauth:// URI."""
        otp_uri = urllib.parse.urlparse(otp_uri)
        otp_qs = {k: v for k, (v,) in urllib.parse.parse_qs(otp_uri.query).items()}
        assert otp_uri.scheme == 'otpauth'
        assert otp_uri.netloc in ('totp', 'hotp')
        assert 'secret' in otp_qs
        if otp_uri.netloc == 'hotp':
            assert 'algorithm' not in otp_qs
            assert 'period' not in otp_qs
            raise NotImplementedError("Incrementing HOTP counters not currently supported")

        return pyotp.TOTP(otp_qs['secret'], interval=int(otp_qs.get('period', 30))).now()

    def pass_show_and_otp(self, entry_name):
        """Process data from pass into a more useful dict."""
        raw_data = self.password_store.get_decrypted_password(entry_name).splitlines()
        if not raw_data:
            raise FileNotFoundError(errno.ENOENT, "No pass data found", entry_name)

        pass_data = {}
        for line in raw_data[1:]:
            if not line:
                # Ignore blank lines
                pass
            elif line.startswith('otpauth://'):
                print("Found OTP URI, generating token")
                try:
                    otp_token = self.get_otp_token(line)
                except NotImplementedError as e:
                    # glib/dbus don't show exceptions anywhere,
                    # but we probably still want to make the password work here anyway,
                    # so continue.
                    print(e, file=sys.stderr)
                    pass
                else:
                    pass_data['otp'] = otp_token
            else:
                if ':' in line:
                    k, _, v = line.partition(': ')
                    if k == 'login':
                        k = 'user'
                    elif k.startswith('#') or ' ' in k:
                        # Ignore comment lines,
                        # and any key:value pairs that have a space in the key name, because it's probably not a real key
                        continue
                    pass_data[k] = v.strip()

        return raw_data[0], pass_data

    def get_connection_identifier(self, connection, setting_name):
        """Determine what filename to search for in pass, and what setting to apply it to in NetworkManager."""
        if setting_name == 'vpn':
            # FIXME: The code I'm basing this off used 'remote' not 'gateway', why different?
            return connection[setting_name]['data']['gateway'], 'password'
        elif setting_name == 'wireguard':
            # FIXME: Don't just grab the first peer, that's lazy.
            #        Although probably valid 90% of the time
            if len(connection[setting_name]['peers']) != 1:
                print(NotImplementedError("Currently only 1 WireGuard peer is supported at a time"), file=sys.stderr)
                raise NotImplementedError("Currently only 1 WireGuard peer is supported at a time")

            # FIXME: How the fuck do I set the peer's preshared-key?
            return connection[setting_name]['peers'][0]['endpoint'].partition(':')[0], 'private-key'
        elif setting_name in '802-11-wireless-security':
            if connection[setting_name]['key-mgmt'] != 'wpa-psk':
                # FIXME: Add support for other WiFi types
                print(NotImplementedError(f"Unsupported WiFi key-mgmt type: {connection[setting_name]['key-mgmt']}"),
                      file=sys.stderr)
                raise NotImplementedError(f"Unsupported WiFi key-mgmt type: {connection[setting_name]['key-mgmt']}")
            # I think NetworkManager is supposed to do this conversion itself, but doesn't.
            # Just in case I'm going to accept it properly if it has happened, so upgrades work
            if isinstance(connection['802-11-wireless']['ssid'], list):
                ssid = NetworkManager.fixups.ssid_to_python(connection['802-11-wireless']['ssid'])
            else:
                ssid = connection['802-11-wireless']['ssid']

            return ssid, 'psk'
        else:
            # FIXME: What about WiFi PSKs?
            print(NotImplementedError(f"Unrecognised setting_name: {setting_name}"), file=sys.stderr)
            raise NotImplementedError(f"Unrecognised setting_name: {setting_name}")

    def GetSecrets(self, connection, connection_path, setting_name, hints, flags):
        """Respond with the necessary secrets."""
        print(f"NetworkManager is asking us for a {setting_name} secret")
        # import pprint
        # pprint.pprint(connection)
        # print('setting_name', setting_name)
        # print('hints', hints)
        # print('flags', flags)

        pass_name, primary_secret_identifier = self.get_connection_identifier(connection, setting_name)
        primary_secret, pass_data = self.pass_show_and_otp(self.pass_find(pass_name))

        if primary_secret_identifier and primary_secret:
            pass_data[primary_secret_identifier] = primary_secret

        return {setting_name: pass_data}

    def generate_extra_secrets(self, connection, setting_name):
        """
        Generate the extra lines of data beyond the primary secret.

        Since each network type has different data this has to be unique for each one.
        """
        return_data = []
        if setting_name == 'wireguard':
            return_data.append('')
            return_data.append('[Interface]')
            # FIXME: IPv6?
            # FIXME: DNS?
            # FIXME: Are more than a single address supported in wg-quick config format? NM's data implies it is
            return_data.append(f"Address = {connection['ipv4']['addresses'][0][0]}/{connection['ipv4']['addresses'][0][1]}")
            return_data.append(f"PrivateKey = {connection[setting_name].get('private-key')}")
            for peer_config in connection[setting_name]['peers']:
                return_data.append('')
                # FIXME: GetSecrets only supports *reading* one peer
                return_data.append('[Peer]')
                return_data.append(f"Endpoint = {peer_config['endpoint']}")
                return_data.append(f"PresharedKey = {peer_config.get('preshared-key', '')}")
                return_data.append(f"PublicKey = {peer_config['public-key']}")
                return_data.append(f"AllowedIPs = {', '.join(peer_config['allowed-ips'])}")
        elif setting_name == 'vpn':
            return_data.append('')
            for key, value in connection[setting_name]['data'].items():
                if key.endswith('-flags'):
                    continue
                elif key == 'user':
                    key = 'login'

                return_data.append(f"{key}: {value}")
        else:
            print(f"Unknown setting_name '{setting_name}', can't continue generating secret extras.", file=sys.stderr)

        return return_data

    # NOTE: This one isn't specified python3-NetworkManager, which is why I need my own decorator here.
    # FIXME: If that's the case, should I just do that for everything here and get rid of that module entirely?
    @dbus.service.method(dbus_interface='org.freedesktop.NetworkManager.SecretAgent', in_signature='a{sa{sv}}o')
    def SaveSecrets(self, connection, connection_path):
        """Print secret data to stdout for debugging."""
        # NOTE: This 'fixups' is usually done internally in NetworkManager.py, but they don't care about supporting SaveSecrets.
        connection = NetworkManager.fixups.to_python('SecretAgent', 'GetSettings', 'connection', connection, 'a{sa{sv}}')
        setting_name = connection['connection']['type']

        if setting_name == '802-11-wireless':
            # NM asks for secrets with the '-security' setting_name, but saves them without.
            # Yet it still stores all the secrets in the '-security' setting, so just change to that for some consistency
            setting_name = '802-11-wireless-security'
        # FIXME: Is this more correct and stable?
        # if 'security' in connection[setting_name]:
        #     setting_name = connection[setting_name]['security']

        print(f"NetworkManageer is asking to save a {setting_name} secret")
        pass_name, primary_secret_identifier = self.get_connection_identifier(connection, setting_name)

        if 'secrets' in connection[setting_name]:
            # Fortisslvpn has this 'secrets' entry it stores the secret in,
            # I don't know if this is standard for most 'vpn' types or not
            primary_secret = connection[setting_name]['secrets'].get(primary_secret_identifier, None)
        else:
            primary_secret = connection[setting_name].get(primary_secret_identifier, None)
        if not primary_secret:
            # nm-connection-editor seems to just not ask for the secrets every 2nd time.
            # I don't understand why this happens, but if I hit "save" without making any changes that secret will be lost.
            # So just don't do anything if there's no secret to save anyway
            print("No primary secret provided, not saving", file=sys.stderr)
            return False

        try:
            pass_file = self.pass_find(pass_name)
        except FileNotFoundError:
            pass_file = f"NetworkManager/{socket.gethostname()}/{pass_name}"
            print(f"No pre-existing pass entry found for {pass_name}, creating {pass_file}")

        pass_lines = self.generate_extra_secrets(connection, setting_name)
        pass_lines.insert(0, primary_secret)
        old_pass_lines = self.password_store.get_decrypted_password(pass_file).splitlines()

        if len(pass_lines) == 1 and len(old_pass_lines) > 1:
            # If there's nothing more than the primary_secret,
            # try to keep whatever notes might be in the original file
            pass_lines.extend(old_pass_lines[1:])
        else:
            # Keep otpauth:// lines from old data because there's no nice place to store them in NM's data anyway
            pass_lines.extend([line for line in old_pass_lines if line.startswith('otpauth://')])

        if pass_lines != old_pass_lines:
            # FIXME: Make pypass support multiple lines in gpg-id
            subprocess.check_output(['pass', 'insert', '--multiline', pass_file],
                                    env={'PASSWORD_STORE_DIR': self.password_store.path},
                                    text=True, input='\n'.join(pass_lines))

        return True


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    loop = GLib.MainLoop()
    # FIXME: Does this automatically use $PASSWORD_STORE_DIR?
    PassAgent('mijofa.py.nm-pass-agent', password_store=pypass.PasswordStore(
        path=os.environ.get('PASSWORD_STORE_DIR', str(pathlib.Path('~/.password-store').expanduser()))))
    systemd.daemon.notify('READY=1')
    loop.run()
    systemd.daemon.notify('STOPPING=1')
