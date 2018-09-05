#!/usr/bin/python3
#import os
#import sys
import getpass
import smtplib
#from email import encoders
#from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import unquote
from gi.repository import Notify


def sendmail(server, port, recipients, msg):
#    with smtplib.SMTP(server, port) as s:
    ## FIXME: ^ that syntax didn't work on Kaylee, suspect Python version mismatch is to blame
    s = smtplib.SMTP(server, port)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.sendmail(msg['From'], recipients, msg.as_string())
    s.close()

def genmail(sender, recipient, magnets):
    outer = MIMEMultipart()

    outer['To'] = recipient
    outer['From'] = sender

    if len(magnets) > 1:
        outer['Subject'] = "{} magnet links".format(len(magnets))
    elif len(magnets) == 1:
        for i in magnets[0].split('&'):
            if i.startswith('dn='):
                outer['Subject'] = unquote(i[3:])
        if not outer['Subject']:
            # Magnet links aren't required to have the 'dn' attribute
            outer['Subject'] = "1 magnet link"

    outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'

    outer.attach(MIMEText(
        '\n'.join(magnets), 'plain'
    ))

    ## FIXME: Future improvement, handle torrent files as well.
#    # List of attachments
#    attachments = ['FULL PATH TO ATTACHMENTS HERE']
#    
#    # Add the attachments to the message
#    for file in attachments:
#        try:
#            with open(file, 'rb') as fp:
#                msg = MIMEBase('application', "octet-stream")
#                msg.set_payload(fp.read())
#            encoders.encode_base64(msg)
#            msg.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file))
#            outer.attach(msg)
#        except:
#            print("Unable to open one of the attachments. Error: ", sys.exc_info()[0])
#            raise

    return outer


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Email magnet links for automatic torrenting",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    username = getpass.getuser()
    # FIXME: Use a config file as well
    parser.add_argument('magnets',          metavar='MAGNET-LINK', help="The magnet link you wish to email", nargs='+')
    parser.add_argument('--server',   '-s', metavar='SMTP-SERVER', help="Specify an alternate SMTP server",   default=REPLACEME)
    parser.add_argument('--port',     '-p', metavar='SMTP-PORT',   help="Specify an alternate SMTP port",     default=25)
    parser.add_argument('--from',     '-f', metavar='FROM',        help="Specify who the email will be from", default=username, dest='sender')
    parser.add_argument('--recipient','-r', metavar='RECIPIENT',   help="Specify who the email will go to",   default=REPLACEME)

    args = parser.parse_args()

    assert all(i.startswith('magnet:') for i in args.magnets), "Magnet links must start with 'magnet:'"

    msg = genmail(args.sender, args.recipient, args.magnets)
    sendmail(args.server, args.port, args.recipient, msg)

    Notify.init(parser.prog)
    Notify.Notification.new(parser.prog,"Sent email '{}'".format(msg['Subject']), 'mail-send').show()

