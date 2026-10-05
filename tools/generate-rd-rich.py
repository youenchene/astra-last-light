#!/usr/bin/env python3.12
"""Generate original rich-sprite/decor masters through AGK's Retro Diffusion API.

Existing masters are never regenerated (or charged again). Use --dry-run for
the API's free price check. Credentials stay inside the installed AGK client.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
KIT = Path(os.environ.get("AGK_KIT", str(Path.home() / "Code/amiga/amiga-game-kit")))
sys.path.insert(0, str(KIT / "harness"))
from agk import rd
from agk.art import parse_palette

SPRITE = ", a single isolated horizontal space shooter sprite, strict SIDE VIEW facing LEFT, bold chunky clean pixel clusters and large readable silhouette, 1990s Amiga pixel art, not isometric, not rotated, no text or shadow"
DECOR = ", horizontal scrolling Amiga game corridor, seamless tiling left to right, detailed border structure along TOP and BOTTOM edges only, middle half completely empty dark space, mechanical pixel-art texture with large readable clusters, no stars, planets, spaceships, text or border frame"
JOBS = {
    "rd_hero16": (32, 32, 6701, "A single heroic space interceptor in strict side view facing RIGHT, long white silver metallic fuselage with pointed nose at right, luminous cyan cockpit, broad swept wings, short vivid orange exhaust flame only at left. Bold chunky clean pixel clusters, large readable silhouette filling most of canvas, 1990s Amiga horizontal shmup player sprite, not top down, not rotated, not isometric, no text or shadow"),
    "rd_scout16": (32, 32, 6702, "A fast orange and silver enemy scout spacecraft with a pointed nose on the left, swept wings, blue cockpit and short cyan engine at the right" + SPRITE),
    "rd_weaver16": (32, 32, 6703, "A hostile violet and pink manta-shaped alien spaceship, curved crescent wings surrounding a bright cyan white core, elegant curved silhouette" + SPRITE),
    "rd_gunner16": (32, 32, 6704, "A bulky hostile copper orange armored gunship, large round gun muzzle on left, layered metallic gray armor, glowing amber power cell" + SPRITE),
    "rd_dart16": (32, 32, 6705, "A long narrow blue silver alien dart fighter, very sharp needle nose on the left, forked rear wings and glowing pink engine on right" + SPRITE),
    "rd_boss16": (32, 32, 6706, "An armored imperial dreadnought reactor cannon module, chunky rectangular dark steel body with layered silver plating, luminous orange cannon aperture on left, glowing cyan reactor core" + SPRITE),
    "rd_asteroid16": (32, 32, 6707, "A single round irregular asteroid with deep craters, warm bronze illuminated upper left rim and dark blue gray shadows below, distinct angular rock facets, large bold clusters, readable Amiga pixel art space shooter obstacle, no stars, no text or shadow"),
    "rd_decor0": (64, 64, 6710, "Abandoned orbital ship hull architecture: navy steel panels, pale cyan pipes and small orange running lights, irregular broken metal silhouette" + DECOR),
    "rd_decor1": (64, 64, 6711, "Alien ion cave architecture: violet and magenta crystalline rocks, silver highlights and glowing cyan crystal tips pointing inward" + DECOR),
    "rd_decor2": (64, 64, 6712, "Imperial industrial furnace architecture: dark gunmetal girders, copper pipes, amber illuminated vents, strong layered mechanical plating" + DECOR),
    "rd_decor3": (64, 64, 6713, "Stellar citadel architecture: elegant silver armored ribs, luminous ice blue crystal reactors, gold trim and dark navy structural shadows" + DECOR),
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", choices=JOBS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-tasks", action="store_true", help="Read recent API task IDs for recovery")
    parser.add_argument("--inspect-task", help="Read public generation parameters for one task")
    parser.add_argument("--resume-task", nargs=2, metavar=("NAME", "TASK_ID"))
    args = parser.parse_args()
    if args.inspect_task:
        task = rd._request("GET", "/inferences/tasks/" + args.inspect_task)
        print("Task keys:", list(task))
        def show_parameters(value):
            if not isinstance(value, dict):
                return
            for key, item in value.items():
                if key in ("prompt", "width", "height", "seed", "status", "task_id"):
                    print(f"{key}: {item}")
                elif isinstance(item, dict):
                    show_parameters(item)
        show_parameters(task)
        return
    if args.list_tasks:
        result = rd._request("GET", "/inferences/tasks")
        if isinstance(result, dict):
            print("Response keys:", list(result))
            result = result.get("tasks", result.get("data", []))
        for task in result[:12]:
            print({key: task.get(key) for key in ("task_id", "id", "status", "created_at")})
        return
    art = ROOT / "game/art"
    colors = list(parse_palette(str(art / "palette.txt")).values())
    manifest_path = art / "rd-rich-manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    if args.resume_task:
        name, task_id = args.resume_task
        if name not in JOBS or (art / (name + ".png")).exists():
            raise SystemExit("Recovery name must be a missing configured image")
        manifest[name] = {"task_id": task_id, "status": "pending"}
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        args.only = [name]
    for name in args.only or JOBS:
        destination = art / (name + ".png")
        if destination.exists():
            if name not in manifest and not args.dry_run:
                width, height, seed, prompt = JOBS[name]
                manifest[name] = {"provider": "Retro Diffusion", "style": "rd_pro__default",
                    "prompt": prompt, "width": width, "height": height, "seed": seed,
                    "cost_usd": 0.18, "status": "complete", "registered_existing_master": True,
                    "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            print(f"Keep existing {destination.name}; no API request", flush=True)
            continue
        width, height, seed, prompt = JOBS[name]
        decor = name.startswith("rd_decor")
        if args.dry_run:
            _, cost, _ = rd.generate(prompt, width, height, colors,
                style="rd_pro__default", seed=seed, dry_run=True,
                tile_x=decor, remove_bg=not decor)
            print(f"{name}: would cost ${cost}", flush=True)
            continue
        entry = manifest.get(name, {})
        if name == "rd_weaver16" and not entry.get("task_id"):
            raise SystemExit("Original weaver request was interrupted without a task ID; do not resubmit it")
        if not entry.get("task_id"):
            body = {"prompt": prompt if decor else prompt + ", on a plain white background",
                "prompt_style": "rd_pro__default", "width": width, "height": height,
                "num_images": 1, "seed": seed, "remove_bg": not decor,
                "input_palette": rd.palette_png(colors)}
            if decor:
                body["tile_x"] = True
            request_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "astra-rich/" + name + prompt))
            accepted = rd._request("POST", "/inferences", body, {"Idempotency-Key": request_id})
            entry = {"task_id": accepted["task_id"], "status": "pending", "request_id": request_id}
            manifest[name] = entry
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            print(f"Saved {name} task {entry['task_id']}", flush=True)
        image, cost, _ = rd.wait_task(entry["task_id"])
        images = [image] if image else []
        if len(images) != 1:
            raise SystemExit(f"Unexpected result for {name}: no single image")
        destination.write_bytes(images[0])
        manifest[name] = {"provider": "Retro Diffusion", "style": "rd_pro__default",
            "prompt": prompt, "width": width, "height": height, "seed": seed,
            "tile_x": decor, "remove_bg": not decor, "cost_usd": cost,
            "sha256": hashlib.sha256(images[0]).hexdigest(), "task_id": entry["task_id"], "status": "complete"}
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"Generated {destination.name}: ${cost}", flush=True)

if __name__ == "__main__":
    main()
