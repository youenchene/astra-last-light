"""Strict archive boundaries shared by dependency setup and release verification."""
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tarfile
import zipfile


class ReleaseError(ValueError):
    """An input cannot safely be used for a release."""


def require_tool(name):
    result = shutil.which(str(name))
    if not result:
        raise ReleaseError(f"Missing required tool: {name}")
    return result


def safe_name(name):
    parts = name.rstrip("/").split("/")
    if (not name or name.startswith("/") or "\\" in name or ":" in name
            or any(p in ("", ".", "..") for p in parts)
            or any(ord(c) < 32 for c in name)):
        raise ReleaseError(f"Unsafe archive path: {name!r}")
    return PurePosixPath(*parts)


def extract_lha(archive, target, bsdtar="bsdtar"):
    """Read individual regular members to avoid trusting archive extraction paths."""
    members = read_lha(archive, bsdtar)
    target = Path(target)
    target.mkdir(parents=True, exist_ok=False)
    for name, member in members.items():
        dest = target / name
        if member["kind"] == "dir":
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(member["data"])
            dest.chmod(member["mode"])


def check_member_names(names):
    canonical = [str(safe_name(name)).casefold() for name in names]
    if len(set(canonical)) != len(canonical):
        raise ReleaseError("Duplicate or case-colliding archive members")
    return [str(safe_name(name)) for name in names]


def read_lha(archive, bsdtar="bsdtar"):
    """Return bytes and original member types/modes, never follow archive links."""
    tool = require_tool(bsdtar)
    names = subprocess.check_output([tool, "-tf", str(archive)], text=True).splitlines()
    listing = subprocess.check_output([tool, "-tvf", str(archive)], text=True).splitlines()
    if len(listing) != len(names) or any(row[0] not in "d-" for row in listing):
        raise ReleaseError("Archive contains links or unsupported member types")
    paths = check_member_names(names)
    result = {}
    for name, relative, row in zip(names, paths, listing):
        permissions = row[1:10]
        if any(c not in "rwx-" for c in permissions):
            raise ReleaseError("Unsupported LHA permission bits")
        mode = sum(bit for char, bit in zip(permissions, (256,128,64,32,16,8,4,2,1)) if char != "-")
        directory = row[0] == "d"
        result[relative] = {"kind": "dir" if directory else "file", "mode": mode,
                            "data": None if directory else subprocess.check_output(
                                [tool, "-xOf", str(archive), name])}
    return result


def extract_tar(archive, target):
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            safe_name(member.name)
            if not (member.isdir() or member.isfile()):
                raise ReleaseError("Dependency tar contains links or special files")
        source.extractall(target, filter="data")


def read_zip(archive):
    with zipfile.ZipFile(archive) as source:
        paths = check_member_names(source.namelist())
        result = {}
        for entry, name in zip(source.infolist(), paths):
            mode = entry.external_attr >> 16
            kind = stat.S_IFMT(mode)
            directory = entry.is_dir()
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or mode & 0o7000:
                raise ReleaseError(f"ZIP symlink/special file or unsafe mode: {name}")
            if kind and directory != (kind == stat.S_IFDIR):
                raise ReleaseError(f"ZIP type/name mismatch: {name}")
            if entry.flag_bits & 1:
                raise ReleaseError("Encrypted ZIP members are not release content")
            result[name] = {"kind": "dir" if directory else "file", "mode": stat.S_IMODE(mode),
                            "data": None if directory else source.read(entry)}
        return result


def verify_members(members, expected, executables=()):
    files = {name: item for name, item in members.items() if item["kind"] == "file"}
    dirs = {name for name, item in members.items() if item["kind"] == "dir"}
    allowed_dirs = {str(parent) for name in expected for parent in PurePosixPath(name).parents
                    if str(parent) != "."}
    if set(files) != set(expected) or not dirs <= allowed_dirs or len(files) + len(dirs) != len(members):
        raise ReleaseError("Archive member inventory differs from content contract")
    for name, data in expected.items():
        if files[name]["data"] != data:
            raise ReleaseError(f"Archive content mismatch: {name}")
        mode = files[name]["mode"]
        if not mode & 0o400 or mode & 0o7000:
            raise ReleaseError(f"Unsafe/unreadable archive mode: {name}")
        if name in executables and mode & 0o111 != 0o111:
            raise ReleaseError(f"Archive game is not executable: {name}")


def verify_zip(archive, expected, executables=()):
    verify_members(read_zip(archive), expected, executables)
