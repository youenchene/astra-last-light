#!/usr/bin/env python3
"""Compare complete native captures against the pre-copper double-buffer baseline.

No pixel masks or golden updates: checks every reference *.screen.png, including
both band boundaries, HUD and sprite channels. Extra actual captures are allowed.
"""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--actual", type=Path, required=True)
    args = parser.parse_args()
    captures = sorted(args.reference.glob("*.screen.png"))
    if not captures:
        raise SystemExit(f"FAIL: no reference captures in {args.reference}")
    for reference in captures:
        actual = args.actual / reference.name
        if reference.read_bytes() != actual.read_bytes():
            raise SystemExit(f"FAIL: capture bytes differ: {reference} / {actual}")
        print(f"PASS byte-identical: {reference.name}")
    print(f"PASS {len(captures)} complete captures; no masked regions")


if __name__ == "__main__":
    main()
