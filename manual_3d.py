
import opc, time

numLEDs = 512
client = opc.Client('treeled.local:7890')
pixels = [(0,0,0)] * numLEDs

colours = [
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
    # load csv with pixel 3d data
    with open('pixels.csv') as f:
        for i, line in enumerate(f):
            h,r,a = tuple(map(int, line.split('\t')))
            pixels[i] = colours[h]

    client.put_pixels(pixels)
    time.sleep(2)
