#!/usr/bin/env python3

import curses
import opc
import time


NUM_LEDS = 512
HOST = "127.0.0.1:7890"
STEP = 0.05  # 5% increments


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(value, max_value))


def render_level(client: opc.Client, brightness: float) -> None:
    """Send a uniform brightness level to all LEDs."""
    level = int(255 * brightness)
    pixels = [(level, level, level)] * NUM_LEDS
    client.put_pixels(pixels)


def draw_status(screen, brightness: float) -> None:
    screen.clear()
    screen.addstr(0, 0, "Brightness test")
    screen.addstr(1, 0, "Arrow Up/Down or +/- to adjust in 5% steps; q to quit.")
    screen.addstr(3, 0, f"Current brightness: {brightness * 100:5.1f}%")
    screen.refresh()


def main(stdscr) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    client = opc.Client(HOST)

    brightness = 0.5
    last_sent = None
    draw_status(stdscr, brightness)
    render_level(client, brightness)
    last_sent = brightness

    while True:
        key = stdscr.getch()

        if key in (ord("q"), ord("Q")):
            break
        elif key in (curses.KEY_UP, ord("+")):
            brightness = clamp(brightness + STEP)
        elif key in (curses.KEY_DOWN, ord("-")):
            brightness = clamp(brightness - STEP)

        if brightness != last_sent:
            draw_status(stdscr, brightness)
            render_level(client, brightness)
            last_sent = brightness

        time.sleep(0.05)


if __name__ == "__main__":
    curses.wrapper(main)
