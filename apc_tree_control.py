#!/usr/bin/env python3

"""
Control a FadeCandy/OPC-driven LED tree with an Akai APC Mini Mk2.

Mappings:
  Pads row 0 (notes 0–7): base color picker
  Pads row 1 (notes 8–15): accent color picker
  Scene buttons (notes 82–86): mode select (Solid, Twinkle, Swirl, Chase, Sparkle)
  Faders 1–9 (CC 48–56):
    1 base color, 2 accent color, 3 brightness, 4 speed, 5 twinkle density,
    6 chase length, 7 sparkle chance, 8 swirl phase, 9 master dimmer
"""

import math
import random
import threading
import time

import mido
from mido import Message

import opc

PORT_IN = "APC MINI"
PORT_OUT = "APC MINI"
OPC_ADDRESS = "treeled.local:7890"
LED_COUNT = 512
FPS = 50

# Simple palette; adjust to taste
PALETTE = [
    (0, 0, 0),        # 0 off
    (255, 0, 0),      # 1 red
    (0, 255, 0),      # 2 green
    (0, 0, 255),      # 3 blue
    (255, 255, 0),    # 4 yellow
    (255, 0, 255),    # 5 magenta
    (0, 255, 255),    # 6 cyan
    (255, 255, 255),  # 7 white
]

# APC Mini Mk2 uses a fixed 128-color table (velocity -> RGB). These entries align with PALETTE.
LED_COLOR_TABLE = [
    0,    # off
    5,    # red (#FF0000)
    21,   # green (#00FF00)
    45,   # blue (#0000FF)
    13,   # yellow (#FFFF00)
    53,   # magenta (#FF00FF)
    90,   # cyan-ish (#38FFCC)
    3,    # white (#FFFFFF)
]

# MIDI channel for pad LED feedback: 6 == solid at 100% brightness per protocol table.
LED_FEEDBACK_CHANNEL = 6

STATE = {
    "mode": 0,            # 0 solid, 1 twinkle, 2 swirl, 3 chase, 4 sparkle
    "base_color": 1,
    "accent_color": 2,
    "brightness": 1.0,
    "speed": 0.5,         # 0..1
    "twinkle_density": 0.2,
    "chase_length": 0.2,
    "swirl_phase": 0.0,
    "sparkle_chance": 0.1,
}

OPC_CLIENT = opc.Client(OPC_ADDRESS)
TWINKLE_CACHE = {"next_refresh": 0.0, "frame": [(0, 0, 0)] * LED_COUNT}


def mix(color, factor, brightness):
    return tuple(int(channel * factor * brightness) for channel in color)


def apply_animation(t):
    global TWINKLE_CACHE
    n = LED_COUNT
    base = PALETTE[STATE["base_color"]]
    accent = PALETTE[STATE["accent_color"]]
    brightness = STATE["brightness"]
    speed = max(0.05, STATE["speed"]) * 1.0
    buf = []

    if STATE["mode"] == 0:  # solid
        buf = [mix(base, 1.0, brightness)] * n
    elif STATE["mode"] == 1:  # twinkle (slower refresh)
        if t >= TWINKLE_CACHE["next_refresh"]:
            period = 0.1 + 0.5 * (1 - STATE["speed"])  # slower when speed fader is down
            TWINKLE_CACHE["next_refresh"] = t + period
            new_frame = []
            for _ in range(n):
                if random.random() > STATE["twinkle_density"]:
                    new_frame.append(mix(base, 0.4, brightness))
                else:
                    new_frame.append(mix(accent, random.random(), brightness))
            TWINKLE_CACHE["frame"] = new_frame
        buf = TWINKLE_CACHE["frame"]
    elif STATE["mode"] == 2:  # swirl (sin wave) with base as background
        phase = t * speed + STATE["swirl_phase"]
        for i in range(n):
            v = (math.sin((i / n) * math.tau + phase) + 1) / 2
            accent_mix = 0.2 + 0.8 * v
            # Blend base as a floor, accent rides on top.
            base_component = mix(base, 0.2, brightness)
            accent_component = mix(accent, accent_mix, brightness)
            buf.append(tuple(min(255, b + a) for b, a in zip(base_component, accent_component)))
    elif STATE["mode"] == 3:  # chase
        phase = int((t * speed * n)) % n
        length = max(1, int(STATE["chase_length"] * n))
        for i in range(n):
            dist = (i - phase) % n
            falloff = max(0, 1 - dist / length)
            buf.append(mix(accent, falloff, brightness))
    elif STATE["mode"] == 4:  # sparkle on base
        buf = [mix(base, 0.3, brightness)] * n
        for i in range(n):
            if random.random() < STATE["sparkle_chance"]:
                buf[i] = mix(accent, 1.0, brightness)
    return buf


def send_to_tree(pixels):
    # Reorder RGB -> GRB for LED strip wiring.
    pixels = [(g, r, b) for (r, g, b) in pixels]
    if len(pixels) < LED_COUNT:
        pixels = pixels + [(0, 0, 0)] * (LED_COUNT - len(pixels))
    elif len(pixels) > LED_COUNT:
        pixels = pixels[:LED_COUNT]
    return OPC_CLIENT.put_pixels(pixels)


def runner(stop_event):
    t0 = time.time()
    while not stop_event.is_set():
        frame = apply_animation(time.time() - t0)
        send_to_tree(frame)
        time.sleep(1.0 / FPS)


def set_pad_led(outport, note, color_idx, channel=LED_FEEDBACK_CHANNEL):
    outport.send(Message("note_on", note=note, velocity=color_idx, channel=channel))


def set_single_led(outport, note, on=True, blink=False):
    # Per protocol: channel 0, velocity 0=off, 1=on, 2=blink
    velocity = 2 if blink else (1 if on else 0)
    outport.send(Message("note_on", channel=0, note=note, velocity=velocity))


def light_mode_buttons(outport):
    base_note = 0x70  # Scene launch buttons 1-5
    for i in range(5):
        note = base_note + i
        set_single_led(outport, note, on=(i == STATE["mode"]), blink=False)


def light_color_grid(outport):
    for i in range(8):
        for j in range(8):
            set_pad_led(outport, j*8 + i, LED_COLOR_TABLE[i])


def handle_cc(msg):
    cc = msg.control
    val = msg.value / 127
    if cc == 48:
        STATE["base_color"] = int(val * (len(PALETTE) - 1))
    elif cc == 49:
        STATE["accent_color"] = int(val * (len(PALETTE) - 1))
    elif cc == 50:
        STATE["brightness"] = 0.1 + 0.9 * val
    elif cc == 51:
        STATE["speed"] = val
    elif cc == 52:
        STATE["twinkle_density"] = val
    elif cc == 53:
        STATE["chase_length"] = 0.05 + 0.9 * val
    elif cc == 54:
        STATE["sparkle_chance"] = val
    elif cc == 55:
        STATE["swirl_phase"] = val * math.tau
    elif cc == 56:
        STATE["brightness"] = 0.05 + val
    else:
        return False
    return True


def handle_note(msg, outport):
    note = msg.note
    vel = msg.velocity
    if msg.type == "note_on" and vel > 0:
        if 0 <= note <= 7:
            STATE["base_color"] = note
        elif 8 <= note <= 15:
            STATE["accent_color"] = note - 8
        elif 0x70 <= note <= 0x77:
            STATE["mode"] = note - 0x70
            print(f"Mode changed to {STATE['mode']} via note {note}")
        light_mode_buttons(outport)
        light_color_grid(outport)
        return True
    return False


def find_port(substring, ports):
    for name in ports:
        if substring.lower() in name.lower():
            return name
    raise RuntimeError(f'Port containing "{substring}" not found. Available: {ports}')


def main():
    random.seed()
    print(f"Sending OPC to {OPC_ADDRESS} for {LED_COUNT} LEDs")

    while True:
        try:
            in_name = find_port(PORT_IN, mido.get_input_names())
            out_name = find_port(PORT_OUT, mido.get_output_names())
            print(f"Using MIDI ports: {in_name} / {out_name}")

            stop_event = threading.Event()
            runner_thread = None

            with mido.open_input(in_name) as inp, mido.open_output(out_name) as outp:
                light_mode_buttons(outp)
                light_color_grid(outp)
                runner_thread = threading.Thread(target=runner, args=(stop_event,), daemon=True)
                runner_thread.start()
                try:
                    for msg in inp:
                        if msg.type == "control_change":
                            handle_cc(msg)
                        elif msg.type in ("note_on", "note_off"):
                            handle_note(msg, outp)
                except KeyboardInterrupt:
                    raise
                finally:
                    stop_event.set()
                    if runner_thread:
                        runner_thread.join()
                    send_to_tree([(0, 0, 0)] * LED_COUNT)
                    for note in range(0, 64):
                        set_pad_led(outp, note, 0)
                    for note in range(0x70, 0x78):
                        set_single_led(outp, note, on=False)

        except KeyboardInterrupt:
            print("Exiting on user request.")
            break
        except Exception as exc:
            # Catch ALSA/port errors, log, and retry.
            print(f"MIDI error: {exc}. Retrying in 2s...")
            time.sleep(2)


if __name__ == "__main__":
    main()
