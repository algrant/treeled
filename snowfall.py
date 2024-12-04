#!/usr/bin/env python

import opc, time, random

client = opc.Client('treeled.local:7890')

numLEDs = 512
base_pixels = [(0,0,0)] * numLEDs
pixels = [(0,0,0)] * numLEDs

# initialize pixels to either red, white or green
colours = [
    (0,127,0),
    (127,127,127),
    (127,0,0),
    (127,0,0),
    (127,0,0)
]

# fire colour paletter
colours = [
    (0,0,0),
    (0,150,0),
    (70,180,0),
    (140,180,0)
]

# pastel colour palette
# colours = [
#     (80, 158, 180),
#     (180, 80, 158),
#     (158, 180, 80),
#     (180, 158, 80),
#     (80, 180, 158),
#     (158, 80, 180),
#     (180, 180, 80),
#     (180, 80, 180),
#     (80, 180, 180),
#     (180, 180, 158),
#     (158, 180, 180)
# ]


for i in range(numLEDs):
    base_pixels[i] = colours[random.randint(0,len(colours) - 1)]
    # (random.randint(0,120),random.randint(0,120),random.randint(0,120))
    pixels[i] = base_pixels[i]

while True:
    client.put_pixels(pixels)
    # randomly glow brighter every few seconds
    for i in range(numLEDs):
        if random.randint(0,100) > 75:
            pixels[i] = base_pixels[i] = colours[random.randint(0,len(colours) - 1)]
        else:
            pixels[i] = base_pixels[i]
    time.sleep(1)