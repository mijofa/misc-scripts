#!/usr/bin/python3
import datetime
import sys
import time


def apply_suffix(interval: float, suffix: str):
    """I want the arguments for this to be effectively the same as sleep(1).
    This function has the same affect as the sleep's function of the same name"""
    multiplier = 0
    if not suffix or suffix == 's':
        multiplier = 1
    elif suffix == 'm':
        multiplier = 60
    elif suffix == 'h':
        multiplier = 60 * 60
    elif suffix == 'd':
        multiplier = 60 * 60 * 60 * 24

    return interval * multiplier


if len(sys.argv) != 2 or '--help' in sys.argv:
    print("Usage: {} NUMBER[SUFFIX]".format(sys.argv[0]))
    print("Pause for NUMBER seconds and display a timer of how long is left.")
    print("SUFFIX may also be supplied using the same semantics as sleep(1).")
    sys.exit(1)

try:
    interval = float(sys.argv[1])
except ValueError:
    # Probably has a suffix, let's try again assuming a suffix.
    interval = apply_suffix(float(sys.argv[1][:-1]), sys.argv[1][-1])

delta = datetime.timedelta(seconds=interval)
end_time = datetime.datetime.now() + delta
print("Waiting for {delta}, until {end_time}".format(delta=delta, end_time=end_time))

try:
    while end_time > datetime.datetime.now():
        print("\33[2K", end='\r')  # VT100 escape sequence to clear the current line
        time_remaining = str(end_time - datetime.datetime.now())
        # The default string formatted output of a timedelta object includes microseconds.
        # I think I could use strftime, but I'm lazy so just going to split it on the '.'
        print(time_remaining.split('.')[0], flush=True, end='')
        time.sleep(1)
    print()
except KeyboardInterrupt:
    # Clear the line, and exit with an error status, but don't bother with printing an exception, it's annoying
    print()
    sys.exit(1)
