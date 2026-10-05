#!/usr/bin/env python3
"""Check that compiled ACE audio is the original WAV converted to Paula PCM."""
import hashlib
import pathlib
import re
import wave

root = pathlib.Path(__file__).resolve().parents[1]
folder = root / "game/art/intro"
with wave.open(str(folder / "ace.wav"), "rb") as wav:
    assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 1, 6000)
    pcm = bytes(value ^ 128 for value in wav.readframes(wav.getnframes()))
if len(pcm) % 2:
    pcm += b"\0"
header = (folder / "ace-sound.h").read_text()
array = re.search(r"aceSample\[\]\s*=\s*\{(.*?)\};", header, re.S)
assert array, "Missing compiled ACE audio"
compiled = bytes(int(value, 0) for value in re.findall(r"0x[0-9a-fA-F]+|\b\d+\b", array.group(1)))
assert compiled == pcm, "ACE audio has been altered or resampled"
assert len(compiled) == 13152
original = root / ".tmp/SuperRugbyV/assets/ace-splash/ace.wav"
if original.exists():
    assert original.read_bytes() == (folder / "ace.wav").read_bytes(), "Original WAV differs"
print(f"PASS original ACE audio: {len(compiled)} bytes, 6000 Hz, SHA256 {hashlib.sha256(pcm).hexdigest()}")
