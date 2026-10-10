# Retro Diffusion rich sprites and scrolling corridors

These are the preserved masters behind the active hero, sector enemy/asteroid
derivatives and decor sources. They are not the earlier rejected three-color
concepts or hand-authored placeholder sprites.
The original generated PNGs are preserved unchanged beside their imported text
strips. Generation metadata is in `rd-rich-manifest.json`; input hashes and
post-processing details are in `rd-rich-import.json`.

## Generated masters

All masters use Retro Diffusion **`rd_pro__default`** with the existing OCS
palette. Cost was **$0.18 each, $1.98 total**. The interrupted weaver job was
recovered by its existing task ID, not submitted and charged again.

| Master | Size | Seed | In-game use |
|---|---|---:|---|
| `rd_hero16.png` | 32×32 | 6701 | Silver/cyan right-facing hero, now imported as 32×24 |
| `rd_scout16.png` | 32×32 | 6702 | Orange scout |
| `rd_weaver16.png` | 32×32 | 6703 | Violet crescent/manta alien |
| `rd_gunner16.png` | 32×32 | 6704 | Armored copper gunship |
| `rd_dart16.png` | 32×32 | 6705 | Narrow blue/silver fighter |
| `rd_boss16.png` | 32×32 | 6706 | Preserved legacy boss segment; unused sector-strip slot |
| `rd_asteroid16.png` | 32×32 | 6707 | Cratered bronze/gray asteroid |
| `rd_decor0.png` | 64×64 | 6710 | Wrecked steel hull, pipes, orange lights |
| `rd_decor1.png` | 64×64 | 6711 | Violet/cyan crystal borders; corridor-connected backdrop uses space ink 0 |
| `rd_decor2.png` | 64×64 | 6712 | Industrial girders, vents and furnace plating |
| `rd_decor3.png` | 64×64 | 6713 | Silver citadel armor and ion-lit reactors |

The full prompts are retained in the generation manifest. Sprite requests used
background removal; decor requests used opaque output and horizontal tiling.
No API credentials are stored in the repository.

## Conversion, not a claim of untouched output

`tools/import-rd-rich-art.py` performs nearest-neighbor fitting to OCS sprite
columns, palette quantization, and transparent padding. An opaque flat border
can be flood-cleared if needed; this batch's metadata records **zero** such
removed pixels because the generated transparency was already usable.

- `hero32.txt`: two 32×24 frames. The existing 32px master is fitted to 22 rows and
  centered, retaining more detail than the earlier 16px import. The second frame
  cycles its warm engine colors. This enlargement incurred no new API charge.
- `actors16.txt`: fourteen preserved 16×16 authoring frames, no longer compiled
  as a runtime strip. The first six are the generated enemy
  and asteroid masters. Normal projectile frames use their top 4 rows, hostile
  bullets 8, and charged pulses 10. Hostile frame 8 contains **one 6×8 bullet** in its
  upper-left corner; the rest is transparent. Its simulation entity and collision
  rectangle also describe just one bullet. Projectile artwork and P/S/R/L badges remain
  hand-authored for crisp readability, and are not attributed to the model.
- `decor.txt`: top 24 and bottom 24 rows of each 64×64 master, yielding eight
  64×24 frames. Two corridor-facing rows are cleared, and the final column
  matches the first to clean the horizontal seam.
  For sector 2 only, after those steps, a four-neighbor flood starts at the
  corridor-facing edge (top crop's last row, bottom crop's first row), traverses
  indices 0/1 with horizontal wrap, and maps reachable index 1 (`#112`) to 0.
  This clears 293 top / 251 bottom backdrop pixels while retaining 53 top / 105
  bottom disconnected index-1 shading pixels. All other indices, other sectors
  and PNG masters remain unchanged. Counts and processing are recorded in
  `rd-rich-import.json`; runtime ink 0 is the sector's space color `#102`.
- `bullets.txt`: four 16×10 pixel-only frames, quantized to 2bpp white/pink/cyan
  for independent channels 6 and 7. Only the hostile frame is now used by sprite
  DMA. Its rounded 6×8 orb doubles the former width and height.
- `pshot.txt` and `lance.txt`: masked 4bpp BOB sources for normal player fire
  (16×4 strip, 8×4 visible bolt) and two 16×10 lance frames. These retain the
  authored playfield colors instead of the restricted bullet-sprite palette.
- `sector_enemies.txt`: the active **24-frame 16×16** bitmap strip, indexed by
  `level * 6 + kind`. The first sector copies the original six frames exactly;
  later sectors are locally authored derivatives with faction-specific silhouettes,
  details and colors. Each sector retains an unused legacy-boss slot. See
  [SECTOR-ENEMIES.md](SECTOR-ENEMIES.md) for precise provenance and frame layout.
- `bonuses.txt`: **five 16×16 P/S/R/L/F frames** with 4bpp pixels and generated
  masks, declared `kind = "bob"`. The historical four-badge base import extracts
  `actors16.txt[10:14]`; the offline sector generator appends the authored F.
  Storage order differs from the gameplay drop cycle P/F/S/R/L.

Hero, sector enemies and decor are declared `kind = "bitmap", depth = 4`: AGK emits
pixel-only interleaved strips. The game's DMA writer splits hero/enemy frames
into attached low/high hardware parts at startup and caches them in two streams.

“16-color” means **15 opaque colors plus transparent index 0**, not sixteen
opaque colors. Individual sprites use the subset their art needs; the enlarged
hero uses twelve. They are genuinely 4bpp, not the old three-color mode. The
32px hero consumes channels 0–3; enemies use attached 4/5, while enemy bullets use
independent 6/7. Player shots, lances and bonuses consume no sprite channels.
The playfield's slot 4 is brightened for the 96 bitplane stars and HUD accents;
the separate sprite palette keeps the original asset colors. Its indices 7/13
and 11/14 are swapped; conversion remaps hero/enemy pixels to preserve RGB while
registers 29–31 expose white/pink/cyan for the 2bpp bullet streams.

## Reproduce and verify

```sh
# Local-only import; no API calls or charges:
python3.12 tools/import-rd-rich-art.py
bash tools/agk art
python3 tools/verify-rich-art.py

# Only missing masters are generated; dry-run checks their price for free:
python3.12 tools/generate-rd-rich.py --dry-run
python3.12 tools/generate-rd-rich.py
```

The generation runner saves task IDs before polling and uses stable idempotency
keys. Existing files are never regenerated automatically. Use `--resume-task
NAME TASK_ID` to recover an existing job. A build needs **no Retro Diffusion key**:
the PNG masters and converted text sources are already present. The local importer
invokes `tools/make-sector-enemies.py` as its final step; sector derivatives and
the F badge require no new paid generation.

The four original title PNGs are converted by `tools/make-title-plates.py` into
read-only `title-plates.h` data, selected by sector and copied eight rows at a
time through one CHIP staging bitmap. `--check` verifies deterministic output;
`--compare-art` can compare Graveyard against pre-removal generated `art.c`.
Gameplay uses moving top/bottom strips and stars in every sector. Veil Nebula's
crystals render through both bitmap and copper paths, with only the derived
corridor-connected backdrop mapped to space ink 0 (`#102`). HUD and play bounds
remain unchanged.

The runtime-only art manifest omits unused compiled sections `player`, `fleet`,
`shot`, `scene`, `actors16`, `graveyard`, `nebula`, `foundry`, `citadel` and `campaign_flash`.
All source art remains available; removing those sections is not deleting masters
or removing active runtime boss-flash rendering.
