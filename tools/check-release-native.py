#!/usr/bin/env python3
"""Cold-boot packaged ADFs and an extracted HD drawer, without GUI or ROM copying."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

from release_archives import ReleaseError, safe_name
from release_build import ROOT, docker, file_sha, kit_path


def guest(path):
    return "/work/" + path.relative_to(ROOT).as_posix()


def make_hd(release, version, work):
    stage = work / "hd-tree"
    stage.mkdir()
    with zipfile.ZipFile(release / f"Astra-{version}-HD.zip") as archive:
        for name in archive.namelist():
            path = stage / safe_name(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(name))
    (stage / "s").mkdir()
    (stage / "s/startup-sequence").write_text("Astra/Astra\n")
    hdf = work / "Astra-HD.hdf"
    subprocess.run(docker(ROOT, "xdftool", guest(hdf), "create", "size=16Mi",
                          "+", "format", "AstraHD", "ofs", "+", "write", guest(stage / "Astra"),
                          "+", "write", guest(stage / "Astra.info"),
                          "+", "write", guest(stage / "s")), check=True)
    return hdf


def run_boot(image, profile_name, out, hd=False):
    from agk import profiles, runner, scenario
    from agk.image import Image
    profile, rom, ext = profiles.resolve(profile_name)
    out.mkdir()
    lines = runner._setup_lines(profile, rom, ext)
    if hd:
        # Extra memory for the filesystem/host: not baseline A500 RAM evidence.
        lines += ["mem set FAST_RAM 2048", f"hd0 attach {image}", "amiga power on"]
    else:
        lines += [f"regression run {image}"]
    text = """wait-serial "AGK language_ready" 900
press right 1
wait 24
press fire 1
wait-serial "AGK title_ready" 900
screenshot title
key 0x45
wait-serial "AGK escape_quit" 100
wait 100
screenshot returned_os
"""
    plan = scenario.parse(text, "release_boot")
    lines += [f"waitserial {scenario.serial_text('AGK ready')} 6000", "wait 1 frames"]
    lines += [line.replace("{out}", str(out)) for line in plan.lines]
    lines += [f"agk serial {out}/serial.txt"]
    code, output, seconds = runner._run_vamiga(lines, str(out), timeout=300)
    if code:
        raise ReleaseError(runner._emulator_error(output) + f"; evidence: {out}")
    serial = (out / "serial.txt").read_text(errors="replace")
    if re.search(r"ERR|STACK SMASHED|allocation failure", serial):
        raise ReleaseError(f"Native allocation/runtime error; evidence: {out}")
    for name in plan.screenshots:
        Image.from_raw_file(str(out / (name + ".raw"))).canonical12().screen().save_png(
            str(out / (name + ".screen.png")))
    return {"profile": profile_name, "medium": "HD" if hd else "ADF",
            "extra_fast_kib": 2048 if hd else (2048 if profile_name == "a500-aros" else 0),
            "image_sha256": file_sha(image), "seconds": round(seconds, 2),
            "boot_title_escape": "PASS", "evidence": str(out.relative_to(ROOT)),
            "workbench_double_click": "not tested; CLI startup only"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    args = parser.parse_args()
    release = args.release.resolve()
    metadata = json.loads((release / "release.json").read_text())
    sys.path.insert(0, str(kit_path() / "harness"))
    work = Path(tempfile.mkdtemp(prefix="release-native-", dir=ROOT / ".tmp"))
    results = []
    for profile in ("a500", "a500-aros"):
        results.append(run_boot(release / f"Astra-{metadata['version']}.adf", profile, work / profile))
        (work / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    hdf = make_hd(release, metadata["version"], work)
    results.append(run_boot(hdf, "a500", work / "hd-a500", hd=True))
    (work / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
