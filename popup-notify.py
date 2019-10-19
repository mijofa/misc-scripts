#!/usr/bin/python
import sys
import gtk

possible_responses = [ # I'm only using the one button at the moment, making this useless. I figured this will probably be useful later though.
    gtk.RESPONSE_ACCEPT,
    gtk.RESPONSE_APPLY,
    gtk.RESPONSE_CANCEL,
    gtk.RESPONSE_CLOSE,
    gtk.RESPONSE_DELETE_EVENT,
    gtk.RESPONSE_HELP,
    gtk.RESPONSE_NO,
    gtk.RESPONSE_NONE,
    gtk.RESPONSE_OK,
    gtk.RESPONSE_REJECT,
    gtk.RESPONSE_YES,
]

title = "Reminder"
if len(sys.argv) > 1 and sys.argv[1] != '':
  title = sys.argv[1]

#text = """Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.""" # I probably shouldn't set a default here and instead error out when this is empty, but having a default makes testing a tiny bit easier.
text = sys.stdin.read()

dialog = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK, message_format=None)
## I don't know why MessageDialog tries to hide from the taskbar, but it does and I don't like it, so I need to undo that here.
#dialog.set_skip_pager_hint(True)
dialog.set_skip_taskbar_hint(False)

dialog.set_title(title)
try: dialog.set_icon(dialog.image.get_pixbuf()) # This fails when using stock icons and I don't understand why, don't care enough either.
except: pass
#dialog.set_icon(dialog.image.get_pixbuf())
#i = gtk.Image()
#i.set_from_file()
dialog.label.set_text(text)
response = dialog.run()
dialog.destroy()

if response in possible_responses:
    print(possible_responses[possible_responses.index(response)].value_nick)
else:
    print("Unrecognized response.")

sys.exit(response*-1)
