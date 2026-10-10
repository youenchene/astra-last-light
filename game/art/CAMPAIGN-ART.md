# Original local campaign pixel art

## Provenance

These six text-art sources are **new, original, locally authored procedural
pixel art**, drawn by the AI coding agent's geometric/pixel source in
`tools/make-campaign-art.py`. They are not Retro Diffusion output, human-painted
illustrations, or scaled versions of previous sprites. The generator reads only
the existing world `palette.txt`; it reads no input illustrations, portraits,
image masters, recordings, credentials or network resources. Generation is free,
offline and deterministic: integer rasterization, explicit pixel coordinates,
no random seed, no external image/font dependency and no antialiasing.

The original Retro Diffusion masters and their provenance remain separate; see
[RD-RICH.md](RD-RICH.md). ACE/Micrix assets and their independent licenses remain
documented in [intro/README.md](intro/README.md).

The palette is the existing sixteen-entry world palette, unchanged. Masked art
uses index 0 solely for transparency and indices 1–15 for opaque pixels. Manga
frames have an entirely opaque color table, including slot 0 (`0x001`), and all
their actual pixels use indices 1–15. No new palette or runtime color changes are
required. The portrait's amber/rose skin and violet hair deliberately work within
that limited palette. Previews use palette.txt RGB; the live world's existing
index-4 brightening may affect gray shading and needs native review.

## Art direction and zero-based frame order

The pilot is a consistent original character: violet asymmetric fringe, cyan
almond eyes, a cheek mark, silver flight suit and an open-face helmet with a
side-mounted communicator. Each sector changes the expression and surrounding
story; the final portrait removes the helmet, reveals longer hair, smiles and
raises a gloved two-finger salute. This is a newly drawn manga-style composition,
not a photorealistic portrait or a claim of matching another artist's style.

| Frame | Sector | Boss silhouette | Manga story |
|---|---|---|---|
| 0 | Orbital Graveyard | Salvage claw: open grapple jaws, armored circular amber reactor, forward cannon, scars and rivets | Alert pilot entering a wreck field beneath a ringed planet |
| 1 | Veil Nebula | Manta: swept violet fins, cyan slit eye, forked tail and bioluminescent nodes | Sideways glance toward an organic threat in crystal clouds and a crescent moon |
| 2 | Imperial Foundry | Furnace carrier: broad copper hull, twin gun sponsons, glowing gridded heat chamber and vented service bays | Soot-marked, wary pilot confronting a factory ship under gantries and furnace windows |
| 3 | Stellar Citadel | Crown: silver lance, open ion halo, pinnacles and luminous conduits | Narrow-eyed resolve before the reactor crown and cathedral towers |
| 4 | Victory (manga only) | No additional boss | Unhelmeted smiling pilot salutes; the fighter leaves shattered crown fragments above a dawn world |

Each boss has **one** native 64×48 pose: the four frames are four different
bosses, not four animation phases of one boss. Flashes replace every occupied
boss pixel with white (`0xFFF`) and preserve all transparent holes exactly.

Explosions have eight temporal frames in each size, drawn directly at that size:
ignition, hot expansion, peak white core, cooling bloom, separating lobes,
outward embers, smoke/embers, sparse dying sparks. Lobes follow fixed integer
directions and a lateral shock line; smaller effects are not downsampled PNGs.
The final frame is sparse rather than empty; the parent's effect lifetime should
remove it. The 64×48 effect is intentionally wider than the others.

## Artifact dimensions and sizes

All paths in this table are under `game/art/`. AGK frame sections serialize as
vertical strips; frame N starts at row `N * frame_height` after conversion.
Text byte counts include the color table, comments and LF line endings.

| Source | Native frame | Frames | Strip | Text bytes | Four-plane pixel bytes | Planar source including single-plane BOB mask |
|---|---:|---:|---:|---:|---:|---:|
| `campaign_boss.txt` | 64×48 | 4 | 64×192 | 12,755 | 6,144 | 7,680 |
| `campaign_flash.txt` | 64×48 | 4 | 64×192 | 12,756 | 6,144 | 7,680 |
| `campaign_fx16.txt` | 16×16 | 8 | 16×128 | 2,475 | 1,024 | 1,280 |
| `campaign_fx32.txt` | 32×32 | 8 | 32×256 | 8,747 | 4,096 | 5,120 |
| `campaign_fx64.txt` | 64×48 | 8 | 64×384 | 25,259 | 12,288 | 15,360 |
| `campaign_manga.txt` | 160×96 | 5 | 160×480 | 77,556 | 38,400 | 38,400 (no mask) |
| **Total** | | **37** | | **139,548** | **68,096** | **75,520** |

The installed AGK `Asset.planar()` independently verified the last column with
the first five assets configured in memory as `bob`, the last as `bitmap`, all
depth 4. This does not modify `art.toml` or build the game.

**Memory accounting is not a baseline A500 fit claim.** The kit's BOB mask
constructor repeats mask bits across four planes. Allocating all BOB pixels and
all such masks plus all five panel bitmaps would consume **97,792 bytes** of
bitmap payload (95.5 KiB), before bitmap headers, BOB save areas, allocator
overhead or any separately resident source arrays. Reuse/caching and actual
chip/slow placement belong to integration. Do not count only the 75,520-byte
source representation as live chip usage.

## Reproduce and verify

From the repository root (normal generation needs only Python's standard library):

```sh
python3 tools/make-campaign-art.py
python3 tools/make-campaign-art.py --check

# Installed AGK parser and PNG helper need Python 3.12; no native build:
python3.12 tools/make-campaign-art.py --check --kit-check \
  --preview /var/folders/62/sj1vngrd76v9j3xk7v896j8w0000gn/T/opencode/astra-campaign-art
```

Set `AGK_KIT` if the kit is not at `$HOME/Code/amiga/amiga-game-kit`.
`--check` fails on a missing or byte-different generated source. The generator
validates all dimensions/frame counts, palette bounds, distinct frames, opaque
panels and pixel-exact white flash masks. `--kit-check` independently parses the
on-disk exports through AGK, checks every decoded color/transparency against the
authored pixels, rejects palette warnings and reports planar sizes.

`--preview` writes six temporary PNG contact sheets using the available local
`agk.image.Image` API. Each sheet uses exact nearest-neighbor enlargement: 4×
for bosses/effects, 3× for panels. Checkerboard indicates transparent pixels.
Manga panels read left-to-right across the first row, then the second row; the
unused sixth contact-sheet cell is not an exported frame. PNGs are review aids,
not additional production artifacts or inputs to generation.

SHA-256 of the generated text artifacts:

```text
campaign_boss.txt   6b74c46889268cd3a2ca383306694087d42b20c3c947165ec8537bbd168c7d7b
campaign_flash.txt  6fdd7f6471e625bb68887f3990cfe58dabd8115d4259260f603ce62cd2c0eb0d
campaign_fx16.txt   44416366b9cf6b824b1a2343701fc94b6fbb6ba8ba67de0ccfba8996a484915d
campaign_fx32.txt   4fe4dd051a1cc7d6267387701381ac7d27e4424cc50ad38c86f56327b65e1828
campaign_fx64.txt   e61c04ea72f6463eb9aa56b0cdba9cce06e82111b584fd75d14743c1d3cf72e6
campaign_manga.txt  56e9d2b160f2daecd347536d07731b470e1741408999103d01de7efbd879b886
```

## Parent presentation handoff

The five panels are shared illustration plates, not thirteen scene-specific
animation strips. Parent-owned presentation logic selects the sector frame for
entry/arrival/defeat and frame 4 for victory. Recommended native crop/highlight
regions within a panel (x, y, width, height):

- Pilot portrait: `(4, 2, 60, 90)`; eye detail: `(22, 39, 32, 14)`.
- Sector boss: `(91, 32, 64, 48)`; hero fighter: `(82, 70, 47, 25)`.
- Victory fighter/dawn: `(80, 30, 80, 66)`; salute: `(55, 56, 23, 40)`.
- Helmet glint: `(16, 6, 28, 10)`; use a clipped local highlight, not a global
  palette change that would recolor the world/hero.

Crop reveal, bounded panning and local highlight timing can animate these
presentations while keeping five full-size bitmaps. Arrival can emphasize the
boss crop, defeat the pilot/fighter crop; narrative overlays explain the state
because the shared artwork still contains the boss. This source does not provide
lip-sync, blinking frames, a wrecked-boss variant, or runtime animation code.
All crop bounds must stay within 160×96, particularly at the bottom/right edge.

## Review status

- **Passed:** generation and repeat `--check`; exact dimensions and frame counts;
  distinct frames; opaque panels; exact white-hit masks; existing palette only.
- **Passed:** installed AGK parser/palette round-trip and planar conversion in
  memory for all six assets, with no warnings.
- **Visually inspected:** all four bosses and flashes, all three eight-frame
  explosion contact sheets, all five manga panels. The final detail pass added
  hull service bays/rivets, fin highlights, planet bands and hair highlights;
  the final boss/panel sheets were re-inspected after regeneration. Faces, eyes,
  helmet, four silhouettes, transparent halo/jaw holes and the unique victory
  gesture are readable in these offline previews.
- **Pending parent integration:** manifest registration, actual 320×256 native
  scene screenshots, animated crops/highlights, collision/restoration checks,
  on-machine color review, A500 memory and worst-case PAL50 performance. Offline
  art review is not a native gameplay acceptance or a user art-direction signoff.

Owned deliverables are exactly the generator, these six text files and this
provenance document. Generation writes only the six text assets. Runtime,
manifest, logic, rendering and audio integration remain parent-owned.
# Compact playtest derivative

`campaign_manga_compact.txt` is generated offline by
`python3 tools/make-compact-manga.py` from the preserved `campaign_manga.txt`.
It selects every second source pixel/row, producing five 80×48 panels with the
original palette indices, no new dependencies and no runtime resampling.
`python3 tools/make-compact-manga.py --check` checks exact reproducibility.
Native artistic approval is pending; the original masters remain unchanged.
