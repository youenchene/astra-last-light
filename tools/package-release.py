#!/usr/bin/env python3
"""Build and verify Astra's raw executable, bootable ADF, HD ZIP/LHA and WHD LHA."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

from release_archives import ReleaseError, read_lha, verify_members, require_tool, verify_zip
from release_build import ROOT, LOCK, build, docker, file_sha, git, sha, verify_build
from release_content import common_content, covered_sources, floppy_content, icons, tree_content, write_tree
from release_sdk import build_slave, prepare_sdk


def version(value):
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value):
        raise argparse.ArgumentTypeError("Use a numeric version, e.g. 1.2.3 (no v prefix)")
    if len(f"Astra-{value}-SHA256SUMS") > 30:
        raise argparse.ArgumentTypeError("Version exceeds Amiga's 30-character filename limit")
    return value


def container_path(path):
    return "/work/" + path.resolve().relative_to(ROOT).as_posix()


def archive_drawer(stage, drawer, out, suffix):
    expected = tree_content(stage / drawer)
    expected = {drawer + "/" + name: data for name, data in expected.items()}
    expected[drawer + ".info"] = (stage / (drawer + ".info")).read_bytes()
    if suffix == ".zip":
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in expected.items():
                entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                entry.external_attr = (0o100755 if name == drawer + "/Astra" else 0o100644) << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, data)
        verify_zip(out, expected, (drawer + "/Astra",))
    else:
        subprocess.run(docker(ROOT, "sh", "-ec", 'cd "$1"; lha ao5q "$2" "$3" "$3.info"',
                              "lha", container_path(stage), container_path(out), drawer), check=True)
        subprocess.run(docker(ROOT, "lha", "t", container_path(out)), check=True)
        game = drawer + ("/Astra" if drawer == "Astra" else "/data/Astra")
        verify_members(read_lha(out), expected, (game,))
    if {name.split("/")[0] for name in expected} != {drawer, drawer + ".info"}:
        raise ReleaseError("Archive must contain only an outer drawer and its icon")


def make_adf(work, binary, out, content):
    stage = work / "floppy"
    write_tree(stage, content | {"Astra": binary.read_bytes(), "s/startup-sequence": b"Astra\n"})
    (stage / "Astra").chmod(0o755)
    args = ["xdftool", container_path(out), "format", "Astra", "ofs", "+", "boot", "install"]
    for name in sorted(content):
        args += ["+", "write", container_path(stage / name), name]
    args += ["+", "write", container_path(stage / "Astra"), "Astra", "+", "makedir", "s",
             "+", "write", container_path(stage / "s/startup-sequence"), "s/startup-sequence"]
    subprocess.run(docker(ROOT, *args), check=True)
    if out.stat().st_size != 901120:
        raise ReleaseError("ADF is not an 880 KiB floppy")
    extracted = work / "adf-verify"
    extracted.mkdir()
    for name, expected in tree_content(stage).items():
        dest = extracted / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(docker(ROOT, "xdftool", container_path(out), "read", name,
                              container_path(dest)), check=True)
        if dest.read_bytes() != expected:
            raise ReleaseError(f"ADF extracted member differs: {name}")


def package(args):
    require_tool("docker")
    require_tool("bsdtar")
    if args.out.exists():
        raise ReleaseError(f"Output already exists; choose a new directory: {args.out}")
    artwork = icons(ROOT)
    record = verify_build() if args.no_build else build()
    binary = ROOT / record["build_dir"] / "astra"
    sdk = prepare_sdk(ROOT)
    work = Path(tempfile.mkdtemp(prefix="release-", dir=ROOT / ".tmp"))
    output = work / "output"
    output.mkdir()
    slave = build_slave(ROOT, sdk, work, binary)
    sources = covered_sources(ROOT)
    common = common_content(ROOT, sources)
    metadata = {
        "schema": 1, "version": args.version, "source_commit": record["source_commit"],
        "source_dirty": bool(git(ROOT, "status", "--porcelain", "--untracked-files=normal")),
        "build_inputs_sha256": sha(json.dumps(record["inputs"], sort_keys=True).encode()),
        "binary_sha256": file_sha(binary), "slave_sha256": file_sha(slave),
        "sources_sha256": sha(sources), "flags": record["flags"], "dependencies": LOCK,
        "validation": {"native_adf": "not validated for this package",
                       "native_hd": "not validated for this package",
                       "native_whd_boot_quit": "not validated for this package"},
        "performance": "Global 50fps acceptance BLOCKED",
        "licenses": "Mixed MPL-2.0 / Micrix CC BY-NC-SA 4.0; retain Sources.zip and notices",
        "icons": {name: sha(data) for name, data in artwork.items()},
    }
    common["release.json"] = (json.dumps(metadata, indent=2) + "\n").encode()
    stage = work / "drawers"
    stage.mkdir()
    hd = common | {"Astra": binary.read_bytes(), "Astra.info": artwork["tool"]}
    whd = common | {"data/Astra": binary.read_bytes(), "Astra.slave": slave.read_bytes(),
                    "Astra.info": artwork["whdload"]}
    for name in ("AstraKick13.asm", "README.md"):
        whd["source/" + name] = (ROOT / "tools/whdload" / name).read_bytes()
    whd["source/game-version.i"] = (work / "game-version.i").read_bytes()
    for name in ("kick13.s", "kickfs.s", "kick.readme"):
        whd["source/whdload/" + name] = (sdk / "Src/sources/whdload" / name).read_bytes()
    for drawer, content in (("Astra", hd), ("AstraWHD", whd)):
        write_tree(stage / drawer, content)
        (stage / (drawer + ".info")).write_bytes(artwork["drawer"])
    (stage / "Astra/Astra").chmod(0o755)
    (stage / "AstraWHD/data/Astra").chmod(0o755)
    prefix = "Astra-" + args.version
    (output / prefix).write_bytes(binary.read_bytes())
    (output / prefix).chmod(0o755)
    make_adf(work, binary, output / (prefix + ".adf"), floppy_content(common) | {"Astra.info": artwork["tool"]})
    for drawer, suffix in (("Astra", "-HD.zip"), ("Astra", "-HD.lha"), ("AstraWHD", "-WHD.lha")):
        archive_drawer(stage, drawer, output / (prefix + suffix), Path(suffix).suffix)
    for name, data in common.items():
        (output / name).write_bytes(data)
    files = sorted(output.iterdir())
    (output / (prefix + "-SHA256SUMS")).write_text(
        "".join(f"{file_sha(path)}  {path.name}\n" for path in files))
    # Recheck after packaging so concurrent source edits cannot silently ship.
    verify_build(receipt=ROOT / record["build_dir"] / "release-build.json")
    destination = args.out.resolve()
    if destination.exists():
        raise ReleaseError(f"Output already exists; choose a new directory: {destination}")
    shutil.copytree(output, destination)
    print(f"Verified five formats: {destination}\nNative validation still required; see release.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, type=version)
    parser.add_argument("--out", type=Path, help="New output directory (never overwrite)")
    parser.add_argument("--no-build", action="store_true",
                        help="Use only a source/hash/cache-verified release build receipt")
    args = parser.parse_args()
    args.out = args.out or ROOT / "game/build" / ("release-" + args.version)
    try:
        package(args)
    except (ReleaseError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Release stopped: {error}\n")


if __name__ == "__main__":
    main()
