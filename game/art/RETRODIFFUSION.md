# Retro Diffusion artwork — Astra polish pass

**Historical pass:** the large backdrops below are now title-only. Current
full-color sprites and scrolling decor are documented in [RD-RICH.md](RD-RICH.md).

Generated using the installed AGK Retro Diffusion client (`agk art-gen`) with
the existing 16-color OCS palette. Source PNGs remain editable/importable; the
Amiga converter, not the model, determines final bitplane and palette data.

## Accepted and integrated

All four use `rd_pro__default`, 128×96 pixels, four bitplanes, and the game's
palette. Each cost $0.18; these are actual API outputs, not hand-drawn substitutes.

| Source | Seed | Prompt direction |
|---|---:|---|
| `graveyard.png` | 6401 | Shattered ringed gas giant over the wreck of an imperial cruiser; icy blue plating, cyan rings and amber wreckage; side-view space opera |
| `nebula.png` | 6402 | Magenta/violet ion cloud curling around a cyan crescent moon; long sweeping shapes and luminous silver edges |
| `foundry.png` | 6403 | Imperial orbital shipyard with gunmetal gantries, orange furnace bays, hull plating and antenna spires |
| `citadel.png` | 6404 | Gothic alien stellar fortress with silver armor, luminous cyan reactor spires and tiny warm windows |

Prompts requested crisp Amiga pixel-art clusters, readable silhouettes, and no
text/stars/borders. The default background-removal option was used. They are
drawn at native resolution—unlike the original 16×16 enlarged placeholders.
Opaque index-0 pixels and transparent regions both appear as the chosen space
background in these unmasked static bitmaps; no runtime alpha blending is used.

## Rejected concepts, preserved but not built

`hero_rd.png` (seed 6501, $0.06) and `raider_rd.png` / `raider_rd_alt1..3.png`
(seed 6502, four variants, $0.24 total) used the low-resolution model at 16×16
with cyan/white/gold. The model produced low-contrast, poorly readable miniature
silhouettes; an enemy variant also enumerated shared sprite colors differently.
These concepts are **not in `art.toml` or the executable**. The readable original
hero/enemy text-art was retained for that earlier pass; the current rich-sprite
pass replaces it with accepted Retro Diffusion masters, as detailed in RD-RICH.md.

The two animated 16×10 charge-pulse frames in `shot.txt` are hand-authored,
not represented as AI output. They share the required cyan/white/gold sprite
palette and use one multiplexed hardware channel each.

Total generation spend for this pass: **$1.02**. No credentials are stored here.
Generation does not change the separate licenses/provenance of the ACE and
Micrix assets in `intro/`.
