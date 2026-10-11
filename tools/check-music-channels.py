#!/usr/bin/env python3
"""Check every registered score's Paula ownership and the sector PCM budget."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "game/build/sound"
SONGS = ("theme", "sector1", "sector2", "sector3", "sector4")


def check_module(name):
    data = (BUILD / f"{name}.mod").read_bytes()
    assert data[1080:1084] == b"M.K.", f"{name}: not a four-channel MOD"
    length = data[950]
    assert 1 <= length <= 128, f"{name}: invalid order length"
    patterns = max(data[952:952 + length]) + 1
    pcm = sum(int.from_bytes(data[42 + i*30:44 + i*30], "big") * 2
              for i in range(31))
    assert len(data) == 1084 + patterns * 1024 + pcm, f"{name}: invalid MOD size"
    for pattern in range(patterns):
        for row in range(64):
            offset = 1084 + pattern*1024 + row*16 + 12
            a, b, c, _ = data[offset:offset + 4]
            sample = (a & 0xf0) | (c >> 4)
            period = ((a & 0x0f) << 8) | b
            assert sample == 0 and period == 0, (
                f"{name}: music note/sample on D: pattern {pattern}, row {row}")
    print(f"PASS {name}: {length} positions, {pcm} PCM bytes, {len(data)} MOD bytes; "
          "no notes/samples on Paula D (global effects permitted)")
    return pcm


def main():
    header = (BUILD / "sound.h").read_text()
    source = (BUILD / "sound.c").read_text()
    assert re.search(r"#define\s+SOUND_MUSIC_COUNT\s+5\b", header), "expected five songs"
    for name in SONGS:
        assert f"SOUND_MUSIC_{name.upper()}" in header, f"missing ID for {name}"
    masks = re.findall(r"ptplayerSetMusicChannelMask\(\s*(0x[0-9a-fA-F]+)\s*\)", source)
    assert masks and all(int(mask, 16) == 0x7 for mask in masks), "music mask must be 0x7"
    sizes = {name: check_module(name) for name in SONGS}
    sector_pcm = sum(sizes[name] for name in SONGS[1:])
    assert sector_pcm <= 32768, f"sector PCM exceeds 32 KiB: {sector_pcm}"
    print(f"PASS sector PCM: {sector_pcm}/32768 bytes; all five songs use music mask 0x7")


if __name__ == "__main__":
    main()
