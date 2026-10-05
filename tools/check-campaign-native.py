#!/usr/bin/env python3
"""NON-SHIPPING native state fixture, NOT an ordinary campaign clear.

Run with python3 tools/check-campaign-native.py [--strict-performance].
Always rebuild production OFF in finally, even after build/run/check errors.
Evidence: game/build/campaign-native/{a500,a500-aros}/ plus report.json.
--check-only parses existing evidence without building or running anything.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
KIT = Path(os.environ.get("AGK_KIT", str(Path.home() / "Code/amiga/amiga-game-kit")))
sys.path.insert(0, str(KIT / "harness"))
from agk.image import Image

PROFILES = ("a500", "a500-aros")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def records(text, tag):
    return [dict((k, int(v)) for k, v in re.findall(r"(\w+)=(-?\d+)", line))
            for line in text.splitlines() if line.startswith(f"AGK {tag}")]


def performance(text):
    """Keep every 50-frame window, with latest state context (may straddle phases)."""
    windows, context = [], {}
    for line in text.splitlines():
        values = dict((k, int(v)) for k, v in re.findall(r"(\w+)=(-?\d+)", line))
        if line.startswith("AGK perf "):
            windows.append({**values, "last_state": context.copy()})
        elif "phase" in values:
            context = {k: values[k] for k in ("frame", "level", "phase", "stage", "sim") if k in values}
    require(windows, "missing performance windows")
    dropped = sum(w.get("dropped", 0) for w in windows)
    peak = max(w["maxload"] for w in windows)
    return {"pass": dropped == 0 and peak <= 90, "dropped": dropped,
            "maxload": peak, "windows": windows}


def check_lifecycle(text):
    scenes = records(text, "qa_scene=")
    require([r["qa_scene"] for r in scenes] == list(range(13)), "scene IDs/ack sequence")
    transitions = records(text, "qa_transition=")
    for scene in scenes[:12]:
        leaving = next(r for r in transitions if r["frame"] > scene["frame"]
                       and r["qa_transition"] == scene["phase"])
        require(leaving["frame"] - scene["frame"] + scene["pf"] == 150,
                f"scene {scene['qa_scene']}: dwell not 150 acknowledged ticks")
    starts, ends = records(text, "qa_pause_begin="), records(text, "qa_pause_end=")
    require(len(starts) == len(ends) == 12, "expected eight hero + four boss pauses")
    for start, end in zip(starts, ends):
        duration = 40 if start["phase"] == 9 else 75
        require(end["qa_pause_end"] == start["phase"] and end["frame"] - start["frame"] == duration,
                f"incorrect death pause: {start} -> {end}")
        require(all(start[k] == end[k] for k in ("sim", "stage", "tick", "lives")),
                "simulation advanced during death")
    require(records(text, "qa_complete=")[0]["qa_complete"] == 8191, "missing WIN completion")
    channels = records(text, "qa_channels=")
    require([(r["qa_channels"], r["mask"]) for r in channels] == [(i, 240) for i in range(1, 5)],
            "not all four channels used by each boss")
    require(not re.search(r"qa_fail=|bullet_hidden=[1-9]|ERR|STACK SMASHED|allocation failure", text),
            "native assertion/error in serial")


def artwork(name):
    colors, frames, rows = {}, [], None
    for line in (ROOT / "game/art" / f"{name}.txt").read_text().splitlines():
        line = line.strip()
        if line == "frame":
            rows = []; frames.append(rows)
        elif rows is not None and line and not line.startswith("#"):
            rows.append(line)
        elif len(line.split()) == 2 and line.split()[1].startswith("0x"):
            symbol, value = line.split()
            rgb = int(value, 16)
            colors[symbol] = tuple(((rgb >> shift) & 15) * 17 for shift in (8, 4, 0))
    colors["4"] = (187, 221, 255)  # live world star register
    return colors, frames


def verify_pixels(image, art, index, x, y, background=None):
    colors, frames = artwork(art)
    rows = frames[index]
    bad, count = [], 0
    for dy, row in enumerate(rows):
        for dx, symbol in enumerate(row):
            if symbol in (".", "0"):
                if background is not None and image.pixel(x + dx, y + dy) not in background:
                    bad.append((x + dx, y + dy))
                continue
            count += 1
            if image.pixel(x + dx, y + dy) != colors[symbol]:
                bad.append((x + dx, y + dy))
    require(count and not bad, f"{art} frame{index} at{x,y}: {len(bad)}/{count} opaque pixels differ; {bad[:8]}")
    return count


def check_images(directory, text):
    names = [f"scene{i:02}" for i in range(13)]
    names += [f"{kind}{i}" for kind in ("boss", "flash", "dead", "fx") for i in range(1, 5)]
    names += [f"hero{i}" for i in range(8)]
    names += ["F_badge", "F2", "F3"]
    images = {n: Image.load_png(str(directory / f"{n}.screen.png")) for n in names}
    require(all((im.width, im.height) == (320, 256) for im in images.values()), "capture dimensions")
    checked = {}
    background = {(0, 0, 17), (187, 221, 255)}
    checked["F_badge"] = verify_pixels(images["F_badge"], "bonuses", 4, 80, 126, background)
    for pattern, offsets in ((2, (-6, 6)), (3, (-8, 0, 8))):
        shots = [r for r in records(text, "qa_F_shot=") if r["qa_F_shot"] == pattern]
        require(len(shots) == pattern, f"F{pattern}: wrong volley size")
        require([r["y"] for r in shots] == [136 + dy for dy in offsets], "F volley offsets")
        require(all(r["kind"] == 0 and r["damage"] == 1 for r in shots), "F must not change power")
        for r in shots:
            checked[f"F{pattern}_shot{r['slot']}"] = verify_pixels(images[f"F{pattern}"], "pshot", 0, r["x"], r["y"], background)
    for tag, art in (("boss", "campaign_boss"), ("flash", "campaign_flash")):
        for r in records(text, f"qa_{tag}="):
            level = r[f"qa_{tag}"]
            checked[f"{tag}{level}"] = verify_pixels(images[f"{tag}{level}"], art, level - 1, r["x"], r["y"])
            require(r["maxhp"] == (108, 144, 192, 240)[level - 1], "fixture changed maxHp")
    for tag, art, width, height in (("dead", "campaign_fx64", 64, 48),
                                   ("hero", "campaign_fx32", 32, 32),
                                   ("fx_slot", "campaign_fx16", 16, 16)):
        for r in records(text, f"qa_{tag}="):
            name = f"fx{r['level']}" if tag == "fx_slot" else f"{tag}{r[f'qa_{tag}']}"
            index = min(7, r["age"] * 8 // r["life"])
            x = max(0, min(320 - width - 1, r["x"]))
            y = max(56, min(216 - height, r["y"]))
            checked[f"{name}_slot{r['slot']}"] = verify_pixels(images[name], art, index, x, y)
    return {"captures": len(images), "opaque_pixels_checked": checked}


def inspect(directory):
    text = (directory / "serial.txt").read_text()
    perf = performance(text)
    print(f"{directory.name}: budget {'PASS' if perf['pass'] else 'FAIL (expected known blocker)'}: "
          f"dropped={perf['dropped']} maxload={perf['maxload']}%", flush=True)
    result = {"performance": perf, "memory": records(text, "chip_free=")}
    try:
        require(result["memory"], "missing chip_free/ram_free memory evidence")
        check_lifecycle(text)
        result["images"] = check_images(directory, text)
        result["functional_pass"] = True
    except (ValueError, OSError, IndexError, KeyError, StopIteration) as error:
        result.update(functional_pass=False, error=str(error))
    print(f"{directory.name}: functional={result['functional_pass']} {result.get('error', '')}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict-performance", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--out", type=Path, default=ROOT / "game/build/campaign-native")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report = {"fixture": "NON-SHIPPING injected state; not ordinary campaign clear", "profiles": {}}
    def command(*parts):
        subprocess.run(["bash", "tools/agk", *parts], cwd=ROOT, check=True)
    try:
        if not args.check_only:
            command("build", "-D", "ASTRA_CAMPAIGN_PROBE=ON")
        for profile in PROFILES:
            directory = args.out / profile
            if not args.check_only:
                command("run", "--no-build", "--fresh", "-p", profile,
                        "-f", "game/tests/native/campaign.agk", "-o", str(directory))
            report["profiles"][profile] = inspect(directory)
            if not report["profiles"][profile]["functional_pass"]:
                break  # stop on unexpected failure, do not auto-correct
    except (subprocess.CalledProcessError, ValueError, OSError) as error:
        report["error"] = str(error)
        # Native runner assertions can fail after writing useful evidence.
        for profile in PROFILES:
            directory = args.out / profile
            if profile not in report["profiles"] and (directory / "serial.txt").exists():
                report["profiles"][profile] = inspect(directory)
    finally:
        if not args.check_only:
            try:
                command("build", "-D", "ASTRA_CAMPAIGN_PROBE=OFF")
                cache = (ROOT / "game/build/CMakeCache.txt").read_text()
                require("ASTRA_CAMPAIGN_PROBE:BOOL=OFF" in cache, "production cache not OFF")
                report["production_restored"] = True
            except (subprocess.CalledProcessError, OSError, ValueError) as error:
                report["production_restored"] = False
                report["restore_error"] = str(error)
        (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    ok = len(report["profiles"]) == 2 and all(r["functional_pass"] for r in report["profiles"].values())
    ok = ok and not report.get("error") and report.get("production_restored", True)
    if args.strict_performance:
        ok = ok and all(r["performance"]["pass"] for r in report["profiles"].values())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
