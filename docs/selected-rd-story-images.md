# Selected Retro Diffusion story images

## Current implementation — consistent ordinary-story eyes

All four regular160×96 panels now use localized offline derivatives in
`game/art/selected-rd/story-eyes/`: blue irises (ink15), dark central pupils
(ink1) and white highlights (ink7), scaled to each pose's existing eye size.
Only28 pixels changed across the four images; no changes outside explicit eye
masks. Original RD PNG/RGB files and manifest are preserved. The generator
`tools/make-story-eyes.py --check` verifies provenance, pixel edits and outputs
without relying on mutable galleries. No paid generation was used.

Importer and independent PNG oracle explicitly select these ordinary derivatives
after validating the originals. The ending remains the approved almond-eye image:
all12 ending capture comparisons in this run match the previous ending PNG/RGB
byte-for-byte. White border, skin palette, picture dimensions and layout unchanged.

Validation: **111 Python tests, C rules, generation/freshness PASS**. Both-profile
injected campaign runs in `game/build/story-eyes-campaign/` pass all13 scenes,
1,160,320 source-derived pixels per profile, ending/restart/ESC;32 complete PNG
pairs match across profiles. All four ordinary images and ending were inspected.
Production probe/timing OFF restored. Production executable505,984 bytes; tables
59,685 resident bytes. Injected startup A500 free34,152 CHIP /38,392 total bytes
(not a worst-case bound). Performance remains blocked:15 drops/125% peak A500,
11 drops/122% AROS. Known broad-suite failures remain unisolated; no golden updates.

## Previous implementation — narrower almond eyes

Selected `victory-eyes-almond/`, an offline localized eye reshape of the preserved
identity master. The eyes are compressed vertically by up to28% centrally,
tapering toward unchanged outer corners. Only eye-mask pixels change:
671 master pixels and299 runtime pixels; zero changes outside either mask.
Peach skin, the rounded purple bob and the rest of the artwork are preserved.
Canonical `victory.png` and master/RGB hashes retain the normal importer contract;
provenance records the offline method and parent hashes, not a new RD generation.
An earlier **$0.18 RD inpainting attempt was rejected** for portrait displacement
and remains archived in `victory-eyes-refined/`; selected offline correction cost$0.

Validation: **105 Python tests and C rules PASS**; generator freshness and build
PASS. Both `game/build/ending-eyes-preview-{a500,aros}/` production replays pass.
Peach checks preserve the exact498 parent samples and separately verify seven
intentional new skin pixels where eye white/liner was removed. Source checks
cover299,264 pixels per profile; seven complete screenshot pairs are identical,
including palette/title restoration. Both native WIN screenshots were inspected.
Executable505,980 bytes; generated tables59,681 bytes. A500 startup34,160 CHIP /
45,432 total free bytes (not worst-case bounds). Focused zero drops with peak92%
A500 /90% AROS; the A500 ≤90% target and prior broad-suite failures remain open.
Probe/timing flags remain OFF. No golden updates or broad-suite rerun.

## Previous implementation — original-style bob and peach skin

Selected `victory-identity-master/`: a preserved480×288 RD redraw from the
original, using strength0.55 and seed861013, with a rounded side-swept purple bob
and peach/rosy skin. Task `1298f725-b3ed-42c5-aa2a-90bcd7c89513`, cost **$0.06**.
Earlier derivatives remain intact. Runtime remains320×192 with2px white border.

Source skin `#FCA98B` initially quantized to the shared orange ink14 `#FA6`.
WIN now uses **ink11 `#FA9` (peach)** while retaining sky ink14 `#FA6`.
Importer and independent oracle quantize WIN against its displayed palette
(0black,4`#BDF`,11`#FA9`). The original rose ink11 is captured and restored
outside WIN through existing back-frame palette publication. Shared palette.txt
and ordinary story colors are unchanged; the displayed tone is an OCS approximation.

Validation: **103 Python tests, C rules, build and generator freshness PASS**.
Both production replays in `game/build/ending-identity-peach-{a500,aros}/` pass.
`tools/verify-ending-peach.py` checks299,264 source-derived pixels per profile,
including498 peach skin pixels and256 orange sky pixels per WIN capture;
initial/returned title pixels match exactly. Seven complete screenshot pairs are
byte-identical across profiles. Ending/restart/title screenshots were inspected.
Executable506,020 bytes; tables59,721 bytes. A500 startup free34,120 CHIP /
45,392 total bytes. Focused zero drops, peaks92% A500 /90% AROS. A500 still
misses the ≤90% target; startup memory is not a worst-case bound. Prior broad
regression failures remain unresolved and were not rerun; no golden updates.

## Previous implementation — higher-definition RD ending redraw

The selected ending now comes from a **480×288** RD Plus environment redraw
of the original160×96 `victory-a.png`, with strength0.72 and seed861014. It resolves
new hair, eye, flight-suit and spacecraft detail rather than enlarging pixel blocks.
`game/art/selected-rd/victory-detail-master/` preserves the provider master,
320×192 pixel-center-sampled runtime image/RGB, request, quote and hashed provenance.
Task: `1457a6d2-68b0-4016-9921-476da0bf5152`; selected image cost **$0.06**.
A second native320×192 candidate is retained in `victory-detail-native/`;
total spend for this revision **$0.12**. Previous originals/derivatives are untouched.
Both importer and independent oracle verify the original, master, PNG and RGB hashes.
Story160×96 geometry, ending320×192 geometry and2px white inset border are unchanged.

Focused validation: **102 Python tests and C rules PASS**; generator check/build
PASS. `game/build/ending-detail-preview-{a500,aros}/` contains passing production
F9/restart/ESC replays. Three ending captures per profile pass **245,760** exact
source-pixel checks; all six complete captures match byte-for-byte across profiles.
Production executable **503,700 bytes**; tables **57,451 resident bytes**. Startup
A500 free memory: **36,392 CHIP / 47,704 total bytes** (not worst-case bounds).
Focused telemetry: zero drops, peak93%/91% on A500/AROS; the ≤90% gate remains unmet.

**Broad regression validation is blocked:** `bash tools/agk test` reports12/38
passing and26 failures, including `asteroids/hero_dying` (2,840 changed pixels)
and `barrage.agk` line11 (six bullets versus expected seven or more). Cause has
not been isolated against the pre-integration dirty baseline. No goldens were
updated; further validation stopped. The injected full campaign was not rerun for
this redraw. Probe/timing flags remain OFF. Do not infer full-game acceptance
from the focused ending checks.

## Previous implementation — native-size stories and RD-enlarged ending

Story scenes 0–11 now display the preserved originals at **160×96**, positioned
at **(144,68)** without resampling. The window is **(136,56,176,152)** and the
frame **(142,66,164,100)**. Captions/replies begin at **y168/y186**, retaining
28-character wrapping. The height remains divisible by eight for bounded erase.

The ending remains **320×192 at (0,32)**, now with a **2px white inset border**
(ink 7). Its new image is an RD Plus image-to-image enlargement of the original
`game/art/selected-rd/victory-a.png`, not nearest-neighbor scaling. The original
is untouched. The derivative, RGB export, request, quote, task ID and hashes are
preserved in `game/art/selected-rd/victory-upscaled/`. Actual cost: **$0.06**;
task `b4de6aba-a6cb-4ca9-814b-72ed41b29313`. `tools/upscale-victory-rd.py`
quotes by default and resumes the same paid task with `--generate`.

**F9 on a ready title screen** previews the ending in production. Release then
press Fire/Space to restart; ESC returns to title. F9 is ignored outside TITLE.

Validation for this revision:
- C rules: PASS; Python discovery: **99 tests PASS**; generated-data check PASS.
- `game/build/story-upscale-ending/report.json`: both profiles pass all 13 scenes,
  **1,160,320 source-derived pixels per profile**, consecutive ending buffers,
  held/released fire, restart and ESC. This is an injected campaign fixture.
- Production F9 replay passes on both profiles, with captures under
  `game/build/story-upscale-preview-{a500,aros}/`.
- Generated tables: **49,180 resident bytes**. Production executable:
  **495,428 bytes**; probe OFF restored. Injected startup A500 reports
  **44,664 CHIP / 48,952 total free bytes**, not a worst-case memory bound.
- Global 50fps acceptance remains blocked: observed injected campaign A500
  **16 drops / 125% peak**, AROS **11 drops / 122% peak**. These observations
  are not performance acceptance and do not establish an ordinary full clear.

## Previous implementation — larger panels and dedicated WIN

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
