import opc
from colours import *

numLEDs = 512
client = opc.Client('treeled.local:7890')
pixels = [(0,0,0)] * numLEDs
colours = load_colours()

while True:
    try:
        colours = load_colours()
        # print("Colours reloaded")
    except:
        print("Error loading colours")

    for i in range(numLEDs):
        pixels[i] = colours[i%len(colours)]
    client.put_pixels(pixels)