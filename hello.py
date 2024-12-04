#!/usr/bin/env python

import opc, time

# colours are 
# GRB

numLEDs = 512
client = opc.Client('localhost:7890')
pixels = [(0,0,0)] * numLEDs
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
    for i in range(8):
        for j in range(8):
            for c in range(64):
                if j == i:
                    pixels[j*64 + c] = colors[j]
                else:
                    pixels[j*64 + c] = colors[(i+1)%len(colors)]
        client.put_pixels(pixels)
        time.sleep(2)
