"""Release boundary tests require no Amiga tools, ROMs or artwork placeholders."""
import argparse
import importlib.util
import json
import os
import stat
import struct
import subprocess
import shutil
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from release_archives import ReleaseError, safe_name, require_tool, verify_zip, read_zip, verify_members
from release_build import FLAGS, check_cache, check_hunk, verify_build, build, file_sha, sha
from release_content import icons
from release_sdk import crc16, prepare_sdk


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


package = load("package_release", "package-release.py")
identity = load("release_identity", "release-identity.py").identity
verifier = load("verify_release", "verify-release.py")


class ReleaseBoundaries(unittest.TestCase):
    def test_versions(self):
        self.assertEqual(package.version("1.2.3"), "1.2.3")
        for value in ("v1.2.3", "1.2", "01.2.3", "1.2.3\n", "../1.2.3", "1.2.3;id", "9" * 20 + ".1.1"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                package.version(value)

    def test_archive_paths(self):
        self.assertEqual(str(safe_name("Astra/data/Astra")), "Astra/data/Astra")
        for name in ("/etc/passwd", "../Astra", "Astra/../x", "Astra//x", "Astra/./x", "C:x", "a\\b", "a\nx"):
            with self.subTest(name=name), self.assertRaises(ReleaseError):
                safe_name(name)

    def test_missing_tool(self):
        with patch("shutil.which", return_value=None), self.assertRaisesRegex(ReleaseError, "Missing required tool"):
            require_tool("lha")

    def test_missing_final_icons(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(ReleaseError, "Missing final"):
            icons(Path(temp))

    def test_reject_debug_and_missing_cache_flags(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "CMakeCache.txt"
            flags = (*FLAGS, "ACE_DEBUG", "ACE_USE_AGA_FEATURES", "ACE_USE_ECS_FEATURES")
            normal = "CMAKE_BUILD_TYPE:STRING=Release\n" + "".join(f"{key}:BOOL=OFF\n" for key in flags)
            cache.write_text(normal)
            self.assertEqual(check_cache(cache), dict.fromkeys(FLAGS, "OFF"))
            for value in (normal.replace(FLAGS[0] + ":BOOL=OFF", FLAGS[0] + ":BOOL=ON"), ""):
                cache.write_text(value)
                with self.assertRaises(ReleaseError):
                    check_cache(cache)

    def test_reject_unreceipted_stale_binary(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(ReleaseError, "Missing release build receipt"):
            verify_build(Path(temp))

    def test_reject_changed_binary_even_with_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / ".tmp/release-build-fixture/verified"
            folder.mkdir(parents=True)
            (root / ".tmp/release-build-latest.json").write_text(json.dumps({
                "schema": 2, "isolation": "fresh-source-snapshot",
                "build_dir": folder.relative_to(root).as_posix(), "binary_sha256": "0" * 64}))
            (folder / "astra").write_bytes(bytes.fromhex("000003f3") + bytes(32))
            with patch("release_build.check_cache"), self.assertRaisesRegex(ReleaseError, "Stale or replaced"):
                verify_build(root)

    def test_legacy_incremental_receipt_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".tmp").mkdir()
            (root / ".tmp/release-build-latest.json").write_text('{"schema": 1}')
            with self.assertRaisesRegex(ReleaseError, "Legacy/non-isolated"):
                verify_build(root)

    def test_source_with_older_mtime_compiles_in_new_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            source = root / "game/src/main.c"
            source.parent.mkdir(parents=True)
            source.write_text("int main(void) { return 1; }\n")
            old_object = root / "game/build/old.obj"
            old_object.parent.mkdir()
            old_object.write_bytes(b"user's existing evidence")
            kit = root / "installed-kit"
            kit.mkdir()

            def inputs(*args):
                return {"project": {"game/src/main.c": file_sha(source)}, "kit": {}, "toolchain": "fixture"}

            def compile_host(project, snapshot_kit):
                # Real compiler execution into a new empty directory; a test-only
                # Hunk wrapper lets this focused test exercise the receipt boundary.
                output = project / "game/build"
                self.assertFalse(output.exists())
                output.mkdir()
                subprocess.run(["cc", "-c", str(project / "game/src/main.c"),
                                "-o", str(output / "fresh.o")], check=True)
                (output / "astra").write_bytes(bytes.fromhex("000003f3") + (output / "fresh.o").read_bytes())
                (output / "astra.adf").write_bytes(b"test-only disk")
                flags = (*FLAGS, "ACE_DEBUG", "ACE_USE_AGA_FEATURES", "ACE_USE_ECS_FEATURES")
                (output / "CMakeCache.txt").write_text("CMAKE_BUILD_TYPE:STRING=Release\n" +
                    "".join(f"{flag}:BOOL=OFF\n" for flag in flags))

            with patch("release_build.kit_path", return_value=kit), \
                    patch("release_build.build_inputs", side_effect=inputs), \
                    patch("release_build.git", return_value="a" * 40), \
                    patch("release_build.compile_snapshot", side_effect=compile_host):
                first = build(root)
                source.write_text("int main(void) { return 2; }\n")
                os.utime(source, (1, 1))
                with self.assertRaisesRegex(ReleaseError, "Stale build"):
                    verify_build(root)
                second = build(root)
                self.assertNotEqual(first["build_dir"], second["build_dir"])
                self.assertNotEqual(first["binary_sha256"], second["binary_sha256"])
                self.assertEqual(verify_build(root), second)
                self.assertEqual(old_object.read_bytes(), b"user's existing evidence")
                self.assertTrue((root / first["build_dir"] / "astra").is_file())

    def test_missing_or_fake_slave(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Astra.slave"
            with self.assertRaises(FileNotFoundError):
                check_hunk(path)
            path.write_bytes(b"PK" + bytes(64))
            with self.assertRaisesRegex(ReleaseError, "Amiga Hunk"):
                check_hunk(path)

    def test_zip_checks_inventory_bytes_and_traversal(self):
        expected = {"Astra/Astra": b"actual bytes", "Astra.info": b"icon bytes"}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "release.zip"
            for content in (expected, expected | {"Astra": b"root executable"},
                            expected | {"Astra/Astra": b"corrupt"}, expected | {"../x": b"bad"}):
                with zipfile.ZipFile(path, "w") as archive:
                    for name, data in content.items():
                        archive.writestr(name, data)
                if content == expected:
                    verify_zip(path, expected)
                else:
                    with self.assertRaises(ReleaseError):
                        verify_zip(path, expected)

    def test_whd_ansi_crc_known_vector(self):
        self.assertEqual(crc16(b"123456789"), 0xBB3D)

    def test_zip_types_and_executable_permissions(self):
        expected = {"Astra/Astra": b"game"}
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "test.zip"
            for mode in (stat.S_IFLNK | 0o777, stat.S_IFIFO | 0o644,
                         stat.S_IFCHR | 0o644, stat.S_IFSOCK | 0o644,
                         stat.S_IFREG | 0o4755, stat.S_IFREG | 0o644, stat.S_IFREG | 0o755):
                with zipfile.ZipFile(archive, "w") as out:
                    entry = zipfile.ZipInfo("Astra/Astra")
                    entry.create_system = 3
                    entry.external_attr = mode << 16
                    out.writestr(entry, b"game")
                if mode == stat.S_IFREG | 0o755:
                    verify_zip(archive, expected, ("Astra/Astra",))
                else:
                    with self.subTest(mode=oct(mode)), self.assertRaises(ReleaseError):
                        verify_zip(archive, expected, ("Astra/Astra",))

    def test_duplicate_case_and_extra_directory_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "test.zip"
            with zipfile.ZipFile(archive, "w") as out:
                out.writestr("Astra/Astra", b"game")
                out.writestr("Astra/astra", b"game")
            with self.assertRaisesRegex(ReleaseError, "case-colliding"):
                read_zip(archive)
            with self.assertRaisesRegex(ReleaseError, "inventory"):
                verify_members({"extra": {"kind": "dir", "mode": 0o755}}, {})

    def test_corrupt_rich_icon_is_not_accepted_by_magic(self):
        from release_icons import validate_icon
        data = (ROOT / "assets/workbench/Astra-whdload.info").read_bytes()
        validate_icon(data, "whdload")
        with self.assertRaises(ReleaseError):
            validate_icon(data[:-1], "whdload")

    def test_rehashed_archive_game_mutation_fails_cross_format_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "HD.zip"
            original = {"Astra/Astra": b"original game", "Astra/Astra.info": b"tool", "Astra.info": b"drawer"}
            for kind in ("HD.zip", "HD.lha", "WHD.lha"):
                data = original | {"Astra/Astra": b"replaced game"}
                with zipfile.ZipFile(path, "w") as out:
                    for name, value in data.items():
                        entry = zipfile.ZipInfo(name)
                        entry.external_attr = (stat.S_IFREG | 0o755) << 16
                        out.writestr(entry, value)
                # An attacker can rewrite this hash; content must still fail.
                (Path(temp) / "SHA256SUMS").write_text(file_sha(path) + "  HD.zip\n")
                normal = {n: {"kind": "file", "mode": 0o755, "data": d} for n, d in original.items()}
                members = {"HD.zip": normal, "HD.lha": normal}
                if kind == "WHD.lha":
                    members[kind] = {"AstraWHD/data/Astra": {"kind": "file", "mode": 0o755, "data": b"replaced game"},
                                     "AstraWHD/Astra.info": {"kind": "file", "mode": 0o644, "data": b"whd"},
                                     "AstraWHD.info": {"kind": "file", "mode": 0o644, "data": b"drawer"},
                                     "AstraWHD/Astra.slave": {"kind": "file", "mode": 0o644, "data": b"slave"}}
                else:
                    members[kind] = read_zip(path)
                with self.subTest(kind=kind), self.assertRaisesRegex(ReleaseError, "content mismatch"):
                    verifier.verify_contract(b"original game", {}, members, {},
                                             {"drawer": b"drawer", "tool": b"tool", "whdload": b"whd"}, {}, b"slave")

    def test_slave_crc_is_bound_to_actual_payload(self):
        game = bytes.fromhex("000003f3") + bytes(28) + bytes.fromhex(
            "2f0a2f02247900000000102a0c004600122a0e000001004015410e00")
        # Explicit parser fixture, not a compiled/distributable slave.
        data = bytearray(160)
        data[:4] = bytes.fromhex("000003f3")
        base = 32
        data[base:base + 12] = bytes.fromhex("70ff4e75") + b"WHDLOADS"
        for offset, value in ((12, 19), (14, 0x2402), (24, 52), (26, 56), (48, 0xF9E3)):
            struct.pack_into(">H", data, base + offset, value)
        for offset, value in ((16, 0x80000), (32, 0x240000), (44, 0x40000)):
            struct.pack_into(">I", data, base + offset, value)
        data[base + 31] = 0x59
        data[base + 52:base + 54] = bytes.fromhex("43fa")
        data[base + 56:base + 61] = b"data\0"
        data.extend((bytes.fromhex("b0bc") + struct.pack(">I", len(game))) * 2)
        data.extend(bytes.fromhex("b87c") + struct.pack(">H", crc16(game)))
        verifier.slave_header(bytes(data), game)
        changed = bytearray(game)
        changed[8] = 1
        with self.assertRaisesRegex(ReleaseError, "CRC16"):
            verifier.slave_header(bytes(data), bytes(changed))

    def test_sdk_legacy_history_preserves_version_and_hash_checks(self):
        from release_build import sha
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            deps = root / ".tmp/release-deps"
            deps.mkdir(parents=True)
            archive = deps / "WHDLoad_dev.lha"
            archive.write_bytes(b"verified fixture archive")
            history = b"*** 20.0 (27.03.2026)\nLegacy author: G\xe1bor\n"

            def extract_fixture(source, destination):
                docs = destination / "WHDLoad/Docs"
                docs.mkdir(parents=True)
                (docs / "History.txt").write_bytes(history)

            with patch.dict("release_sdk.LOCK", {"sdk_sha256": sha(archive.read_bytes())}), \
                    patch("release_sdk.extract_lha", side_effect=extract_fixture) as extract:
                sdk = prepare_sdk(root)
                self.assertEqual((sdk / "Docs/History.txt").read_bytes(), history)
                history = b"*** 20.1 beta\nLegacy author: G\xe1bor\n"
                with self.assertRaisesRegex(ReleaseError, "version metadata"):
                    prepare_sdk(root)
                archive.write_bytes(b"tampered fixture")
                with self.assertRaisesRegex(ReleaseError, "checksum"):
                    prepare_sdk(root)
                self.assertEqual(extract.call_count, 2)

    def test_release_uses_tag_commit_not_target_branch(self):
        event = {"release": {"tag_name": "v1.2.3", "target_commitish": "main"}}
        self.assertEqual(identity(event, "a" * 40, lambda ref: "a" * 40)["commit"], "a" * 40)
        with self.assertRaisesRegex(ValueError, "does not resolve"):
            identity(event, "a" * 40, lambda ref: "b" * 40)

    def test_manual_defaults_to_build_only(self):
        event = {"inputs": {"version": "1.2.3", "ref": "main"}}
        self.assertEqual(identity(event, "a" * 40, lambda ref: self.fail("must not resolve tag"))["attach"], "false")


def release_mutations(release):
    """Opt-in real-artifact attacks; preserve all mutant directories as evidence."""
    from release_archives import extract_lha
    from release_build import docker
    release = release.resolve()
    metadata = json.loads((release / "release.json").read_text())
    prefix = "Astra-" + metadata["version"]
    original = (release / prefix).read_bytes()
    changed = original[:64] + bytes((original[64] ^ 1,)) + original[65:]
    work = Path(tempfile.mkdtemp(prefix="release-mutation-", dir=ROOT / ".tmp"))
    guest = lambda p: "/work/" + p.relative_to(ROOT).as_posix()
    payload = work / "changed-game"
    payload.write_bytes(changed)
    payload.chmod(0o755)
    results = []
    for kind in ("raw", "adf", "HD.zip", "HD.lha", "WHD.lha"):
        target = work / kind.replace(".", "-")
        shutil.copytree(release, target)
        expected = "Archive content mismatch: "
        if kind == "raw":
            (target / prefix).write_bytes(changed)
            claim = metadata | {"binary_sha256": sha(changed)}
            (target / "release.json").write_text(json.dumps(claim))
            expected = "Raw executable differs from trusted isolated build"
        elif kind == "adf":
            disk = target / (prefix + ".adf")
            subprocess.run(docker(ROOT, "xdftool", guest(disk), "delete", "Astra", "+",
                                  "write", guest(payload), "Astra"), check=True)
            expected += "Astra"
        elif kind == "HD.zip":
            path = target / (prefix + "-HD.zip")
            new = work / "changed.zip"
            with zipfile.ZipFile(path) as source, zipfile.ZipFile(new, "w") as out:
                for entry in source.infolist():
                    out.writestr(entry, changed if entry.filename == "Astra/Astra" else source.read(entry))
            new.replace(path)
            expected += "Astra/Astra"
        else:
            path = target / (prefix + "-" + kind)
            stage = work / (kind + "-stage")
            extract_lha(path, stage)
            drawer = "Astra" if kind == "HD.lha" else "AstraWHD"
            member = drawer + ("/Astra" if kind == "HD.lha" else "/data/Astra")
            (stage / member).write_bytes(changed)
            new = work / (kind + "-changed.lha")
            subprocess.run(docker(ROOT, "sh", "-ec", 'cd "$1"; lha ao5q "$2" "$3" "$3.info"',
                                  "mutate", guest(stage), guest(new), drawer), check=True)
            new.replace(path)
            expected += member
        # Rewrite the self-supplied manifest, including modified metadata for raw.
        manifest = target / (prefix + "-SHA256SUMS")
        manifest.write_text("".join(f"{file_sha(p)}  {p.name}\n" for p in sorted(target.iterdir()) if p != manifest))
        verifier.verify_manifest(target, prefix)  # attacker-controlled hashes all agree
        try:
            verifier.verify_release(target)
        except ReleaseError as error:
            if str(error) != expected:
                raise AssertionError(f"Unexpected rejection for {kind}: {error}") from error
            results.append({"format": kind, "self_manifest": "PASS", "independent_verifier": "REJECTED", "reason": str(error)})
        else:
            raise AssertionError(f"Rehashed {kind} executable replacement was accepted")
    (work / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"evidence": str(work), "mutations": results}, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--release-mutations":
        release_mutations(Path(sys.argv[2]))
    else:
        unittest.main()
