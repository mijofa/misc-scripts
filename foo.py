import json
import operator
import PIL.Image
import PIL.ImageStat
import time
import urllib.request
import Xlib.display

# FIXME: Config or cmdline switch this
sonoff_hostname = 'sonoff-6810'


# This function mostly copied from here: https://rosettacode.org/wiki/Color_of_a_screen_pixel#Python
o_x_root = Xlib.display.Display().screen().root
o_x_geo = o_x_root.get_geometry()
o_x_geo.height = int(o_x_geo.height / 4)
def get_x_image():  # noqa: E302
    o_x_image = o_x_root.get_image(0, 0, o_x_geo.width, o_x_geo.height, Xlib.X.ZPixmap, 0xffffffff)
    o_pil_image_rgb = PIL.Image.frombytes("RGB", (o_x_geo.width, o_x_geo.height), o_x_image.data, "raw", "BGRX")
    return o_pil_image_rgb


# This function mostly copied from: https://zeevgilovitz.com/detecting-dominant-colours-in-python
def most_frequent_colour(image):
    w, h = image.size
    pixels = image.getcolors(w * h)

    # Pixels is a list of tuples,
    # the first item is the number of occurences,
    # the 2nd item is the RGB of a particular colour.
    #
    # operator.itemgetter(0) is a more efficient alternative to:
    #     lambda i: i[0]
    # Do I actually need a key at all though?
    # I seem to get the same result with & without,
    # but I don't know if that's the expected behaviour or just fluke
    most_frequent_pixel = max(pixels, key=operator.itemgetter(0))

## This is dumb & inefficient
#    most_frequent_pixel = pixels[0]
#    for count, colour in pixels:
#        if count > most_frequent_pixel[0]:
#            most_frequent_pixel = (count, colour)

## I have no idea what this function was supposed to be, but everything works without it
#    compare("Most Common", image, most_frequent_pixel[1])

    return most_frequent_pixel


# Maybe give it just a little white so that the light is never really off?
white = 0
def update_sonoff_colour(red, green, blue):  # noqa: E302
    # Make sure all the colours are at least 1,
    # otherwise the light bulb will turn off and not come back on automatically
    red = max(1, red)
    green = max(1, green)
    blue = max(1, blue)

    # NOTE: Tasmota has been told not to power the globe on when setting the color via the SetOption20 config command
    # NOTE: "Color2" = Set color adjusted to current Dimmer value.
    #       We don't actually want that though because that'd make 1,1,1 just be pure white.
    command = f"Color1 {red},{green},{blue},{white}"
    req = urllib.request.Request(f"http://{sonoff_hostname}/cm",
                                 data=f"cmnd={command}".encode('ascii'))
    return json.load(urllib.request.urlopen(req))


prev_colour = None
while True:
    time.sleep(0.10)
    _, colour = most_frequent_colour(get_x_image())
    if colour != prev_colour:
        prev_colour = colour
        try:
            print(update_sonoff_colour(*colour))
        except urllib.request.http.client.RemoteDisconnected as e:
            # "Remote end closed connection without response"
            # Transient? Let's just try again and see what happens
            print(e)
            print(update_sonoff_colour(*colour))
