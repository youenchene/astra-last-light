#!/usr/bin/env python3
"""Independently verify published-file checksums and compiled Astra slave metadata."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import base64
import io
import re
import stat
import tempfile
import shutil

from release_archives import (ReleaseError, safe_name, read_zip, read_lha,
                              verify_members, check_member_names)
from release_build import ROOT, LOCK, FLAGS, docker, file_sha, sha, verify_build
from release_sdk import crc16, prepare_sdk, build_slave
from release_content import covered_sources, common_content, floppy_content, icons


def slave_header(data, game):
    if data[:4] != bytes.fromhex("000003f3") or data.count(b"WHDLOADS") != 1:
        raise ReleaseError("Expected a single real WHDLoad slave header in an Amiga Hunk")
    base = data.index(b"WHDLOADS") - 4
    word = lambda offset: struct.unpack_from(">H", data, base + offset)[0]
    long = lambda offset: struct.unpack_from(">I", data, base + offset)[0]
    if data[base:base + 4] != bytes.fromhex("70ff4e75"):
        raise ReleaseError("Slave security entry is not moveq #-1,d0 / rts")
    if word(12) != 19 or word(14) != 0x2402:
        raise ReleaseError("Unexpected slave version/flags; require NoError/EmulPriv/Examine only")
    if (long(16), long(20), data[base + 31], long(32), long(44), word(48)) != (
            0x80000, 0, 0x59, 0x240000, 0x40000, 0xF9E3):
        raise ReleaseError("Unexpected slave memory, F10 key or Kick13 identity")
    entry = base + word(24)
    if not base + 52 <= entry < len(data) - 4 or entry % 2 or data[entry:entry + 2] != b"\x43\xfa":
        raise ReleaseError("Slave loader entry does not target Kick13 boot code")
    directory = base + word(26)
    if data[directory:directory + 5] != b"data\0":
        raise ReleaseError("Slave current directory is not data")
    # vasm emits CMP with immediate EA for register destinations, not CMPI.
    if data.count(bytes.fromhex("b0bc") + struct.pack(">I", len(game))) != 2:
        raise ReleaseError("Slave lacks executable size guard")
    if data.count(bytes.fromhex("b87c") + struct.pack(">H", crc16(game))) != 1:
        raise ReleaseError("Slave lacks executable ANSI CRC16 guard")
    prefix = bytes.fromhex("2f0a2f022479")
    suffix = bytes.fromhex("102a0c004600122a0e000001004015410e00")
    matches = [i for i in range(0, len(game) - 27, 2)
               if game[i:i + 6] == prefix and game[i + 10:i + 28] == suffix]
    if len(matches) != 1:
        raise ReleaseError("Game must contain exactly one checked register-ABI handler")
    return {"bytes": len(data), "sha256": sha(data), "version": word(12),
            "flags": hex(word(14)), "entry_file_offset": entry,
            "keyexit": "F10", "keyboard_signature_count": len(matches),
            "game_crc16": f"{crc16(game):04x}", "runtime_boot_quit": "not validated"}


def regular_file(path):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ReleaseError(f"Release input is not a regular file: {path}")
    return path.read_bytes()


def verify_manifest(root, prefix):
    names = {prefix + suffix for suffix in ("", ".adf", "-HD.zip", "-HD.lha", "-WHD.lha")}
    names |= {"ReadMe.txt", "Sources.zip", "MPL-2.0.txt", "IntroCredits.txt", "release.json"}
    manifest = root / (prefix + "-SHA256SUMS")
    if {p.name for p in root.iterdir()} != names | {manifest.name}:
        raise ReleaseError("Release directory inventory differs from the five-format contract")
    files = {}
    for line in regular_file(manifest).decode("ascii").splitlines():
        digest, name = line.split("  ")
        if name not in names or name in files or sha(regular_file(root / name)) != digest:
            raise ReleaseError(f"Checksum or manifest path mismatch: {name}")
        files[name] = {"bytes": (root / name).stat().st_size, "sha256": digest}
    if set(files) != names:
        raise ReleaseError("Manifest does not cover exactly all release files")
    return files


def read_adf(path, work):
    data = regular_file(path)
    if len(data) != 901120 or data[:4] != b"DOS\0":
        raise ReleaseError("Expected an 880 KiB OFS ADF")
    copy = work / "input.adf"
    copy.write_bytes(data)
    rows = json.loads(subprocess.check_output(docker(
        ROOT, "python3", "/work/tools/release_adf.py", "/work/" + copy.relative_to(ROOT).as_posix())))
    names = check_member_names([row["name"] for row in rows])
    return {name: row | {"data": base64.b64decode(row["data"]) if row["data"] is not None else None}
            for name, row in zip(names, rows)}


def zip_source_contract(data, trusted):
    expected = {name: member["data"] for name, member in read_zip(io.BytesIO(trusted)).items()
                if member["kind"] == "file"}
    verify_members(read_zip(io.BytesIO(data)), expected)


def verify_contract(raw, metadata, members, common, artwork, source_files, trusted_slave):
    """Cross-format content checks, independent of hashes supplied by a release."""
    hd = {"Astra/" + name: data for name, data in common.items()}
    hd |= {"Astra/Astra": raw, "Astra/Astra.info": artwork["tool"], "Astra.info": artwork["drawer"]}
    for kind in ("HD.zip", "HD.lha"):
        verify_members(members[kind], hd, ("Astra/Astra",))
    whd = {"AstraWHD/" + name: data for name, data in common.items()}
    whd |= {"AstraWHD/data/Astra": raw, "AstraWHD/Astra.info": artwork["whdload"],
            "AstraWHD.info": artwork["drawer"], "AstraWHD/Astra.slave": trusted_slave}
    whd.update({"AstraWHD/source/" + name: data for name, data in source_files.items()})
    verify_members(members["WHD.lha"], whd, ("AstraWHD/data/Astra",))
    # Validate guards against the actual extracted WHD payload, not a raw-file claim.
    info = slave_header(members["WHD.lha"]["AstraWHD/Astra.slave"]["data"],
                        members["WHD.lha"]["AstraWHD/data/Astra"]["data"])
    if info["sha256"] != metadata["slave_sha256"]:
        raise ReleaseError("Slave does not match release.json")
    floppy = floppy_content(common)
    if "IntroSrc.zip" not in members["adf"]:
        raise ReleaseError("ADF lacks intro source bundle")
    actual_intro = members["adf"]["IntroSrc.zip"]["data"]
    zip_source_contract(actual_intro, floppy["IntroSrc.zip"])
    floppy["IntroSrc.zip"] = actual_intro  # ZIP timestamps are not content identity.
    floppy |= {"Astra": raw, "Astra.info": artwork["tool"], "s/startup-sequence": b"Astra\n"}
    verify_members(members["adf"], floppy, ("Astra",))
    return info


def verify_release(root, receipt=None):
    metadata_data = regular_file(root / "release.json")
    metadata = json.loads(metadata_data)
    version = metadata.get("version", "")
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version):
        raise ReleaseError("Invalid release version")
    prefix = "Astra-" + version
    if len(prefix + "-SHA256SUMS") > 30:
        raise ReleaseError("Version exceeds Amiga filename limit")
    files = verify_manifest(root, prefix)
    # A verified fresh build and the checked-out sources are the trust anchors.
    record = verify_build(receipt=receipt)
    trusted_game = ROOT / record["build_dir"] / "astra"
    raw = regular_file(root / prefix)
    if raw != regular_file(trusted_game):
        raise ReleaseError("Raw executable differs from trusted isolated build")
    if (metadata["binary_sha256"] != sha(raw) or metadata["source_commit"] != record["source_commit"]
            or metadata["build_inputs_sha256"] != sha(json.dumps(record["inputs"], sort_keys=True).encode())
            or metadata["flags"] != dict.fromkeys(FLAGS, "OFF") or metadata["dependencies"] != LOCK):
        raise ReleaseError("Release metadata differs from trusted build identity")
    artwork = icons(ROOT)  # independent DiskObject/classic/GlowIcon decoder + exact bytes
    if metadata["icons"] != {kind: sha(data) for kind, data in artwork.items()}:
        raise ReleaseError("Icon provenance does not match checked-out artwork")
    sources = regular_file(root / "Sources.zip")
    zip_source_contract(sources, covered_sources(ROOT))
    if metadata["sources_sha256"] != sha(sources):
        raise ReleaseError("Source metadata mismatch")
    common = common_content(ROOT, sources) | {"release.json": metadata_data}
    for name, data in common.items():
        if regular_file(root / name) != data:
            raise ReleaseError(f"Notice/source content differs from checked-out contract: {name}")
    work = Path(tempfile.mkdtemp(prefix="release-verify-", dir=ROOT / ".tmp"))
    sdk = prepare_sdk(ROOT)
    compiled = build_slave(ROOT, sdk, work, trusted_game)
    source_files = {name: (ROOT / "tools/whdload" / name).read_bytes()
                    for name in ("AstraKick13.asm", "README.md")}
    source_files["game-version.i"] = (work / "game-version.i").read_bytes()
    source_files.update({"whdload/" + name: (sdk / "Src/sources/whdload" / name).read_bytes()
                         for name in ("kick13.s", "kickfs.s", "kick.readme")})
    members = {"HD.zip": read_zip(root / (prefix + "-HD.zip")),
               "HD.lha": read_lha(root / (prefix + "-HD.lha")),
               "WHD.lha": read_lha(root / (prefix + "-WHD.lha")),
               "adf": read_adf(root / (prefix + ".adf"), work)}
    info = verify_contract(raw, metadata, members, common, artwork, source_files, compiled.read_bytes())
    verify_build(receipt=receipt)
    return {"release": str(root), "files": files, "slave": info,
            "five_format_content_contract": "PASS", "trust": "fresh isolated build and checked-out sources",
            "archive_types_modes_icons_sources": "PASS"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("--receipt", type=Path, help="Trusted schema-2 build receipt; default is local latest")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = verify_release(args.release.resolve(), args.receipt)
    text = json.dumps(report, indent=2) + "\n"
    if args.report:
        if args.report.exists():
            raise ReleaseError("Verification report already exists")
        args.report.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
