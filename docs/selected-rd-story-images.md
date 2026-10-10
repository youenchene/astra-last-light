# Selected Retro Diffusion story images

## Current implementation — larger panels and dedicated WIN

Selections remain **1B / 2B / 3B / 4B / 5A**. Preserved 160×96 PNGs, provider
metadata, RGB exports and legacy procedural assets are unchanged. No new art
generation was performed.

| Layer | Image geometry | Surrounding layout |
|---|---|---|
| Scenes 0–11 | **140×84 at (162,68)**, exact 5:3 | 144×84 byte-aligned slot at (160,68), two ink-0 padding pixels per side; unchanged (152,56,160,136) window |
| WIN, phase 5 / scene 12 | **320×192 at (0,32)**, exact 2× master | Black margins; only DAWN RESTORED at y12 and FIRE TO RESTART at y237 |

Ordinary image area grows **27.604%** over 128×72. The frame is (158,66,148,88).
Existing meaningful headings remain at y60; caption/reply start at y156/y174,
with intact 4×6, 28-character word wrapping. Entry headings remain omitted.
The ending covers 75% of the screen and has no ordinary card, HUD, world,
stars, copper decor or hardware hero/enemy/bullet sprites. Ships depicted in
the selected ending artwork are part of that original image.

Sampling is offline floor nearest-neighbor: ordinary `(x*8//7,y*8//7)` and
ending `(x//2,y//2)`. Nearest palette-color quantization and lowest-index ties
are unchanged. Ordinary ink 0 retains the sector override; WIN overrides ink 0
to actual black. Ink 4 retains `#BDF`. Native source-pixel checks include these
palette rules and the slot padding.

WIN clears each physical framebuffer at eight rows per step, then bypasses
every world composition stage. Its dedicated margin and image tables decode
directly into the bound back bitmap. Existing two-target/vblank acknowledgement
controls readiness; each back copper list disables decor and publishes empty
sprite streams before becoming visible. Ordinary CLEAR/boss-death ship
visibility and immobility remain. WIN still requires readiness, release and a
fresh press after 25 acknowledged ticks; it does not auto-dismiss at 150.

### Compression and loader correction

Mixed-height cards/images have generated descriptors (height, byte span,
destination, row-table offset and optional gap). Flattened U16 row tables index
shared four-plane descriptors. Plane streams use repeats, literal blocks,
packed byte-dictionary literals and offline-selected references to bytes already
decoded in the same layer. A layer must begin at row zero and resume on the same
physical bitmap. No new allocation, framebuffer or runtime resizing is involved.

Every complete row fits **320 output bytes / 64 commands**; every call makes
progress within those bounds. Current stream pool: **29,976 bytes**, safely below
65,536. All generated tables total **42,225 bytes**, versus 50,323 for the failed
larger-image candidate (**−8,098**) and 39,887 for the preceding 128×72 version
(**+2,338**). Word tables remain aligned. The actual 68000 decoder audit finds
only `_memset` as an undefined helper, with no multiply/divide or allocator helper.

The failed **494,716-byte** build and ADF are retained under
`game/build/large-manga-a500/failed-astra{,.adf}`. The unchanged A500/6000-frame
cold capture in `large-manga-cold-loader/loader.png` shows **AmigaDOS error 103**,
before entry. After compression admitted the executable, a second failure
reached display allocation with only **2,016 CHIP bytes / 1,944 largest CHIP
block**, despite **421,704 total free bytes**. Its monolithic code hunk had been
loaded into CHIP; this was physical-bank placement, not absence of total RAM.

Generated constant tables now use a separate ordinary `.data` hunk. The final
code hunk is **423,184 bytes**, the principal data hunk **42,552**, and BSS
**24,968**. Horizontal glyph masks cache seven unique rows rather than repeated
vertical rows, removing **9,072 redundant BSS bytes** without changing glyph
pixels. Startup-only `display_memory` telemetry and failure-only renderer-owner
telemetry identify this boundary in future failures. No hardware, RAM or timeout
increase was used.

### Current validation — functional scope passed

- **83 Python tests PASS**, host C rules **1/1 PASS**, production/probe builds PASS.
- Independent original-PNG oracle checks all 13 mappings, all card/HUD pixels,
  text bounds, mixed heights, command counts, progress and per-step sentinel write
  bounds. An independent font test covers all 36 glyphs at scales 1/2/4.
- Both profiles pass production `large_manga`, `pause_continuity` and
  `gameover_title`, plus the focused injected `large_ending` scenario.
- Ending fixture checks **1,035,520 source-derived native pixels per profile**,
  all 13 scene pairs, all 12 exact ordinary dwell times, eight hero/four boss
  death pauses, channel ownership, held ending, release/fresh restart and ESC.
  WIN checks cover all 81,920 screen pixels, including margins, from its very
  first publication and on consecutive ready buffers: no HUD, hero, decor,
  stars or stale ordinary-card pixels can be masked out.
- The old pause checker failure was sampling: 60 held ticks could yield only two
  periodic samples. The PLAY pause now holds 160 ticks, guaranteeing at least
  three 50-tick samples; every existing clock/pixel/input assertion is retained.
- **50 complete 320×256 captures per profile are byte-identical across profiles**.
  The first 48 A500 images were inspected uncropped in six native-resolution
  contact sheets; the added first-ending/consecutive-buffer captures were
  inspected individually. Repeated captures from the final run also match the
  previously reviewed images exactly. Identical AROS counterparts share those
  pixels. No golden update.
- Allocation-safety ASAN/UBSAN checks pass all 16 audio failure positions/retries,
  BOB/bitmap failures and exact preservation of all 21 audio arrays.
- `ASTRA_CAMPAIGN_PROBE` and `ASTRA_PRESENTATION_TIMING` are **OFF**. The focused
  runner restored production in `finally`; final executable **487,888 bytes**.

| Startup | Free CHIP | Total free RAM |
|---|---:|---:|
| Production A500 | **51,616** | **63,432** |
| Probe-ON A500 | **51,616** | **56,384** |
| Production AROS | **152,248** | **1,374,168** |
| Probe-ON AROS | **152,248** | **1,367,120** |

Before production A500 display allocation, CHIP is **408,472 bytes free**, with
a **408,400-byte largest block**. This demonstrates restored allocation headroom,
not formal worst-case or exact pre-loader largest-block headroom. Versus the
preceding 128×72 production build, executable size grows **3,516 bytes**, free
CHIP changes **−4,504**, and total free RAM changes **+5,712**; actual placement
and BSS savings explain why asset/file size alone does not predict free CHIP.

Opening preparation has **136 held work iterations per bitmap**; measured input
transition to first/both visible is **137/274 vblanks (2.74/5.48 s)** on both
profiles. Closing remains 16 held iterations per bitmap and 17 vblanks between
publications. WIN preparation has **159 held iterations per bitmap** and **160
vblanks (3.20 s)** between first-target and both-ready acknowledgements.

Final evidence and artifact SHA256s:
`game/build/large-ending-both-buffers/{report,final-evidence}.json`, with seven
full-resolution review sheets. The initial six reviewed sheets and actual
`presentation-68000.txt` audit remain in `game/build/large-ending-accepted/`.
Production cases are `large-manga-hunk-split-{a500,aros}`,
`large-manga-pause-{a500,aros}` and `large-manga-gameover-{a500,aros}`.

**Performance optimization is deferred until the parent commit.** These are
functional checks, not global 50fps acceptance. Observations remain visible:
opening/GAMEOVER have zero drops and 92%/89% peaks; pause has zero drops and
90%/88% peaks; the injected journey has **22/15 drops, 122%/119% peaks** (A500/AROS).
Zero drops and <=90% remain the unchanged global gate. Decoder-only raster cost,
full ordinary campaign clear, native OOM fault injection and formal worst-case
memory/performance remain unproven. No commit, GUI, cleanup or paid generation.

### Reproduce current checks

```sh
python3.12 tools/make-presentation.py --check
python3.12 -m unittest discover -s game/tests/unit -p 'test_*.py'
bash tools/agk unit
bash tools/agk build
python3.12 tools/check-large-ending.py --out game/build/NEW-ending-evidence
python3.12 tools/audit-presentation-code.py --out game/build/NEW-decoder-audit.txt
python3.12 tools/check-allocation-safety.py
# For each PROFILE=a500,a500-aros, with fresh OUTPUT paths:
bash tools/agk run --profile PROFILE --no-build --fresh -f game/tests/native/large_manga.agk -o OUTPUT
python3.12 tools/verify-precomputed-cards.py --scene 0 OUTPUT
bash tools/agk run --profile PROFILE --no-build --fresh -f game/tests/native/pause_continuity.agk -o OUTPUT
python3.12 tools/verify-pause-continuity.py OUTPUT
bash tools/agk run --profile PROFILE --no-build --fresh -f game/tests/native/gameover_title.agk -o OUTPUT
python3.12 tools/verify-gameover-title.py OUTPUT/serial.txt
```

## Historical 128×72 implementation and first validation stop

The applied selection is **1B / 2B / 3B / 4B / 5A**: `graveyard-b`, `nebula-b`,
`foundry-b`, `citadel-b`, `victory-a`. Original 160×96 PNGs and full provider
records (prompts, seeds, task IDs, source hashes and original costs) are preserved
under `game/art/selected-rd/`. The procedural sources and their legacy compact
derivatives remain intact. No new generation is involved.

`tools/preserve-selected-rd.py` imports only existing, hash-matched sources and
refuses differing overwrites. Lossless RGB hex exports allow the game-only build
to use standard Python without an image-library dependency. The independent
validator decodes the original PNGs instead of trusting these exports.

Conversion is offline, integer floor nearest-neighbor sampling to **128×72**:
source `(x*160//128, y*96//72)`, then minimum squared RGB distance to the sixteen
existing `palette.txt` colors expanded by nibble ×17. Ties choose the lowest
index. There is no dithering or runtime resampling. Native checks apply the
existing sector ink-0 override and PLAY ink-4 `#BDF` override explicitly.

Window `(152,56,160,136)` is retained. Image `(168,72,128,72)` and frame
`(164,68,136,80)` enlarge image area by 28.57%. Caption/reply local y positions
are 96/116; two reply lines finish at local y129. All thirteen narratives and
meaningful headings remain; entry headings/instructions remain omitted.

Five compressed row tables share one byte pool with static card/HUD rows.
Scene mapping is 0–2→Graveyard, 3–5→Nebula, 6–8→Foundry, 9–11→Citadel, 12→Victory.
The bound back bitmap receives at most **320 bytes / 64 decode operations** per
step (at most five 64-byte image rows). The cursor remains per physical bitmap.
No staging allocation is required: the 17,920-byte CHIP strip and its compiled
source are removed. Exactly two framebuffers remain. Shared generated data is
39,887 bytes, versus 20,234 before (+19,653); ordinary data can spill into CHIP.
Actual executable size and free memory must be measured, not inferred from this
payload ledger. No frame publication or input/pause/boss-flight behavior changes.

## Historical 128×72 validation status

Host validation passes: **81 Python tests**, C rules **1/1**, generator freshness
and native build. Production executable is **484,372 bytes**; ADF is
`game/build/astra.adf`. Both diagnostic flags remain OFF.

The A500 `pause_continuity.agk` replay passes its harness assertions and emits
nine screenshots under `game/build/selected-rd-pause-a500/`. Actual startup:
**56,120 CHIP / 57,720 total free bytes**. Emitted performance windows report
zero drops, peak 89%. These are scoped observations, not worst-case acceptance.
Opening has 131 held work iterations per bitmap, first publication after 132
vblanks and both ready after 264 (5.28 seconds); closing remains 16 held work
iterations per bitmap and 17 vblanks between publications. Decoder-only raster
cost has not been measured.

**Stopped on a new validator failure**, before AROS or campaign runs:

```
python3.12 tools/verify-pause-continuity.py game/build/selected-rd-pause-a500
ValueError: phase 1: insufficient pause samples
```

`serial.txt` has paused PLAY samples at frames 965 and 1000, then resume at 1029.
The validator requires at least three paused samples; a roughly 64-tick pause
combined with 50-tick periodic telemetry is phase-dependent. The two observed
paused samples retain stage/sim=8, enemy_tick=6, enemy_acc=8 and ship=(32,126).
This establishes insufficient sampling, not complete pause validation. Proposed
correction: make the replay's sampling window deterministic while preserving all
clock/input assertions and emulator timeouts. No corrective change was applied.

Visually inspected native captures: `opening_first.screen.png` (selected
Graveyard B, enlarged frame/dialogue and visible hero) and `play_paused.screen.png`
(removed story window, visible hero and PAUSE). The companion checker aborts
before pixel validation, so fresh native exact-source-pixel acceptance is still
pending. Host original-PNG checks cover all five panels/all thirteen mappings.

Unvalidated: AROS, probe-ON startup/campaign, all-thirteen native windows,
boss-flight regressions, decoder stage timing, allocation-safety rerun and
worst-case memory/performance. The known probe-ON allocation failure is not
claimed fixed. Hardware/RAM, timeouts, sound and performance thresholds are
unchanged. No further tests/builds or runtime corrections followed this failure.
