#!/usr/bin/env python

import opc, time

# colours are
# GRB

numLEDs = 512
client = opc.Client('treeled.local:7890')
pixels = [(0,0,0)] * numLEDs
client.put_pixels(pixels)
time.sleep(2)
pixels = [(100,100,100)] * numLEDs
client.put_pixels(pixels)
time.sleep(2)

colors = [
        (0,255,0),
        (127,255,0),
        (255,255,0),
        (255,0,0),
        (150,0,150),
        (0,0,255),
        (0,75,130),
        (100,100,100)
    ]


while True:
    for i in range(numLEDs):
        print(i)
        pixels = [(0,0,0)] * numLEDs
        client.put_pixels(pixels)
        time.sleep(0.5)
        pixels[i] = (200,200,200)
        client.put_pixels(pixels)
        time.sleep(0.5)
