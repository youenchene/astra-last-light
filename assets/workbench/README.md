# Astra Workbench icons

Original Astra artwork generated with Retro Diffusion `rd_pro__default`, two
64×64 transparent masters at **$0.18 each / $0.36 total**. The hangar drawer and
silver/cyan right-facing interceptor are new images. The existing `rd_hero16`
was referenced verbally; no image conditioning was used. No Retromiga artwork
is copied into these assets.

## Packaging contract

| File | DiskObject type | Use |
| --- | --- | --- |
| `Astra-drawer.info` | WBDRAWER (2), real 56-byte DrawerData | Outer HD and WHD drawers |
| `Astra-tool.info` | WBTOOL (3), stack 65536 | Beside native `Astra` executable as `Astra.info` |
| `Astra-whdload.info` | WBPROJECT (4), stack 65536 | Beside `Astra.slave` as `Astra.info` |

The WHD project uses default tool `WHDLoad` and exactly `SLAVE=Astra.slave` /
`PRELOAD`. WHDLoad must be installed by the user. The 64 KiB stack is a launcher
request, not proof of sufficient free RAM on a particular Workbench host. Native
launch/memory acceptance belongs to packaging validation.

Each file has **two 64×48 classic two-plane images**, followed by a genuine
**OS3.5 GlowIcon `FORM ICON`**, with `FACE` and two `IMAG` chunks. Both color
images have their own RGB palette, transparency index 0, and uncompressed chunky
pixels. This is not NewIcons tooltype encoding or a renamed PNG. Older Workbench
uses classic images and its own screen pens; OS3.5-compatible icon libraries can
use the embedded color images. Classic previews use the Workbench 1.3 default
blue/white/black/orange palette, not an embedded classic palette.

## Provenance and offline conversion

- `*-master.png`: original unchanged RD responses.
- `generation.json`: exact prompts, dimensions, seeds, stable idempotency keys,
  task IDs, quotes, actual costs, and master SHA-256 hashes; no credentials.
- `*-normal.png`, `*-selected.png`: exported registered color canvases.
- `*-classic-*.png`: actual four-pen fallback raster exports.
- `conversion.json`: output hashes, bounding boxes and offline transformations.

The interceptor response retained 782 pixels of flat sage background
`RGB(203,214,203)`; conversion clears that exact color only. The original master
remains unchanged. Alpha is thresholded at 128, the full remaining silhouette
is fitted with nearest-neighbor sampling within 60×44, then centered on 64×48.
No visible silhouette is cropped. Selection is authored offline: RGB channels
lift by 18/34/42 with clamping; classic pens 1/3 exchange. Canvas registration
and alpha remain identical between states. No selected-state API requests were
made.

These are generated Astra assets, separate from the game's third-party intro
assets and their licenses. Suggested distribution provenance text: “Original
Astra Workbench art generated with Retro Diffusion; offline conversion and
selected states authored for Astra.” This does not relicense the rest of the game.

## Reproduce / verify (no API calls)

Uses Python 3.12 and the existing AGK pure-Python PNG reader; no packages need
installation. `AGK_KIT` overrides `~/Code/amiga/amiga-game-kit`.

```sh
python3.12 tools/make-workbench-icons.py
python3.12 tools/make-workbench-icons.py --check
python3.12 game/tests/unit/test_workbench_icons.py
python3.12 game/tests/unit/test_workbench_icons.py --previews
```

The last command independently decodes the **serialized .info files**, then
writes `.tmp/workbench-icons/index.html` and native-size PNGs. Open the HTML
manually to see pixel-scaled normal/selected classic/color previews. If the
read-only Rugby checkout exists, its decoded icons are also shown there;
comparison images stay outside distributed assets.

Generation is opt-in: `python3.12 tools/generate-workbench-art.py` only quotes
missing images for free. `--submit` enforces the $0.36 combined ceiling and
preserves completed masters. Pending task IDs are resumed without new charges;
an uncertain POST without a saved task ID stops for recovery, never resubmits.

## Format verification references

The implementation follows the field layout and stream order in AROS's
[DiskObject reader](https://github.com/aros-development-team/AROS/blob/master/workbench/libs/icon/diskobjio.c),
the `FACE` / `IMAG` layout and byte-count-minus-one conventions in its
[OS3.5 icon reader](https://github.com/aros-development-team/AROS/blob/master/workbench/libs/icon/diskobj35io.c),
and the transparency/palette/frameless flag values in
[`icon_intern.h`](https://github.com/aros-development-team/AROS/blob/master/workbench/libs/icon/icon_intern.h).
These were consulted as format references; source code and art were not copied.

The independent test reader also decodes compressed Rugby GlowIcons. Reference
upstream `youenchene/SuperRugbyV` main was verified at
`a31028f539ab43ba49a835da61c8ebd964ce3388`; local original icon Git blob hashes
match upstream: drawer `0b181baa831fa8fbab9bff8b2059ceedbc0a155f`, launcher
`7cb8b25a510d9bcca155f18f5f00a53760f0b229`.

Host structural, exact-pixel and reproducibility tests pass. Native Workbench
rendering and double-click launch validation are pending the packaging agent;
the host previews are not emulator captures.
