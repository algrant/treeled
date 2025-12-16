#!/usr/bin/env python3

"""
Control a FadeCandy/OPC-driven LED tree with an Akai APC Mini Mk2.

Mappings:
  Pads row 0 (notes 0–7): base color picker
  Pads row 1 (notes 8–15): accent color picker
  Scene buttons (notes 0x70–0x76): mode select
    Solid, Twinkle, Swirl, Chase, Sparkle, Game, Spectrum (new multi-color wash)
    Spectrum scene: top-half pads set the primary hue, bottom-half pads set the secondary hue.
      Faders 5–8 tweak spread, brightness/value, saturation, and contrast for that wash.
  Faders 1–9 (CC 48–56):
    1 base/spectrum primary color, 2 accent/spectrum secondary, 3 brightness,
    4 speed, 5 twinkle density / spectrum spread, 6 chase length / spectrum value,
    7 sparkle chance / spectrum saturation, 8 swirl phase / spectrum contrast,
    9 master dimmer
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

MODE_SOLID = 0
MODE_TWINKLE = 1
MODE_SWIRL = 2
MODE_CHASE = 3
MODE_SPARKLE = 4
MODE_GAME = 5
MODE_SPECTRUM = 6
NUM_MODES = MODE_SPECTRUM + 1

STATE = {
    "mode": MODE_SOLID,   # 0 solid, 1 twinkle, 2 swirl, 3 chase, 4 sparkle, 5 game, 6 spectrum
    "base_color": 1,
    "accent_color": 2,
    "brightness": 1.0,
    "speed": 0.5,         # 0..1
    "twinkle_density": 0.2,
    "chase_length": 0.2,
    "swirl_phase": 0.0,
    "sparkle_chance": 0.1,
    "spectrum_primary_hue": 0.02,
    "spectrum_secondary_hue": 0.58,
    "spectrum_saturation": 1.0,
    "spectrum_value": 0.9,
    "spectrum_spread": 0.35,
    "spectrum_contrast": 0.8,
    "spectrum_primary_note": 0,     # top half grid controls primary hue
    "spectrum_secondary_note": 40,  # bottom half grid controls secondary hue
}

OPC_CLIENT = opc.Client(OPC_ADDRESS)
TWINKLE_CACHE = {"next_refresh": 0.0, "frame": [(0, 0, 0)] * LED_COUNT}
GAME_LEVELS = [
    {"size": 4, "speed": 2.0},
    {"size": 3, "speed": 2.5},
    {"size": 3, "speed": 3.0},
    {"size": 2, "speed": 3.5},
    {"size": 1, "speed": 4.0},
]
GAME_STATE = {
    "active": False,
    "level": 0,
    "pos": [2.0, 2.0],
    "vel": [1.0, 0.8],
    "size": 4,
}
GAME_FLASH_TIMER = 0.0
LAST_DT = 0.02


def clamp01(x):
    return max(0.0, min(1.0, x))


def lerp(a, b, t):
    return a + (b - a) * t


def hsv_to_rgb(h, s, v):
    h = h % 1.0
    s = clamp01(s)
    v = clamp01(v)
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i = i % 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return (int(r * 255), int(g * 255), int(b * 255))


def mix(color, factor, brightness):
    return tuple(int(channel * factor * brightness) for channel in color)


def apply_animation(t):
    global TWINKLE_CACHE, GAME_FLASH_TIMER
    n = LED_COUNT
    base = PALETTE[STATE["base_color"]]
    accent = PALETTE[STATE["accent_color"]]
    brightness = STATE["brightness"]
    speed = max(0.05, STATE["speed"]) * 1.0
    buf = []

    if STATE["mode"] == MODE_SOLID:  # solid
        buf = [mix(base, 1.0, brightness)] * n
    elif STATE["mode"] == MODE_TWINKLE:  # twinkle (slower refresh)
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
    elif STATE["mode"] == MODE_SWIRL:  # swirl (sin wave) with base as background
        phase = t * speed + STATE["swirl_phase"]
        for i in range(n):
            v = (math.sin((i / n) * math.tau + phase) + 1) / 2
            accent_mix = 0.2 + 0.8 * v
            # Blend base as a floor, accent rides on top.
            base_component = mix(base, 0.2, brightness)
            accent_component = mix(accent, accent_mix, brightness)
            buf.append(tuple(min(255, b + a) for b, a in zip(base_component, accent_component)))
    elif STATE["mode"] == MODE_CHASE:  # chase
        phase = int((t * speed * n)) % n
        length = max(1, int(STATE["chase_length"] * n))
        for i in range(n):
            dist = (i - phase) % n
            falloff = max(0, 1 - dist / length)
            buf.append(mix(accent, falloff, brightness))
    elif STATE["mode"] == MODE_SPARKLE:  # sparkle on base
        buf = [mix(base, 0.3, brightness)] * n
        for i in range(n):
            if random.random() < STATE["sparkle_chance"]:
                buf[i] = mix(accent, 1.0, brightness)
    elif STATE["mode"] == MODE_SPECTRUM:  # multi-color wash between two user hues
        spread = max(0.05, STATE["spectrum_spread"])
        contrast = clamp01(STATE["spectrum_contrast"])
        sat = clamp01(STATE["spectrum_saturation"])
        val = clamp01(STATE["spectrum_value"])
        scroll = (t * (0.5 + STATE["speed"] * 2.5)) / spread
        for i in range(n):
            pos = (i / n) + scroll
            wave = (math.sin(pos * math.tau) + 1) / 2
            blended = lerp(0.5, wave, contrast)  # pull extremes down when contrast < 1
            hue = lerp(STATE["spectrum_primary_hue"], STATE["spectrum_secondary_hue"], blended) % 1.0
            rgb = hsv_to_rgb(hue, sat, val)
            buf.append(mix(rgb, 1.0, brightness))
    elif STATE["mode"] == MODE_GAME:
        # Base glow with accent pulse; flash boost when the player hits the square.
        flash_boost = 1.0 + 0.8 * max(0.0, GAME_FLASH_TIMER)
        phase = t * (1.0 + GAME_STATE["level"] * 0.5)
        for i in range(n):
            v = (math.sin((i / n) * math.tau + phase) + 1) / 2
            accent_mix = 0.2 + 0.6 * v
            base_component = mix(base, 0.2, brightness)
            accent_component = mix(accent, accent_mix * flash_boost, brightness)
            buf.append(tuple(min(255, b + a) for b, a in zip(base_component, accent_component)))
    return buf


def send_to_tree(pixels):
    # Reorder RGB -> GRB for LED strip wiring.
    pixels = [(g, r, b) for (r, g, b) in pixels]
    if len(pixels) < LED_COUNT:
        pixels = pixels + [(0, 0, 0)] * (LED_COUNT - len(pixels))
    elif len(pixels) > LED_COUNT:
        pixels = pixels[:LED_COUNT]
    return OPC_CLIENT.put_pixels(pixels)


def runner(stop_event, outport):
    global LAST_DT
    t0 = time.time()
    last = t0
    while not stop_event.is_set():
        now = time.time()
        dt = now - last
        LAST_DT = dt
        last = now
        update_game(outport, dt)
        frame = apply_animation(now - t0)
        send_to_tree(frame)
        time.sleep(max(0.0, (1.0 / FPS) - (time.time() - now)))


def set_pad_led(outport, note, color_idx, channel=LED_FEEDBACK_CHANNEL):
    outport.send(Message("note_on", note=note, velocity=color_idx, channel=channel))


def set_single_led(outport, note, on=True, blink=False):
    # Per protocol: channel 0, velocity 0=off, 1=on, 2=blink
    velocity = 2 if blink else (1 if on else 0)
    outport.send(Message("note_on", channel=0, note=note, velocity=velocity))


def light_mode_buttons(outport):
    base_note = 0x70  # Scene launch buttons
    for i in range(NUM_MODES):
        note = base_note + i
        set_single_led(outport, note, on=(i == STATE["mode"]), blink=False)


def draw_palette_grid(outport):
    for i in range(8):
        for j in range(8):
            set_pad_led(outport, j * 8 + i, LED_COLOR_TABLE[i])


def draw_game_grid(outport):
    size = GAME_STATE["size"]
    px, py = GAME_STATE["pos"]
    top = int(round(py))
    left = int(round(px))
    # Clear grid
    for i in range(64):
        set_pad_led(outport, i, 0)
    # Draw square
    color = LED_COLOR_TABLE[STATE["accent_color"] % len(LED_COLOR_TABLE)]
    for y in range(top, min(8, top + size)):
        for x in range(left, min(8, left + size)):
            note = y * 8 + x
            set_pad_led(outport, note, color)


def apc_color_index_from_rgb(rgb):
    # APC Mini Mk2 color table is 7-bit. Packing 2 bits per channel gives a coarse but colorful grid.
    r, g, b = rgb
    r_idx = min(3, int(r / 64))
    g_idx = min(3, int(g / 64))
    b_idx = min(3, int(b / 64))
    return max(1, min(127, 1 + r_idx + g_idx * 4 + b_idx * 16))


def spectrum_note_to_hue(note):
    row, col = divmod(note, 8)
    hue = col / 8.0
    return row, hue


def draw_spectrum_grid(outport):
    for note in range(64):
        row, hue = spectrum_note_to_hue(note)
        # Top half selects primary, bottom half selects secondary. Rows fade saturation/value.
        within_band = row % 4
        sat = 0.55 + 0.45 * (1 - within_band / 3)
        val = 0.65 + 0.35 * (1 - within_band / 3)
        rgb = hsv_to_rgb(hue, sat, val)
        velocity = apc_color_index_from_rgb(rgb)
        # Highlight the last picked pad for each hue band by boosting velocity.
        if note in (STATE["spectrum_primary_note"], STATE["spectrum_secondary_note"]):
            velocity = min(127, velocity + 8)
        set_pad_led(outport, note, velocity)


def refresh_grid(outport):
    if STATE["mode"] == MODE_GAME:
        draw_game_grid(outport)
    elif STATE["mode"] == MODE_SPECTRUM:
        draw_spectrum_grid(outport)
    else:
        draw_palette_grid(outport)


def handle_cc(msg):
    cc = msg.control
    val = msg.value / 127
    if cc == 48:
        STATE["base_color"] = int(val * (len(PALETTE) - 1))
        if STATE["mode"] == MODE_SPECTRUM:
            STATE["spectrum_primary_hue"] = val
            # Keep highlight tied roughly to the column the fader implies.
            STATE["spectrum_primary_note"] = int(round(val * 7))
    elif cc == 49:
        STATE["accent_color"] = int(val * (len(PALETTE) - 1))
        if STATE["mode"] == MODE_SPECTRUM:
            STATE["spectrum_secondary_hue"] = val
            STATE["spectrum_secondary_note"] = 40 + int(round(val * 7))
    elif cc == 50:
        STATE["brightness"] = 0.1 + 0.9 * val
    elif cc == 51:
        STATE["speed"] = val
    elif cc == 52:
        STATE["twinkle_density"] = val
        if STATE["mode"] == MODE_SPECTRUM:
            STATE["spectrum_spread"] = 0.05 + 1.2 * val
    elif cc == 53:
        STATE["chase_length"] = 0.05 + 0.9 * val
        if STATE["mode"] == MODE_SPECTRUM:
            STATE["spectrum_value"] = 0.35 + 0.65 * val
    elif cc == 54:
        STATE["sparkle_chance"] = val
        if STATE["mode"] == MODE_SPECTRUM:
            STATE["spectrum_saturation"] = 0.4 + 0.6 * val
    elif cc == 55:
        STATE["swirl_phase"] = val * math.tau
    elif cc == 56:
        STATE["brightness"] = 0.05 + val
        if STATE["mode"] == MODE_SPECTRUM:
            STATE["spectrum_contrast"] = 0.35 + 0.65 * val
    else:
        return False
    return True


def handle_note(msg, outport):
    note = msg.note
    vel = msg.velocity
    if msg.type == "note_on" and vel > 0:
        if STATE["mode"] == MODE_GAME and 0 <= note <= 63:
            row, col = divmod(note, 8)
            if is_hit(row, col):
                handle_game_hit(outport)
        elif STATE["mode"] == MODE_SPECTRUM and 0 <= note <= 63:
            row, hue = spectrum_note_to_hue(note)
            if row < 4:
                STATE["spectrum_primary_hue"] = hue
                STATE["spectrum_primary_note"] = note
            else:
                STATE["spectrum_secondary_hue"] = hue
                STATE["spectrum_secondary_note"] = note
        elif 0 <= note <= 7:
            STATE["base_color"] = note
        elif 8 <= note <= 15:
            STATE["accent_color"] = note - 8
        elif 0x70 <= note <= 0x76:
            STATE["mode"] = min(MODE_SPECTRUM, note - 0x70)
            print(f"Mode changed to {STATE['mode']} via note {note}")
            if STATE["mode"] == MODE_GAME:
                reset_game()
        light_mode_buttons(outport)
        refresh_grid(outport)
        return True
    return False


def find_port(substring, ports):
    for name in ports:
        if substring.lower() in name.lower():
            return name
    raise RuntimeError(f'Port containing "{substring}" not found. Available: {ports}')


def reset_game():
    GAME_STATE["active"] = True
    GAME_STATE["level"] = 0
    apply_game_level()


def apply_game_level():
    cfg = GAME_LEVELS[GAME_STATE["level"]]
    GAME_STATE["size"] = cfg["size"]
    GAME_STATE["pos"] = [random.uniform(0, 8 - cfg["size"]), random.uniform(0, 8 - cfg["size"])]
    # Random velocity direction, normalized to cfg speed.
    angle = random.uniform(0, math.tau)
    GAME_STATE["vel"] = [math.cos(angle) * cfg["speed"], math.sin(angle) * cfg["speed"]]


def update_game(outport, dt):
    global GAME_FLASH_TIMER
    if STATE["mode"] != MODE_GAME:
        GAME_STATE["active"] = False
        return
    if not GAME_STATE["active"]:
        reset_game()
        refresh_grid(outport)
        return

    cfg = GAME_LEVELS[GAME_STATE["level"]]
    size = cfg["size"]
    px, py = GAME_STATE["pos"]
    vx, vy = GAME_STATE["vel"]

    px += vx * dt
    py += vy * dt

    # Bounce on edges
    if px < 0:
        px = -px
        vx = abs(vx)
    if py < 0:
        py = -py
        vy = abs(vy)
    if px + size > 8:
        px = 8 - size
        vx = -abs(vx)
    if py + size > 8:
        py = 8 - size
        vy = -abs(vy)

    GAME_STATE["pos"] = [px, py]
    GAME_STATE["vel"] = [vx, vy]
    refresh_grid(outport)

    GAME_FLASH_TIMER = max(0.0, GAME_FLASH_TIMER - dt)


def is_hit(row, col):
    size = GAME_STATE["size"]
    px, py = GAME_STATE["pos"]
    return (px <= col < px + size) and (py <= row < py + size)


def handle_game_hit(outport):
    global GAME_FLASH_TIMER
    # Cycle colors for fun
    STATE["base_color"] = (STATE["base_color"] + 1) % len(PALETTE)
    STATE["accent_color"] = (STATE["accent_color"] + 2) % len(PALETTE)
    # Level up to max 4
    if GAME_STATE["level"] < len(GAME_LEVELS) - 1:
        GAME_STATE["level"] += 1
        apply_game_level()
    GAME_FLASH_TIMER = 1.5
    refresh_grid(outport)


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
                refresh_grid(outp)
                runner_thread = threading.Thread(target=runner, args=(stop_event, outp), daemon=True)
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
