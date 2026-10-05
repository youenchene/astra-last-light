#!/usr/bin/env python3
"""Render Astra's original, deterministic synth bank using only the stdlib."""

import math
from pathlib import Path
import random
import struct
import wave


RATE = 22050
OUTPUT = Path(__file__).resolve().parents[1] / "game/sound/samples"
C3 = 130.8127826502993
C4 = C3 * 2


def envelope(t, duration, attack, decay):
    """Smooth both boundaries before AGK's signed eight-bit conversion."""
    fade_in = math.sin(min(1.0, t / attack) * math.pi / 2) ** 2
    fade_out = min(1.0, (duration - t) / (duration * 0.3)) ** 2
    return fade_in * fade_out * math.exp(-decay * t)


def warm_wave(phase):
    return sum(math.sin(phase * h) / h ** 2 for h in range(1, 7))


def pad(t):
    # Root/fifth and detuning are baked into ONE mono sample, not extra voices.
    root = sum(warm_wave(math.tau * C4 * ratio * t)
               for ratio in (0.996, 1.004)) / 2
    fifth = 0.28 * warm_wave(math.tau * C4 * 1.498307 * t)
    return (root + fifth) * envelope(t, 0.52, 0.045, 1.1)


def lead(t):
    phase = math.tau * C4 * t + 0.018 * math.sin(math.tau * 4 * t)
    tone = math.sin(phase) + 0.22 * math.sin(2 * phase) + 0.06 * math.sin(3 * phase)
    return tone * envelope(t, 0.50, 0.012, 5.5)


def bass(t):
    phase = math.tau * C3 * t
    tone = math.sin(phase) + 0.24 * math.sin(2 * phase) + 0.07 * math.sin(3 * phase)
    return tone * envelope(t, 0.32, 0.007, 3.0)


def kick(t):
    # Integrated exponential pitch fall: 116 Hz down towards a rounded 48 Hz.
    phase = math.tau * (48 * t + 68 * 0.025 * (1 - math.exp(-t / 0.025)))
    return math.sin(phase) * envelope(t, 0.16, 0.003, 19)


def snare_frames(count):
    rng = random.Random(0xA57A)
    low = 0.0
    frames = []
    for index in range(count):
        t = index / RATE
        low += 0.24 * (rng.uniform(-1, 1) - low)
        body = 0.23 * math.sin(math.tau * 178 * t) * math.exp(-28 * t)
        frames.append((low + body) * envelope(t, 0.22, 0.002, 14))
    return frames


def encode_pcm(frames):
    peak = max(abs(value) for value in frames)
    gain = 0.82 * 32767 / peak
    return b"".join(struct.pack("<h", round(value * gain)) for value in frames)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bank = (("dusk-pad", 0.52, pad), ("beacon", 0.50, lead),
            ("rounded-bass", 0.32, bass), ("soft-kick", 0.16, kick),
            ("hushed-snare", 0.22, None))
    total = 0
    for name, duration, synth in bank:
        count = round(RATE * duration)
        frames = ([synth(i / RATE) for i in range(count)] if synth
                  else snare_frames(count))
        pcm = encode_pcm(frames)
        path = OUTPUT / f"{name}.wav"
        with wave.open(str(path), "wb") as output:
            output.setparams((1, 2, RATE, count, "NONE", "not compressed"))
            output.writeframes(pcm)
        total += len(pcm)
        print(f"{path.name}: {count} frames, {len(pcm)} source PCM bytes")
    print(f"Total: {total} source PCM bytes (16-bit mono, {RATE} Hz)")
    print("Run bash tools/agk sound for the authoritative 8-bit chip-RAM total.")


if __name__ == "__main__":
    main()
