#!/usr/bin/env python

# Burn-in test: Keep LEDs at full brightness most of the time, but dim periodically
# so it's clear when there's a problem.

import opc, time

numLEDs = 512
client = opc.Client('treeled.local:7890')

while True:
	for i in range(numLEDs):
		pixels = [ (0,0,0) ] * numLEDs
		pixels[i] = (255, 255, 255)
		client.put_pixels(pixels)
		time.sleep(0.1)
