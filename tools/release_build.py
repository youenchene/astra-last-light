"""Production builds and content-based freshness receipts (no timestamp trust)."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile

from release_archives import ReleaseError, require_tool

FLAGS = tuple("ASTRA_" + name for name in (
    "CAMPAIGN_PROBE", "COMBAT_STRESS", "COMBAT_TIMING", "PRESENTATION_TIMING",
    "FRAME_BREAKDOWN", "HUD_BOB_TIMING", "HUD_BOB_DETAIL"))
ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "tools/release-lock.json").read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def kit_path():
    return Path(os.environ.get("AGK_KIT", Path.home() / "Code/amiga/amiga-game-kit")).resolve()


def inventory(base, paths):
    result = {}
    for relative in paths:
        path = base / relative
        if not path.exists():
            raise ReleaseError(f"Missing source input: {path}")
        files = sorted(path.rglob("*")) if path.is_dir() else [path]
        for source in files:
            if any(p in (".git", "__pycache__", ".DS_Store") for p in source.parts):
                continue
            if source.is_symlink():
                raise ReleaseError(f"Source input is a symlink: {source}")
            if source.is_file():
                result[source.relative_to(base).as_posix()] = file_sha(source)
    return result


def build_inputs(root, kit):
    if git(kit, "rev-parse", "HEAD") != LOCK["agk_commit"]:
        raise ReleaseError("AGK revision differs from release lock")
    ace = root / "game/vendor/ACE"
    if git(ace, "rev-parse", "HEAD") != LOCK["ace_commit"]:
        raise ReleaseError("ACE revision differs from release lock")
    return {
        "project": inventory(root, ["game/src", "game/art", "game/sound", "game/tools",
                                    "game/CMakeLists.txt", "game/agk.toml", "game/vendor/ACE",
                                    "tools", "assets/workbench", "game/tests/unit/test_workbench_icons.py",
                                    "dependencies.lock"]),
        "kit": inventory(kit, ["runtime", "harness/agk", "tools", "patches/ace-agk.patch"]),
        "toolchain": LOCK["toolchain_image"],
    }


def check_cache(path):
    entries = {}
    for line in Path(path).read_text().splitlines():
        if ":" in line and "=" in line and not line.startswith(("#", "//")):
            key, value = line.split("=", 1)
            entries[key.split(":", 1)[0]] = value
    for flag in (*FLAGS, "ACE_DEBUG", "ACE_USE_AGA_FEATURES", "ACE_USE_ECS_FEATURES"):
        if entries.get(flag) != "OFF":
            raise ReleaseError(f"Non-production or missing cache flag: {flag}={entries.get(flag)}")
    if entries.get("CMAKE_BUILD_TYPE") != "Release":
        raise ReleaseError("CMAKE_BUILD_TYPE must be Release")
    return {flag: "OFF" for flag in FLAGS}


def docker(root, *args):
    return [require_tool("docker"), "run", "--rm", "--platform", LOCK["platform"],
            "-u", f"{os.getuid()}:{os.getgid()}", "-v", f"{root}:/work", "-w", "/work",
            LOCK["toolchain_image"], *map(str, args)]


def check_hunk(path):
    data = Path(path).read_bytes()
    if len(data) < 32 or data[:4] != bytes.fromhex("000003f3"):
        raise ReleaseError(f"Expected nonempty Amiga Hunk executable: {path}")
    return data


def copy_inputs(base, entries, destination):
    for name, digest in entries.items():
        source = base / name
        if file_sha(source) != digest:
            raise ReleaseError(f"Source changed while snapshotting: {name}")
        if source.suffix in (".o", ".obj") or "CMakeFiles" in source.parts:
            raise ReleaseError(f"Inherited build object in source inventory: {name}")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if file_sha(target) != digest:
            raise ReleaseError(f"Snapshot copy mismatch: {name}")


def compile_snapshot(project, kit):
    env = dict(os.environ, AGK_TOOLCHAIN_IMAGE=LOCK["toolchain_image"],
               DOCKER_DEFAULT_PLATFORM=LOCK["platform"], AGK_KIT=str(kit))
    subprocess.run(["bash", str(kit / "tools/agk"), "build", str(project / "game"), *[
        f"-D{flag}=OFF" for flag in (*FLAGS, "ACE_DEBUG", "ACE_USE_AGA_FEATURES",
                                     "ACE_USE_ECS_FEATURES")]], env=env, check=True)
    # AGK creates build/ only inside this new snapshot. No old CMake/object tree exists.


def build(root=ROOT):
    kit = kit_path()
    before = build_inputs(root, kit)
    (root / ".tmp").mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="release-build-", dir=root / ".tmp"))
    project, snapshot_kit = run / "project", run / "kit"
    copy_inputs(root, before["project"], project)
    copy_inputs(kit, before["kit"], snapshot_kit)
    # AGK's build script checks this path; CMake uses project-local pinned ACE.
    (snapshot_kit / "third_party/ACE").mkdir(parents=True)
    compile_snapshot(project, snapshot_kit)
    if build_inputs(root, kit) != before:
        raise ReleaseError("Source inputs changed during build; receipt not written")
    for base, entries in ((project, before["project"]), (snapshot_kit, before["kit"])):
        if any(file_sha(base / name) != digest for name, digest in entries.items()):
            raise ReleaseError("Snapshot source changed during build; receipt not written")
    built = project / "game/build"
    folder = run / "verified"
    folder.mkdir()
    for name in ("astra", "astra.adf", "CMakeCache.txt"):
        shutil.copy2(built / name, folder / name)
    check_cache(folder / "CMakeCache.txt")
    check_hunk(folder / "astra")
    record = {"schema": 2, "isolation": "fresh-source-snapshot",
              "build_dir": folder.relative_to(root).as_posix(),
              "source_commit": git(root, "rev-parse", "HEAD"),
              "inputs": before, "flags": {flag: "OFF" for flag in FLAGS},
              "binary_sha256": file_sha(folder / "astra"),
              "adf_sha256": file_sha(folder / "astra.adf"),
              "cache_sha256": file_sha(folder / "CMakeCache.txt")}
    (folder / "release-build.json").write_text(json.dumps(record, indent=2) + "\n")
    (root / ".tmp/release-build-latest.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def verify_build(root=ROOT, receipt=None):
    receipt = Path(receipt) if receipt else root / ".tmp/release-build-latest.json"
    if not receipt.is_file():
        raise ReleaseError("Missing release build receipt; run package without --no-build")
    record = json.loads(receipt.read_text())
    if record.get("schema") != 2 or record.get("isolation") != "fresh-source-snapshot":
        raise ReleaseError("Legacy/non-isolated build receipt refused; rebuild in a fresh snapshot")
    from release_archives import safe_name
    relative = safe_name(record["build_dir"])
    if not str(relative).startswith(".tmp/release-build-") or relative.name != "verified":
        raise ReleaseError("Receipt build directory is not an isolated release output")
    folder = root / relative
    if folder.resolve() != root.resolve() / relative:
        raise ReleaseError("Receipt build directory contains a symlink")
    check_cache(folder / "CMakeCache.txt")
    check_hunk(folder / "astra")
    for name, key in (("astra", "binary_sha256"), ("astra.adf", "adf_sha256"),
                      ("CMakeCache.txt", "cache_sha256")):
        if file_sha(folder / name) != record.get(key):
            raise ReleaseError(f"Stale or replaced build output: {name}")
    if record.get("source_commit") != git(root, "rev-parse", "HEAD"):
        raise ReleaseError("Build belongs to a different source commit")
    if record.get("inputs") != build_inputs(root, kit_path()):
        raise ReleaseError("Stale build: source/dependency contents changed")
    return record
