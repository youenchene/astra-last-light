# Phase 1 character consistency — review candidate

Offline pixel retouch, cost **$0**. The files at this directory's root are the
final phase-1 candidate. **Pending parent visual approval; not integrated.**
Current production selections, renderer, importer, build and goldens are untouched.

## Review images

- [Five panels: displayed OCS, before/after, ordinary 2x and ending 1x](previews/five-panels-ocs-2x.png)
- [Five panels: displayed OCS at native sizes](previews/five-panels-ocs-native.png)
- [Five panels: source RGB, ordinary 2x and ending 1x](previews/five-panels-source-2x.png)
- [Five panels: source RGB at native sizes](previews/five-panels-source-native.png)

Each detail sheet has BEFORE on the left and AFTER on the right, nearest-neighbor
8x ordinary / 4x ending enlargement. Each includes face and armor together.

| Panel | Source detail | Displayed OCS detail | Mask overlay |
|---|---|---|---|
| Graveyard | [RGB](previews/graveyard-b-source-detail.png) | [OCS](previews/graveyard-b-ocs-detail.png) | [Masks](previews/graveyard-b-masks.png) |
| Nebula | [RGB](previews/nebula-b-source-detail.png) | [OCS](previews/nebula-b-ocs-detail.png) | [Masks](previews/nebula-b-masks.png) |
| Foundry | [RGB](previews/foundry-b-source-detail.png) | [OCS](previews/foundry-b-ocs-detail.png) | [Masks](previews/foundry-b-masks.png) |
| Citadel | [RGB](previews/citadel-b-source-detail.png) | [OCS](previews/citadel-b-ocs-detail.png) | [Masks](previews/citadel-b-masks.png) |
| Ending | [RGB](previews/victory-source-detail.png) | [OCS](previews/victory-ocs-detail.png) | [Masks](previews/victory-masks.png) |

Overlay colors: green = declared armor, orange = cheek cleanup/mark,
magenta = protected complete eye regions, including liners, highlights and brows.
Masks are permissions, not a claim every pixel inside them changed.

## New candidate files and exact parents

| New PNG | Parent under `game/art/selected-rd/` |
|---|---|
| `graveyard-b.png` | `story-eyes/graveyard-b.png` |
| `nebula-b.png` | `story-eyes/nebula-b.png` |
| `foundry-b.png` | `story-eyes/foundry-b.png` |
| `citadel-b.png` | `story-eyes/citadel-b.png` |
| `victory.png` | `victory-eyes-almond/victory.png` |

Each new PNG also has a lossless `.rgb.hex` export and `.displayed.png` palette
preview. Dimensions remain 160x96 for ordinary panels and 320x192 for the ending.
The original ending 480x288 master remains unchanged; no edited master is claimed.

## Design and coordinates

The ending's armor is entirely unchanged. Ordinary armor retains the existing
pose, silhouette, helmet/headset and dark joints. Pale/white plates, silver edge
shading, stable cyan-blue inner seams, collar divisions and small central
fasteners adapt its design language to the small helmeted portraits. Geometry
edits are literal pixel lines/polygons, beyond palette-only substitutions.

Only old cheek identity marks are cleared: Graveyard/Nebula purple marks,
Foundry interior soot and Citadel cyan cheek paint. Facial contour shading,
mouths, noses, hair and eyes remain. The replacement mark is copper ink 13
(`#AA4433`), on pilot-left / viewer-right in every pose.

All coordinates are zero-based source pixels. Boxes below are half-open.
`recipe.json` contains every armor polygon, cleanup polygon/filter/sample,
detail line and cheek coordinate. `provenance.json` records RGB before/after
values for every changed pixel. Binary masks are
`masks/<name>-{armor,cheek,protected-eyes}.png`, with 255 for membership.

| Panel | Mark pixels, in order | Complete eye boxes |
|---|---|---|
| Graveyard | (36,57), (35,58) | (17,46,31,57), (32,48,41,57) |
| Nebula | (40,30), (39,31), (38,32) | (19,17,35,29), (35,19,45,29) |
| Foundry | (38,60), (37,61) | (19,48,34,60), (34,50,44,60) |
| Citadel | (49,60), (48,61), (47,62) | (24,43,42,58), (42,48,52,58) |
| Ending | (127,92), (126,93), (125,94), (124,95), (123,96) | (64,63,94,88), (106,65,134,88) |

## Verification results

| Panel | Changed RGB | Changed OCS | Armor RGB | Cheek RGB | Protected eye pixels |
|---|---:|---:|---:|---:|---:|
| Graveyard | 441 | 441 | 429 | 12 | 235 |
| Nebula | 560 | 560 | 551 | 9 | 292 |
| Foundry | 586 | 585 | 562 | 24 | 280 |
| Citadel | 685 | 685 | 655 | 30 | 370 |
| Ending | 5 | 5 | 0 | 5 | 1394 |
| **Total** | **2277** | **2276** | **2197** | **80** | **2571** |

PASS: exact RGB equality for all 2,571 protected eye pixels; zero changed pixels
outside declared armor/cheek masks; ending changes exactly its five mark pixels;
mark coordinates on skin/old cheek paint with the same diagonal orientation;
allowed armor inks and palette-stable blue/pale motifs; dimensions/RGB exports;
all **95 historical file SHA256s**, including parents, prior derivatives, ending
master and shared palette; output hashes and byte-for-byte regeneration.
One Foundry RGB edit quantizes to the same displayed color, explaining the count
difference. Masks are non-overlapping with all complete eye regions.

Reproduce from the repository root (Python + Pillow, no service calls):

```sh
python3 tools/make-story-character.py --inspect
python3 tools/make-story-character.py --check
python3 tools/verify-story-character.py
```

To recreate missing artifacts use `python3 tools/make-story-character.py`.
Generation refuses differing overwrites. The independent verifier reads saved
PNGs, RGB exports, masks and frozen hashes rather than importing generator code.
`protected-sha256.json` freezes the 95 historical inputs. No historical
provenance file was refreshed or relaxed.

## Visual inspection and remaining judgment

Inspected all five enlarged parents, final OCS face/armor comparisons, RGB
details, ordinary mask overlays and the five-panel native montage. Initial
iterations exposed hair-edge mark placement, residual soot and pink plate
reflections; these were corrected. `draft/` and `draft-v2/` are rejected
diagnostic iterations, **not candidate assets**. Their provenance retains their
pixel edit histories; final checks and review links refer to the root candidate.

- Collars are deliberately simplified at 160x96; the ending's fine hardware
  cannot be replicated literally at this scale. Parent review must judge the
  family resemblance and the brighter ordinary plates.
- Graveyard/Foundry use two-pixel diagonals because their cheeks are narrower;
  using three joined them to nose shading. Nebula/Citadel use three, ending five.
- Foundry's red/dark lower-jaw contour remains: it was treated as contour/ambient
  shading rather than interior cheek soot. This interpretation remains a visual
  review point.
- OCS sheets are offline palette-rendered panel previews, not fresh emulator
  captures. Ordinary panels quantize against the immutable base palette, then
  apply sector ink 0 and ink 4 overrides; ending quantizes against its effective
  black/blue/peach palette. Native integration and validation belong to phase 2.
