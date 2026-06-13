#!/usr/bin/env python3
"""
Extract iPhone keyboard sounds from the iOS Simulator runtime and generate
pitch-shifted variations so rapid typing doesn't sound monotonous.

Run once before keyboard_sounds.py:
    python3 prepare_sounds.py
"""

import glob
import subprocess
import sys
from pathlib import Path

try:
    import numpy as np
    import soundfile as sf
except ImportError:
    sys.exit("Install deps first: pip install -r requirements.txt")

SOUNDS_DIR = Path(__file__).parent / "sounds"
SOUNDS_DIR.mkdir(exist_ok=True)

# Source CAF file for each sound category
SOUND_MAP = {
    "key":      "key_press_click.caf",    # 4ms crisp tick — the real iPhone key click
    "space":    "key_press_click.caf",
    "delete":   "key_press_delete.caf",   # 15ms — distinct delete sound
    "modifier": "key_press_modifier.caf", # 19ms — shift/caps
    "return":   "key_press_click.caf",
}

# Pitch offsets in semitones per category — keep variation subtle like real iPhone
VARIATIONS = {
    "key":      [0],
    "space":    [0],
    "delete":   [0],
    "modifier": [0],
    "return":   [0],
}


def find_simulator_sounds() -> Path | None:
    """Return the UISounds path from the newest installed iOS Simulator runtime."""
    patterns = [
        "/Library/Developer/CoreSimulator/Volumes/*/Library/Developer/CoreSimulator"
        "/Profiles/Runtimes/*.simruntime/Contents/Resources/RuntimeRoot"
        "/System/Library/Audio/UISounds",
        "~/Library/Developer/CoreSimulator/Volumes/*/Library/Developer/CoreSimulator"
        "/Profiles/Runtimes/*.simruntime/Contents/Resources/RuntimeRoot"
        "/System/Library/Audio/UISounds",
    ]
    found = []
    for pat in patterns:
        found.extend(glob.glob(str(Path(pat).expanduser())))
    if not found:
        return None
    return Path(sorted(found)[-1])  # newest runtime last alphabetically


def convert_caf_to_wav(src: Path, dst: Path) -> None:
    """Use macOS afconvert to produce a 44100 Hz stereo 16-bit WAV."""
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "2", str(src), str(dst)],
        check=True,
        capture_output=True,
    )


def pitch_shift(data: np.ndarray, semitones: float) -> np.ndarray:
    """
    Resample audio data to shift pitch (and proportionally speed) by semitones.
    Works well for short transients; the tiny duration change is inaudible on clicks.
    """
    if semitones == 0:
        return data
    factor = 2 ** (semitones / 12)
    n_orig = len(data)
    n_new = max(1, int(round(n_orig / factor)))
    indices = np.linspace(0, n_orig - 1, n_new)
    src = np.arange(n_orig)
    if data.ndim == 1:
        return np.interp(indices, src, data).astype(data.dtype)
    return np.column_stack(
        [np.interp(indices, src, data[:, ch]).astype(data.dtype) for ch in range(data.shape[1])]
    )


def main() -> None:
    sim_dir = find_simulator_sounds()
    if sim_dir is None:
        sys.exit(
            "Could not find iOS Simulator sounds.\n"
            "Install Xcode and download at least one iOS Simulator runtime:\n"
            "  Xcode → Settings → Platforms → iOS"
        )
    print(f"Simulator sounds: {sim_dir}\n")

    # Remove any previously generated WAV files so stale variations don't linger
    for old in SOUNDS_DIR.glob("*.wav"):
        old.unlink()

    # Convert each unique CAF file once, then generate variations
    converted: dict[str, tuple[np.ndarray, int]] = {}

    for category, caf_name in SOUND_MAP.items():
        src = sim_dir / caf_name
        if not src.exists():
            print(f"  WARNING: {caf_name} not found — skipping '{category}'")
            continue

        if caf_name not in converted:
            tmp = SOUNDS_DIR / f"_tmp_{Path(caf_name).stem}.wav"
            print(f"Converting {caf_name}...")
            convert_caf_to_wav(src, tmp)
            data, sr = sf.read(str(tmp), dtype="float32")
            converted[caf_name] = (data, sr)
            tmp.unlink()

        data, sr = converted[caf_name]

        for i, st in enumerate(VARIATIONS[category], 1):
            out = SOUNDS_DIR / f"{category}_{i}.wav"
            shifted = pitch_shift(data, st)
            sf.write(str(out), shifted, sr, subtype="PCM_16")
            sign = "+" if st > 0 else ""
            print(f"  {out.name}  ({sign}{st} semitones)")

    total = len(list(SOUNDS_DIR.glob("*.wav")))
    print(f"\nDone — {total} WAV files written to sounds/")


if __name__ == "__main__":
    main()
