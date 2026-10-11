"""Download a reviewed SDK, verify before extracting; use pinned Docker tools."""
from pathlib import Path
import subprocess
import urllib.request

from release_archives import ReleaseError, extract_lha
from release_build import LOCK, docker, file_sha


def prepare_sdk(root):
    deps = root / ".tmp/release-deps"
    deps.mkdir(parents=True, exist_ok=True)
    archive = deps / "WHDLoad_dev.lha"
    if not archive.exists():
        with urllib.request.urlopen(LOCK["sdk_url"], timeout=60) as response:
            data = response.read(8 * 1024 * 1024 + 1)
        from release_build import sha
        if sha(data) != LOCK["sdk_sha256"]:
            raise ReleaseError("Downloaded SDK checksum differs from reviewed 20.0 pin")
        archive.write_bytes(data)
    if file_sha(archive) != LOCK["sdk_sha256"]:
        raise ReleaseError("Cached SDK checksum differs from reviewed 20.0 pin")
    # A fresh extraction prevents modified cached SDK sources becoming build inputs.
    import tempfile
    fresh = Path(tempfile.mkdtemp(prefix="sdk-", dir=deps)) / "extracted"
    extract_lha(archive, fresh)
    sdk = fresh / "WHDLoad"
    if b"20.0 (27.03.2026)" not in (sdk / "Docs/History.txt").read_bytes():
        raise ReleaseError("SDK version metadata differs from release lock")
    return sdk


def crc16(data):
    """WHDLoad ANSI CRC16, reflected polynomial A001, initial value zero."""
    value = 0
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xA001 if value & 1 else 0)
    return value


def build_slave(root, sdk, work, binary):
    data = binary.read_bytes()
    # Actual pinned GCC register-ABI handler, not Rugby's stack-ABI signature.
    prefix = bytes.fromhex("2f0a2f022479")
    suffix = bytes.fromhex("102a0c004600122a0e000001004015410e00")
    matches = [i for i in range(0, len(data) - 27, 2)
               if data[i:i + 6] == prefix and data[i + 10:i + 28] == suffix]
    if len(matches) != 1:
        raise ReleaseError("Unsupported ACE keyboard handler: expected one register-ABI signature")
    (work / "game-version.i").write_text(
        f"ASTRA_SIZE = {len(data)}\nASTRA_CRC = ${crc16(data):04x}\n")
    relative = lambda p: "/work/" + p.relative_to(root).as_posix()
    # NDK uses *_lib.i; SDK expects *.i. Create aliases only in the build area.
    script = """import pathlib, shutil, subprocess, sys
ndk = pathlib.Path('/opt/m68k-amigaos/m68k-amigaos/ndk-include')
sdk, work, source = map(pathlib.Path, sys.argv[1:])
aliases = work / 'includes/lvo'
aliases.mkdir(parents=True)
for path in (ndk / 'lvo').glob('*_lib.i'):
    shutil.copyfile(path, aliases / path.name.replace('_lib.i', '.i'))
subprocess.run(['vasmm68k_mot', '-m68000', '-Fhunkexe', '-nosym',
    '-I' + str(sdk / 'Include'), '-I' + str(sdk / 'Src/sources'),
    '-I' + str(ndk), '-I' + str(aliases.parent), '-I' + str(work),
    '-o', str(work / 'Astra.slave'), str(source)], check=True)
"""
    subprocess.run(docker(root, "python3", "-c", script, relative(sdk), relative(work),
                          relative(root / "tools/whdload/AstraKick13.asm")), check=True)
    slave = work / "Astra.slave"
    from release_build import check_hunk
    if b"WHDLOADS" not in check_hunk(slave):
        raise ReleaseError("Compiled slave lacks WHDLoad header")
    return slave
