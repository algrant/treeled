
import opc, time
from colorsys import *
from random import random
import math
numLEDs = 512
client = opc.Client('treeled.local:7890')
pixels = [(0,0,0)] * numLEDs

t = 0

blips = {}

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
            col = tuple([x*255 for x in hsv_to_rgb(((int(value) + t*1) %360)/360.0, 1, 0.5)])
            for pixel in pixelstr.split(","):
                if "-" in pixel:
                    start, end = pixel.split("-")
                    for i in range(int(start), int(end)+1):
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

