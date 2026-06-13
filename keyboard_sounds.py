#!/usr/bin/env python3
"""
iPhone keyboard sounds for macOS.

Setup (once):
    pip install -r requirements.txt
    python3 prepare_sounds.py

Run:
    python3 keyboard_sounds.py

macOS requires Accessibility access for global key listening:
  System Settings → Privacy & Security → Accessibility → add Terminal (or your IDE).
"""

import random
import sys
from collections import defaultdict
from pathlib import Path

try:
    import pygame
except ImportError:
    sys.exit("Run: pip install -r requirements.txt")

try:
    from pynput import keyboard
except ImportError:
    sys.exit("Run: pip install -r requirements.txt")

SOUNDS_DIR = Path(__file__).parent / "sounds"

VOLUME = 1.0    # 0.0 – 1.0; adjust to taste
BUFFER = 256    # samples; lower = less latency (try 512 if you hear crackling)
CHANNELS = 16   # simultaneous sounds needed for fast typing


def load_sounds() -> dict[str, list[pygame.mixer.Sound]]:
    if not SOUNDS_DIR.exists() or not list(SOUNDS_DIR.glob("*.wav")):
        sys.exit(
            f"No sounds in {SOUNDS_DIR}/\n"
            "Run:  python3 prepare_sounds.py"
        )

    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=BUFFER)
    pygame.mixer.init()
    pygame.mixer.set_num_channels(CHANNELS)

    groups: dict[str, list[pygame.mixer.Sound]] = defaultdict(list)
    for wav in sorted(SOUNDS_DIR.glob("*.wav")):
        # "key_3.wav" → category "key"
        category = wav.stem.rsplit("_", 1)[0]
        snd = pygame.mixer.Sound(str(wav))
        snd.set_volume(VOLUME)
        groups[category].append(snd)

    summary = ", ".join(f"{k}×{len(v)}" for k, v in sorted(groups.items()))
    print(f"Sounds loaded: {summary}")
    return dict(groups)


_channel_cursor = 0


def play(sounds: dict, category: str) -> None:
    """Play a random variation from category, cycling through mixer channels."""
    global _channel_cursor
    pool = sounds.get(category) or sounds.get("key")
    if not pool:
        return
    ch = pygame.mixer.Channel(_channel_cursor % CHANNELS)
    ch.play(random.choice(pool))
    _channel_cursor += 1


def make_listener(sounds: dict):
    SPACE    = keyboard.Key.space
    BACK     = keyboard.Key.backspace
    DELETE   = keyboard.Key.delete
    ENTER    = keyboard.Key.enter
    SHIFTS   = {keyboard.Key.shift, keyboard.Key.shift_r,
                keyboard.Key.shift_l, keyboard.Key.caps_lock}

    def on_press(key):
        try:
            if key == SPACE:
                play(sounds, "space")
            elif key in (BACK, DELETE):
                play(sounds, "delete")
            elif key == ENTER:
                play(sounds, "return")
            elif key in SHIFTS:
                play(sounds, "modifier")
            elif hasattr(key, "char") and key.char:
                play(sounds, "key")
            # cmd, ctrl, fn, arrows, media keys → silent
        except Exception:
            pass

    return on_press


def main() -> None:
    sounds = load_sounds()
    print(f"iPhone keyboard sounds active (volume {VOLUME:.0%}). Ctrl+C to stop.\n")
    try:
        with keyboard.Listener(on_press=make_listener(sounds)) as kb:
            kb.join()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        pygame.mixer.quit()


if __name__ == "__main__":
    main()
