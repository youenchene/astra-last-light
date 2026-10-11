#!/usr/bin/env python3
"""Extract original ACE logo bytes without hand-transcribing binary artwork."""
import pathlib
import re
import sys
import shutil

source = pathlib.Path(sys.argv[1]).read_text()
match = re.search(r"aceLogoPlanes\s*\[.*?\]\s*=\s*\{(.*?)\};", source, re.S)
if not match:
    raise SystemExit("ACE logo array missing")
values = re.findall(r"0x[0-9a-fA-F]+|\b\d+\b", match.group(1))
if len(values) != 2360:
    raise SystemExit(f"Expected 2360 planar bytes; got {len(values)}")
output = pathlib.Path(__file__).resolve().parents[1] / "game/art/intro/ace-logo.h"
output.write_text(
    "/* Original ACE logo, MPL-2.0. See README.md for source and attribution. */\n"
    "#ifndef ASTRA_ACE_LOGO_H\n#define ASTRA_ACE_LOGO_H\n"
    "static const unsigned char aceLogoPlanes[] = {\n"
    + "\n".join("  " + ",".join(values[i:i+20]) + "," for i in range(0, len(values), 20))
    + "\n};\n#endif\n"
)

# Preserve the original unsigned WAV as source and its exact upstream signed
# Paula sample as compiled data. Do not synthesize or resample this branding.
sample = re.search(r"aceSample\s*\[.*?\]\s*=\s*\{(.*?)\};", source, re.S)
if not sample:
    raise SystemExit("ACE sound array missing")
sample_values = re.findall(r"0x[0-9a-fA-F]+|\b\d+\b", sample.group(1))
if len(sample_values) < 1000 or len(sample_values) % 2:
    raise SystemExit("Expected a nonempty, even-length Paula sample")
output.with_name("ace-sound.h").write_text(
    "/* Original ACE splash audio, MPL-2.0. See README.md for attribution. */\n"
    "#ifndef ASTRA_ACE_SOUND_H\n#define ASTRA_ACE_SOUND_H\n"
    "static const unsigned char aceSample[] = {\n"
    + "\n".join("  " + ",".join(sample_values[i:i+20]) + "," for i in range(0, len(sample_values), 20))
    + "\n};\n#endif\n"
)
source_dir = pathlib.Path(sys.argv[1]).resolve().parent
shutil.copyfile(source_dir / "ace.wav", output.with_name("ace.wav"))
shutil.copyfile(source_dir / "MPL-2.0.txt", output.with_name("MPL-2.0.txt"))
print(f"Imported original ACE PCM: {len(sample_values)} bytes, {len(sample_values) / 6000:.3f} seconds at 6000 Hz")
