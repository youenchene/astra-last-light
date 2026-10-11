#!/usr/bin/env python3
"""Check publication/repair/music evidence and complete native transition captures.

Pass one or more clean_transitions output directories. No golden modification.
The timestamps prove controller invocation alignment, not Paula sample onset.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import sys


def require(ok, message):
    if not ok:
        raise ValueError(message)


def records(text, tag):
    return [(i, {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", line)})
            for i, line in enumerate(text.splitlines()) if line.startswith(f"AGK {tag}=")]


def validate(text):
    lines = text.splitlines()
    submitted, visible = records(text, "cut_submit"), records(text, "cut_visible")
    require(submitted and len(submitted) == len(visible), "missing publication acknowledgement")
    ready = records(text, "cut_target_ready")
    require(len(ready) == len(submitted) and all(r["cut_target_ready"] == 1 for _, r in ready),
            "partial target published")
    by_revision = {}
    for (si, s), (vi, v), (ri, _) in zip(submitted, visible, ready):
        fields = ("phase", "level", "bitmap", "copper", "both")
        require(ri < si < vi and s["cut_submit"] == v["cut_visible"] and
                all(s[k] == v[k] for k in fields), "publication identity changed before acknowledgement")
        require(v["vblank"] > s["vblank"], "acknowledged before vblank")
        by_revision.setdefault(s["cut_submit"], []).append(s)
    for revision, pair in by_revision.items():
        require(len(pair) == 2 and [s["both"] for s in pair] == [0, 1],
                f"revision {revision}: missing hidden-buffer repair")
        require(pair[0]["bitmap"] != pair[1]["bitmap"] and pair[0]["copper"] != pair[1]["copper"],
                f"revision {revision}: repair reused displayed identities")
    for hi, h in records(text, "cut_hold"):
        following = next((s for si, s in submitted if si > hi and s["cut_submit"] == h["cut_hold"]), None)
        require(following is not None and all(h[k] == following[k] for k in ("bitmap", "copper")),
                "hidden target swapped during hold")
    first_index, first = visible[0]
    require(first["phase"] == 0 and first["both"] == 0, "first publication is not a complete title")
    music = records(text, "music_visible")
    require(len(music) == 1, "missing first music handoff")
    mi, m = music[0]
    require(mi > first_index and m["music_visible"] == first["cut_visible"] and
            m["vblank"] == first["vblank"], "music controller not aligned with first visible title")
    themes = [i for i, line in enumerate(lines) if line == "AGK music theme"]
    require(themes and first_index < themes[0] < mi, "theme started before title visibility")
    require("AGK intro_released" in lines and lines.index("AGK intro_released") < first_index,
            "intro still owns display at title publication")
    for tag in ("title_ready", "combat_ready", "gameover_ready", "scene_ready"):
        for index, line in enumerate(lines):
            if line != f"AGK {tag}":
                continue
            prior = [v for vi, v in visible if vi < index]
            require(prior and prior[-1]["both"] == 1, f"{tag} before repair acknowledgement")
    require(not re.search(r"ERR|STACK SMASHED|allocation failure|bullet_hidden=[1-9]", text),
            "native error in evidence")
    return len(by_revision)


def check_images(folder):
    kit = Path(os.environ.get("AGK_KIT", str(Path.home() / "Code/amiga/amiga-game-kit")))
    sys.path.insert(0, str(kit / "harness"))
    from agk.image import Image
    spec = importlib.util.spec_from_file_location("campaign", Path(__file__).with_name("check-campaign-native.py"))
    campaign = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(campaign)

    def load(name):
        image = Image.load_png(str(folder / f"{name}.screen.png"))
        require((image.width, image.height) == (320, 256), f"{name}: dimensions")
        return image

    def same(a, b, exterior=False):
        left, right = load(a), load(b)
        bad = sum(left.pixel(x, y) != right.pixel(x, y)
                  for y in range(256) for x in range(320)
                  if not exterior or not (136 <= x < 312 and 56 <= y < 208))
        require(bad == 0, f"{a}/{b}: {bad} {'exterior' if exterior else 'full-frame'} pixels changed")

    for a, b in (("intro_hold", "intro_hold_later"), ("title_first", "title_repaired"),
                 ("title_repaired", "title_hold"), ("title_hold", "title_hold_later"),
                 ("title2", "scene_hold"), ("scene_hold", "scene_hold_later"),
                 ("scene_first", "scene_repair")):
        same(a, b)
    campaign.check_scene_pair(load("scene_ready"), load("scene_later"), 3)
    first, ready = load("scene_first"), load("scene_ready")
    hero = campaign.hero_pixels(ready)
    require(all(first.pixel(x, y) == ready.pixel(x, y)
                for y in range(256) for x in range(320) if (x, y) not in hero),
            "opening preparation changed exterior beyond the validated hero")
    # Closing repairs only the window; the hardware hero may blink when PLAY
    # resumes its retained invulnerability. All framebuffer exterior pixels stay.
    restored = load("restored_first")
    try:
        hero = campaign.hero_pixels(restored)
    except ValueError:
        hero = set()  # The blink-off frame must match the exact empty background.
    require(all(first.pixel(x, y) == restored.pixel(x, y)
                for y in range(256) for x in range(320)
                if not (136 <= x < 312 and 56 <= y < 208) and (x, y) not in hero),
            "opening close changed frozen exterior")
    for name in ("title_first", "title2"):
        image = load(name)
        space = image.pixel(0, 0)
        require(all(image.pixel(x, y) == space for y in (*range(26), *range(245, 256))
                    for x in range(320)), f"{name}: TITLE HUD remains")
    scene = load("scene_ready")
    require(any(scene.pixel(x, y) != scene.pixel(0, 0) for y in range(29, 53) for x in range(320)),
            "incoming sector scenery missing")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+", type=Path)
    args = parser.parse_args()
    for folder in args.directories:
        try:
            count = validate((folder / "serial.txt").read_text())
            check_images(folder)
            print(f"PASS {folder}: {count} cuts, repair identities, music invocation and full-frame holds/static windows")
        except (ValueError, OSError) as error:
            parser.exit(1, f"FAIL {folder}: {error}\n")
