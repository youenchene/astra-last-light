"""Use the icon workstream's independent decoder without modifying its files."""
import importlib.util
import struct

from release_archives import ReleaseError
from release_build import ROOT


def validate_icon(data, kind):
    spec = importlib.util.spec_from_file_location(
        "release_icon_reader", ROOT / "game/tests/unit/test_workbench_icons.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class BytesPath:
        def read_bytes(self):
            return data

    try:
        icon = module.read_icon(BytesPath())
        header = icon["header"]
        expected_type = {"drawer": 2, "tool": 3, "whdload": 4}[kind]
        valid = (
            header[48:50] == bytes((expected_type, 0))
            and struct.unpack_from(">I", header, 74)[0] == 65536
            and (icon["drawer"] is not None) == (kind == "drawer")
            and icon["default"] == ("WHDLoad" if kind == "whdload" else None)
            and icon["tooltypes"] == (["SLAVE=Astra.slave", "PRELOAD"] if kind == "whdload" else [])
            and icon["window"] is None
            and len(icon["classic"]) == len(icon["rich"]) == 2
            and icon["classic"][0] != icon["classic"][1]
            and icon["rich"][0] != icon["rich"][1]
            and all(image[:2] == (64, 48) for image in icon["classic"] + icon["rich"])
            and all(h == (0, 0, 2, 1, 3, 0, 0) for h in icon["image_headers"]))
        if not valid:
            raise ReleaseError(f"Invalid {kind} classic/GlowIcon/launch contract")
    except (ValueError, IndexError, struct.error, TypeError, UnboundLocalError) as error:
        raise ReleaseError(f"Malformed {kind} icon: {error}") from error
    return icon
