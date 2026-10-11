# Sector enemy derivatives and damage/fire badges

`sector_enemies.txt` contains **24 frames, each 16×16**, in zero-based
`level * 6 + kind` order. Each sector's six columns are scout, weaver, gunner,
dart, **unused legacy boss**, asteroid. Frames 4/10/16/22 preserve the original
boss segment as an unused slot; actual campaign bosses use their separate art.

| Sector | Frames | Treatment |
|---|---|---|
| 0 — Orbital Graveyard | 0–5 | Exact original `actors16.txt[0:6]` pixels and RGBs |
| 1 — Veil Nebula | 6–11 | Swept organic fins, branching cyan veins, violet hulls; mineral growths on rocks |
| 2 — Imperial Foundry | 12–17 | Stepped copper armor, rivets and dark vents; irregular sheared slag rocks |
| 3 — Stellar Citadel | 18–23 | Split-tip silver/gold fins and bright shield spines; faceted silver/gold ore |

The four active ship types retain their master hulls and have different fin
attachment positions. Asteroids retain irregular rocky bodies, with no engines
or guns; their passive behavior belongs to game logic. Every active kind has
four distinct transparency silhouettes, checked by the generator.

`bonuses.txt` contains **five 16×16 frames in D/S/R/L/F order**. Every run derives
D from preserved `actors16.txt[10]`, replacing only the 5×7 letter at (5,4)
with white ink 7 and interior ink 2. The orange bezel, all pixels outside that
rectangle, transparency mask and palette are preserved. S/R/L are extracted
unchanged from `actors16.txt[11:14]`. The new white F has
an open right side, cyan rim and violet interior, distinguishing it from the
closed-loop orange D. Pickup sequencing is independent of this storage order.
The display-only D rename retains internal `BONUS_POWER=0` and all upgrade rules.

## Provenance and palette

These are **locally authored derivatives of the imported Retro Diffusion
masters**, not newly generated Retro Diffusion images or untouched model output.
The base sprites remain the first six frames of `actors16.txt`, imported from
`rd_scout16.png`, `rd_weaver16.png`, `rd_gunner16.png`, `rd_dart16.png`,
`rd_boss16.png`, and `rd_asteroid16.png`. See [RD-RICH.md](RD-RICH.md) and its
manifests for original prompts, seeds, hashes and generation costs.

Fins, veins, armor, ore facets and the D/F glyphs are authored offline in
`tools/make-sector-enemies.py`. The F bezel follows the existing authored badge
style; neither D/F nor the original P/S/R/L badges is attributed to RD.
The generator reads but never writes the PNG masters or `actors16.txt`.
It uses the existing fifteen opaque colors plus transparent index zero, leaving
all hero RGBs unchanged. No paid service, key, network access or random seed is
needed. The historical four-badge description in RD-RICH.md describes the base
import; this document records the subsequent fifth-frame extension and P-to-D derivative.

## Reproduce

From the repository root:

```sh
python3 tools/make-sector-enemies.py
python3 tools/make-sector-enemies.py --check
# Optional contact sheet; its parent directory must already exist.
python3.12 tools/make-sector-enemies.py --check --preview /tmp/sector-enemies.png
# Complete legacy import also invokes this generator as its final step:
python3.12 tools/import-rd-rich-art.py
```

Generation and byte-for-byte `--check` use only Python's standard library.
`--check` exits nonzero for either missing or stale output and does not rewrite
assets. Optional previews use the installed kit's `agk.image.Image` API via
`AGK_KIT` (default `$HOME/Code/amiga/amiga-game-kit`) and Python 3.12.
No manifest or native build is involved.

The 576×480 contact sheet shows four sector rows, then D/S/R/L/F; enemy columns
follow the enum order above, including the unchanged unused boss column.
Inspection confirms visible faction outlines/details and the readable open F.
This is source-art validation, not an emulator screenshot, native memory check,
or 50fps acceptance claim. Palette remapping and runtime integration remain the
renderer owner's responsibility.
