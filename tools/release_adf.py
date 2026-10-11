"""Read-only ADF exporter, executed inside the digest-pinned amitools image."""
import base64
import json
import sys

from amitools.fs.ADFSVolume import ADFSVolume
from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory


def export(path):
    device = BlkDevFactory().open(path, read_only=True)
    volume = ADFSVolume(device)
    volume.open()
    if not volume.boot.valid_chksum or not volume.boot.boot_code or volume.is_ffs:
        raise ValueError("Expected a checksummed bootable OFS disk")
    members = []
    seen = set()

    def walk(directory, prefix=""):
        for node in directory.get_entries():
            block = node.block.blk_num
            if block in seen:
                raise ValueError("Cyclic/duplicate disk node")
            seen.add(block)
            name = node.get_file_name().get_unicode_name()
            if not name or "/" in name or ":" in name or name in (".", ".."):
                raise ValueError("Unsafe disk component")
            path = prefix + name
            if node.is_dir():
                members.append({"name": path, "kind": "dir", "mode": 0o755, "data": None})
                walk(node, path + "/")
            elif node.is_file():
                protect = node.get_meta_info().get_protect()
                mode = (0o444 if not protect & 8 else 0) | (0o111 if not protect & 4 else 0)
                members.append({"name": path, "kind": "file", "mode": mode,
                                "protect": protect,
                                "data": base64.b64encode(node.get_file_data()).decode("ascii")})
            else:
                raise ValueError("Unsupported disk node type")
    walk(volume.get_root_dir())
    volume.close()
    device.close()
    return members


if __name__ == "__main__":
    print(json.dumps(export(sys.argv[1])))
