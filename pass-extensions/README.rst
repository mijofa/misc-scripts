Pass Extensions
===============

A couple of extensions for use with `Pass <https://github.com/zx2c4/password-store>`_

Pass will not run extensions from the password store itself without setting PASSWORD_STORE_EXTENSIONS_ENABLE=true.
I would also recommend setting PASSWORD_STORE_SIGNING_KEY=true as well, and signing each extension appropriately

get-meta.bash
-------------
Gets the value of a key:value metadata line in the file.
Pretty much the same use-case as `https://github.com/rjekker/pass-extension-meta <pass-extension-meta>`_,
but much simpler.

Pass-extension-meta allowed for partial key matches,
complicated searches for multiple keys,
and even copying to clipboard directly.
This has none of that, but also doesn't need perl.

head.bash
---------
Gets **just** the password from the top line of the file.
Effectively the opposite of `https://github.com/palortoff/pass-extension-tail <pass-extension-tail>`_.

This will also leave out the newline character from the end of the line.

pass-show-and-maybe-otp.py
--------------------------
This is actually a **wrapper** to pass, for use with `QtPass <https://qtpass.org>`_.
QtPass is rather annoying to me in the UX of how it integrates the `OTP extension <https://github.com/tadfisher/pass-otp>`_.

That UX can't really be changed with a new extension, or by changing the OTP extension itself.
It requires actual changes to QtPass that I don't know where to begin, but I can workaround it with this messy wrapper.

Basically it just makes it so 'pass show' searches for OTP URIs in and runs them through oathtool directly every time.
Theoretically I could've done this as an extension like 'pass show-and-otp ...' but I wanted to use Python, which pass does not support.

ssh-add.bash
------------
Store SSH keys in pass and import them directly into your SSH agent without creating intermediary temporary files.
Equivalent to::

    ssh-add <(pass show foo)

ssh-agent.bash
--------------
Create a temporary SSH agent, import a key file from pass, run a command (sftp/rsync/scp), then close the agent.

I initially created this for sftp servers that close the connection after trying the first key from your agent,
before finding the last added one which will actually work.
This way the agent used by the sftp call only knows about the one needed for this specific server.

ssh.bash
--------
Allows for using keys, passwords, and OTP tokens from pass directly when SSHing to an external host.

Depends on `ssh-agent.bash`_, and `ssh.askpass-helper`_.

FIXME: Currently does not support passwords *and* keys at the same time, because when it identifies the pass file as a key it just calls out to ssh-agent.bash

ssh.askpass-helper
------------------
Only exists as a helper for `ssh.bash`_.
This is what SSH calls to get the passwords/etc from pass.
