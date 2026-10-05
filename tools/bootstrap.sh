#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KIT="${AGK_KIT:-$HOME/Code/amiga/amiga-game-kit}"
ACE_REV=10ca68a321989738e9ac40f895bdd9f1d8e040fe
KIT_REV=4d825a05a8d8dfcf8d824d70f0cb53b2f350fc7a
if [[ ! -x "$KIT/tools/agk" ]]; then
  printf 'Install https://github.com/codebase/amiga-game-kit at revision %s and run its tools/setup.\nSet AGK_KIT to that checkout.\n' "$KIT_REV" >&2
  exit 1
fi
if [[ "$(git -C "$KIT" rev-parse HEAD)" != "$KIT_REV" ]]; then
  printf 'Warning: AGK differs from tested revision %s.\n' "$KIT_REV" >&2
fi
ACE="$ROOT/game/vendor/ACE"
if [[ ! -d "$ACE/.git" ]]; then
  mkdir -p "$ROOT/game/vendor"
  git clone --branch feat/multiplexed-sprites https://github.com/youenchene/ACE.git "$ACE"
  git -C "$ACE" checkout --detach "$ACE_REV"
fi
if [[ "$(git -C "$ACE" rev-parse HEAD)" != "$ACE_REV" ]]; then
  printf 'Unexpected ACE revision. Preserve local work and restore %s manually.\n' "$ACE_REV" >&2
  exit 1
fi
PATCH="$KIT/patches/ace-agk.patch"
if git -C "$ACE" apply --reverse --check "$PATCH" 2>/dev/null; then
  printf 'ACE AGK compatibility patch already applied.\n'
else
  git -C "$ACE" apply --check "$PATCH"
  git -C "$ACE" apply "$PATCH"
fi
PATCH_SOURCE="$ROOT/tools/patches/ace-allocation-safety.patch"
# Keep the repository patch LF-only; the pin uses CRLF for bob.h/bob.c.
# Materialize those hunk endings without letting autocrlf rewrite vendor files.
PATCH="$(mktemp)"
trap 'rm -f "$PATCH"' EXIT
python3 - "$PATCH_SOURCE" "$PATCH" <<'PY'
import pathlib
import sys

lines = pathlib.Path(sys.argv[1]).read_text().splitlines(keepends=True)
is_bob = in_hunk = False
for i, line in enumerate(lines):
    if line.startswith("diff --git "):
        is_bob = line.rstrip().endswith(("/bob.h", "/bob.c"))
        in_hunk = False
    elif line.startswith("@@ "):
        in_hunk = True
    elif is_bob and in_hunk:
        lines[i] = line.rstrip("\n") + "\r\n"
pathlib.Path(sys.argv[2]).write_bytes("".join(lines).encode())
PY
if git -C "$ACE" -c core.autocrlf=false apply --reverse --check "$PATCH" 2>/dev/null; then
  printf 'ACE allocation safety patch already applied.\n'
else
  git -C "$ACE" -c core.autocrlf=false apply --check "$PATCH"
  git -C "$ACE" -c core.autocrlf=false apply "$PATCH"
fi
printf 'Ready. Build: bash tools/agk build\n'
