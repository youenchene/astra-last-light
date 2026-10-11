"""Allowlisted distribution content; never copy runtime ROMs, RTBs or keys."""
import io
from pathlib import Path
import struct
import zipfile

from release_archives import ReleaseError
from release_build import file_sha

NOTICE = """ASTRA: LAST LIGHT - development build

Native game: A500, 68000, OCS PAL, Kickstart 1.3, 512 KiB CHIP + 512 KiB slow.
Hard-disk Workbench launch may need extra RAM for the desktop and icon stack.
Escape returns to AmigaOS. Arrow keys/joystick move, Space/fire starts/charges;
release fires; M toggles music. Global locked-50fps acceptance remains BLOCKED.

WHDLoad edition: install WHDLoad yourself on AmigaOS/Kickstart 2.0+.
The slave reserves 512 KiB CHIP + 2 MiB expansion + 256 KiB Kick13 emulation.
Host OS, WHDLoad and PRELOAD need additional memory. Use at least 4 MiB fast
as a candidate test configuration, not an established minimum. F10 quits;
Escape follows the game's normal shutdown then returns to the WHDLoad host.
Supply your legal Devs:Kickstarts/kick34005.A500 and matching .RTB yourself.
No WHDLoad executable, ROM, ROM key or RTB is distributed here.
Native WHDLoad boot/quit validation status is recorded in release.json.

MIXED LICENSES - NOT A BLANKET MIT GAME LICENSE.
ACE code and ACE intro/logo/original PCM: Mozilla Public License 2.0.
Sources.zip includes covered sources and the full MPL-2.0 license.
IntroCredits.txt identifies upstream authors, revisions and modifications.
Micrix Production, Youen CHENE (1996-2022): CC BY-NC-SA 4.0.
Micrix adaptation retains NonCommercial and ShareAlike requirements.
https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode
No endorsement; licensed material is provided as-is without warranties.
Do not assume commercial distribution rights for the combined game.
Retain Sources.zip, notices and release.json when redistributing the raw
executable or floppy image. The complete source bundle is embedded in the HD
and WHD drawers and supplied alongside the raw executable and floppy. The
880 KiB floppy includes intro sources and Sources.txt naming the full bundle
and its checksum; the full ACE source bundle does not fit on that floppy.

Original Astra Workbench art generated with Retro Diffusion; offline conversion
and selected states authored for Astra. No Retromiga artwork is included.
"""


def icons(root):
    result = {}
    for kind, expected_type in (("drawer", 2), ("tool", 3), ("whdload", 4)):
        path = root / f"assets/workbench/Astra-{kind}.info"
        if not path.is_file():
            raise ReleaseError(f"Missing final Workbench icon: {path}")
        data = path.read_bytes()
        from release_icons import validate_icon
        validate_icon(data, kind)
        if len(data) < 78 or data[:4] != bytes.fromhex("e3100001") or data[48] != expected_type:
            raise ReleaseError(f"Invalid {kind} DiskObject icon")
        if not all(any(data[p:p + 4]) for p in (22, 26)):
            raise ReleaseError(f"{kind} icon lacks normal/selected fallback images")
        if kind == "tool" and struct.unpack_from(">I", data, 74)[0] < 4096:
            raise ReleaseError("Tool icon lacks a usable stack size")
        if kind == "whdload" and not all(s in data for s in (
                b"WHDLoad\0", b"SLAVE=Astra.slave\0", b"PRELOAD\0")):
            raise ReleaseError("WHDLoad launch metadata missing")
        result[kind] = data
    return result


def covered_sources(root):
    """Ship exact local covered source, including patched ACE, even for dirty builds."""
    paths = [root / "game/src/intro.c", root / "game/src/intro.h"]
    paths += [p for p in (root / "game/art/intro").rglob("*") if p.is_file()]
    ace = root / "game/vendor/ACE"
    for directory in ("src", "include", "cmake"):
        paths += [p for p in (ace / directory).rglob("*") if p.is_file()]
    paths += [ace / "CMakeLists.txt", root / "tools/patches/ace-allocation-safety.patch"]
    paths += [p for p in ace.iterdir() if p.is_file() and p.name.lower().startswith("license")]
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(set(paths)):
            if path.is_symlink():
                raise ReleaseError(f"Source symlink refused: {path}")
            archive.writestr(path.relative_to(root).as_posix(), path.read_bytes())
    return stream.getvalue()


def common_content(root, sources):
    return {"ReadMe.txt": NOTICE.encode(), "Sources.zip": sources,
            "MPL-2.0.txt": (root / "game/art/intro/MPL-2.0.txt").read_bytes(),
            "IntroCredits.txt": (root / "game/art/intro/README.md").read_bytes()}


def floppy_content(common):
    """Keep the 880 KiB disk bootable and give exact accompanying-source identity."""
    from release_build import sha
    sources = common["Sources.zip"]
    stream = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(sources)) as full:
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as intro:
            for name in full.namelist():
                if name.startswith("game/art/intro/") or name in ("game/src/intro.c", "game/src/intro.h"):
                    intro.writestr(name, full.read(name))
    return {name: data for name, data in common.items() if name != "Sources.zip"} | {
        "IntroSrc.zip": stream.getvalue(),
        "Sources.txt": ("Full covered source: accompanying Sources.zip (also inside HD/WHD archives).\n"
                        "SHA256 " + sha(sources) + "\nKeep this bundle with redistributions.\n").encode()}


def write_tree(folder, content):
    folder.mkdir(parents=True, exist_ok=False)
    for name, data in content.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def tree_content(folder):
    return {path.relative_to(folder).as_posix(): path.read_bytes()
            for path in sorted(folder.rglob("*")) if path.is_file()}
