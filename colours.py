
def load_colours():
    colours = []
    with open('colours') as f:
        for line in f:
            name, colour = line.split(" ")
            g, r, b = colour.strip()[1:-1].split(",")
            colours.append((int(g), int(r), int(b)))
    return colours

if __name__ == "__main__":
    import opc

    numLEDs = 512
    client = opc.Client('treeled.local:7890')

    colours = load_colours()

    pixels = [(0,0,0)] * numLEDs


    x = 0
    c = 0
    while True:
        x+= 1
        if x%6000 == 0:
            c+=1
            try:
                colours = load_colours()
                print("Colours reloaded")
            except:
                print("Error loading colours")

            for i in range(numLEDs):
                pixels[i] = colours[c%len(colours)]
        client.put_pixels(pixels)
