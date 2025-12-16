

"""
Setup & Calibrate a FadeCandy/OPC-driven LED tree with an Akai APC Mini Mk2.

Opens and modifies a local file (config.json) based on inputs.


Mappings:
  The top 8 scene buttons are used to toggle whether or not a string of lights is on/off
  The Fader C

Mappings:
  Pads row 0 (notes 0–7): base color picker
  Pads row 1 (notes 8–15): accent color picker
  Scene buttons (notes 0x70–0x75): mode select (Solid, Twinkle, Swirl, Chase, Sparkle, Game)
  Faders 1–9 (CC 48–56):
    1 base color, 2 accent color, 3 brightness, 4 speed, 5 twinkle density,
    6 chase length, 7 sparkle chance, 8 swirl phase, 9 master dimmer
"""