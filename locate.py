
import opc, time
from colorsys import *
from random import random
import math
numLEDs = 512
client = opc.Client('treeled.local:7890')
pixels = [(0,0,0)] * numLEDs

t = 0

blips = {}


# vec3 palette( in float t, in vec3 a, in vec3 b, in vec3 c, in vec3 d )
# {
#     return a + b*cos( 6.283185*(c*t+d) );
# }

def palette( a, b, c, d):
    return lambda t: tuple([255*(a[i] + b[i]*math.cos(6.283185*(c[i]*t+d[i]))) for i in range(3)])
    # vec3                col = pal( p.x, vec3(0.5,0.5,0.5),vec3(0.5,0.5,0.5),vec3(1.0,1.0,1.0),vec3(0.0,0.33,0.67) );
    # if( p.y>(1.0/7.0) ) col = pal( p.x, vec3(0.5,0.5,0.5),vec3(0.5,0.5,0.5),vec3(1.0,1.0,1.0),vec3(0.0,0.10,0.20) );
    # if( p.y>(2.0/7.0) ) col = pal( p.x, vec3(0.5,0.5,0.5),vec3(0.5,0.5,0.5),vec3(1.0,1.0,1.0),vec3(0.3,0.20,0.20) );
    # if( p.y>(3.0/7.0) ) col = pal( p.x, vec3(0.5,0.5,0.5),vec3(0.5,0.5,0.5),vec3(1.0,1.0,0.5),vec3(0.8,0.90,0.30) );
    # if( p.y>(4.0/7.0) ) col = pal( p.x, vec3(0.5,0.5,0.5),vec3(0.5,0.5,0.5),vec3(1.0,0.7,0.4),vec3(0.0,0.15,0.20) );
    # if( p.y>(5.0/7.0) ) col = pal( p.x, vec3(0.5,0.5,0.5),vec3(0.5,0.5,0.5),vec3(2.0,1.0,0.0),vec3(0.5,0.20,0.25) );
    # if( p.y>(6.0/7.0) ) col = pal( p.x, vec3(0.8,0.5,0.4),vec3(0.2,0.4,0.2),vec3(2.0,1.0,1.0),vec3(0.0,0.25,0.25) );


def pal1(t):
    return palette((0.5,0.5,0.5), (0.5,0.5,0.5), (1.0,1.0,1.0), (0.0,0.33,0.67))(t)

def pal2(t):
    return palette((0.5,0.5,0.5), (0.5,0.5,0.5), (1.0,1.0,1.0), (0.0,0.10,0.20))(t)

def pal3(t):
    return palette((0.5,0.5,0.5), (0.5,0.5,0.5), (1.0,1.0,1.0), (0.3,0.20,0.20))(t)

def pal4(t):
    return palette((0.5,0.5,0.5), (0.5,0.5,0.5), (1.0,1.0,0.5), (0.8,0.90,0.30))(t)

def pal5(t):
    return palette((0.5,0.5,0.5), (0.5,0.5,0.5), (1.0,0.7,0.4), (0.0,0.15,0.20))(t)

# pink, aqua, blue, light green
def pal6(t):
    return palette((0.5,0.5,0.5), (0.5,0.5,0.5), (2.0,1.0,0.0), (0.5,0.20,0.25))(t)

def pal7(t):
    return palette((0.8,0.5,0.4), (0.2,0.4,0.2), (2.0,1.0,1.0), (0.0,0.25,0.25))(t)

def blue_palette(t):
    return palette((0,0,0), (0,0,0), (0.5, 0.5, 0.5), (0.5, 0.5, 0.5))(t)

random_pixel = [tuple([int(random()*255) for i in range(3)]) for i in range(512)]
random_hsv = [tuple([x*255 for x in hsv_to_rgb(random(), 1, 1)]) for i in range(512)]

def random_palette(height, time, pixel):
    return random_hsv[pixel] #tuple([int(random()*255) for i in range(3)])

def get_colour(height, time, pixel):
    return pal6(time/100 + pixel/50)

# random_palette(height, time, pixel)
# pal3(((time + height)/200.0)%1)

# (50, 50, 100 + 155*((height + time*1)%255)/255.0)
    tuple([x*255 for x in hsv_to_rgb(((height + time*1) %180)/360.0 + 180, 1, 0.5)])

while True:
    t += 1
    # load csv with pixel 3d data
    pixels = [(0,0,0)] * numLEDs

    with open('locations') as f:
        show, extra = f.read().split("extra")

        for line in show.split("\n"):
            if not line:
                continue
            # line is a string with the relevant metric the value and then a list of pixels
            # for example "h 1 1-5,7,28"
            # h is the metric, 1 is the value, and 1-5,7,28 are the pixels
            metric, value, pixelstr = line.split(" ")

            for pixel in pixelstr.split(","):
                if "-" in pixel:
                    start, end = pixel.split("-")
                    for i in range(int(start), int(end)+1):
                        col = get_colour(int(value), t, i)
                        pixels[i] = col
                else:
                    print(int(pixel))
                    pixels[int(pixel)] = col

        for i in range(512):
            if random() < 0.001 and i not in blips:
                blips[i] = 10

            if i in blips:
                pixels[i] = [x*math.cos(blips[i]/10)*3 for x in (200,200,180)]
                blips[i] -= 1

                if blips[i] == 0:
                    del blips[i]
    client.put_pixels(pixels)
    time.sleep(0.07)

