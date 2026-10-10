# Precomputed static presentation

## Subsequent pause/panel change

The latest source uses 112×64 panels and relocated static frame/dialogue rows.
Generated payload remains 20,234 bytes and the 320-byte/64-operation decoder is
unchanged. Production pause checks pass on both profiles, but the new probe-ON
A500 startup fails before audio allocation. See [current evidence and stop](pause-ship-continuity.md).
The accepted measurements below are the preceding 96×56 revision.

## Final correction — scoped validation passed

The final production build is **476,972 bytes**, with both
`ASTRA_CAMPAIGN_PROBE` and `ASTRA_PRESENTATION_TIMING` **OFF**. The ADF is
`game/build/astra.adf`. Production SHA256 identities are retained in
`game/build/precomputed-accepted/final-evidence.json`; probe-ON executable/ADF
copies and hashes remain in `game/build/precomputed-accepted-campaign/probe-on/`.

### What fixed the blockers

- **Decoder:** dense rows now use literal blocks instead of many two-byte repeat
  commands. Every row carries its precomputed command count. Before starting a
  complete row, the resumable writer checks remaining budgets of **320 output
  bytes and 64 decode operations**. At most four card rows or two HUD rows are
  written per call. Host tests independently decode tokens to verify counts,
  progress, output bounds and pixels on every step, for all 13 cards/eight HUDs.
- **Loader:** the preserved fixed-6000-frame diagnostic screenshot shows
  `Unable to load astra: Error code 103`, before executable entry. This establishes
  AmigaDOS loader memory admission as the failure boundary, not game allocations
  or the serial transport. Literal compression reduces generated data from
  **28,196 to 20,234 bytes**. Fresh probe-ON boots and complete campaigns now pass
  on the unchanged A500/AROS profiles and unchanged timeout. Exact largest-free
  loader block was not measured. Failed binary/ADF hashes, loader screenshot and
  machine snapshot remain under `precomputed-startup-repro/probe-on/` and
  `precomputed-cold-loader/` in `game/build/`.
- **Reporter:** file reading and performance parsing are inside the inspection
  error boundary. Missing/malformed performance is `null`, never fabricated zero.
  Reinspection retains both the original command error and the profile evidence
  error. Regression tests cover empty/missing/malformed traces and restoration.
- **Pixel preservation:** the native baseline comparison exposed a mixed-case
  HUD-name defect shared by the generator and original host oracle. Both now
  implement the original runtime ASCII uppercase behavior; an explicit lowercase
  `r` glyph regression and complete native pixel comparisons guard it. Failed
  candidate evidence is retained, not overwritten or promoted to goldens.

### Final measurements

Same sound-enabled title-latency scenario on both profiles:

| Measurement | Original baseline | Final |
|---|---:|---:|
| Held incomplete iterations (`cut_work`) per opening bitmap | 166 | 122 |
| Opening transition → first visible | 167 vblanks / 3.34 s | 123 / 2.46 s |
| Opening transition → playable/both ready | 334 / 6.68 s | 246 / 4.92 s |
| Accepted fire → first feedback | 45 / 0.90 s | 45 / 0.90 s |
| Accepted fire → playable opening | 384 / 7.68 s | 296 / 5.92 s |
| Accepted fire → combat ready | 567 / 11.34 s | 479 / 9.58 s |
| A500 scenario drops / peak | 0 / 97% | **0 / 90%** |
| AROS scenario drops / peak | 0 / 95% | **0 / 87%** |

Opening preparation is **26.3% faster than baseline** (1.76 s saved). The final
4.92 s deliberately trades one second against the unsafe 3.92 s candidate to
remove its four dropped frames. Window-close repair retains 16 held iterations
per bitmap and 17 elapsed vblanks between first/second acknowledgements. Selection
latencies remain 21–24 vblanks first-visible / 42–48 both-ready.

| Startup measurement | Baseline | Final | Delta |
|---|---:|---:|---:|
| Production executable | 461,332 | 476,972 | +15,640 bytes |
| A500 free CHIP | 62,840 | 46,696 | −16,144 bytes |
| A500 total free RAM | 67,144 | 51,504 | −15,640 bytes |
| AROS free CHIP | 138,808 | 138,808 | 0 |
| AROS total free RAM | 1,377,880 | 1,362,240 | −15,640 bytes |

No new runtime allocation or framebuffer was introduced. Allocation placement
explains why CHIP and total-free deltas differ; ordinary constant data is not
free of CHIP pressure. These are startup measurements, not worst-case proofs.
The final injected executable is 484,156 bytes; its A500 startup free memory is
42,320 CHIP / 44,520 total bytes.

### Stage cost and actual 68000 audit

`tools/check-presentation-cost.py --out game/build/precomputed-raster-cost` built
the optional NON-SHIPPING timing flag, measured both profiles with sound, then
rebuilt OFF in `finally`. Its report records **20 HUD calls / 34 card-row calls
per bitmap** for opening zero. Maximum decoder work: HUD **32 PAL raster lines**
(~2.04 ms), card **67 lines** (~4.28 ms), including interrupt interference but
excluding diagnostic serial reporting afterwards. This isolates the decoder,
not all rendering/main-loop work, and is not a worst-case proof for every scene.

`tools/audit-presentation-code.py` retains the actual production object symbols
and code disassembly in `precomputed-accepted/presentation-68000.txt`. Row address
products compile to native `muls.w`; literal blocks use byte-copy/DBF loops.
The compiler converts repeat filling into bounded **`_memset` calls** (at most
40 bytes each). There are no external multiply/divide/modulo helpers or allocator
calls in the decoder object. Timing instrumentation is absent in production.

### Final validation and image review

- **75 Python tests PASS**, host C rules **1/1 PASS**, native builds PASS.
- Both profiles: title latency, clean transitions, live opening, GAMEOVER return,
  BOB restore, title-sector selection and sector2 scenarios PASS, with their
  strict functional/source-pixel companion validators.
- Independent host comparison covers all 13 card layers/eight HUD variants.
  `verify-precomputed-cards.py` additionally checks **565,760 complete native
  window pixels per profile**: every pixel of all 13 cards, first and late,
  including the five source manga panels, frame and text. No pixel masks.
- Source checks retain all 12,288 title pixels per source and all 15,360 Nebula
  band pixels. Original compact-manga/title generation freshness checks pass.
- **100 full captures per profile** (47 focused + 53 campaign) compare exactly
  across A500 and AROS. All 100 A500 captures were visually reviewed, uncropped
  at native resolution in `review-presentation-*.png`; each has a pixel-identical
  AROS counterpart. Sheet order is recorded in `final-evidence.json`.
- Against the preserved baseline: all 15 clean-transition and four GAMEOVER
  captures match completely, as do nine of ten title-latency images per profile.
  The opening-ready/live-opening differences are exactly **14 hero-engine pixels**
  in the runtime animation chosen by `(frame >> 3) & 1`, reflecting the shorter
  preparation clock. Full diffs were inspected; no screenshot regions were masked.
  Static presentation content is unchanged. See `pixel-differences.json`.
- Allocation safety passes ASAN/UBSAN: 16 sound failure positions/retries,
  BOB/bitmap failures and 21 unchanged generated audio arrays. All five songs
  retain Paula A–C only; original ACE audio hash and 13,624 sector PCM bytes pass.
- Both fresh injected campaigns pass functional checks, all 13 scenes,
  bosses/flashes/effects, lifecycle, F upgrades and channel ownership.

### Remaining global performance boundary

Functional campaign success is **not** strict performance acceptance. Final
campaign windows still report **A500 19 drops / 125% peak**, **AROS 12 / 125%**.
The ordinary BOB replay reports 7/2 drops and 112%/113% peaks. GAMEOVER has zero
drops but 97%/95% peaks; sector2 has zero drops but 91%/88% peaks. These broader
gameplay costs remain visible, outside this static-composition optimization.
No thresholds, audio or hardware were changed. No ordinary full-quota campaign,
real-hardware validation, native OOM injection or formal worst-case memory proof
is claimed. No GUI, commit, cleanup, paid art or golden update was performed.

### Reproduce

```sh
python3.12 tools/make-presentation.py --check
python3.12 -m unittest discover -s game/tests/unit -p 'test_*.py'
bash tools/agk unit
bash tools/agk build
# Use a fresh output directory to retain previous evidence.
python3.12 tools/check-campaign-native.py --out game/build/new-campaign-evidence
python3.12 tools/verify-precomputed-cards.py game/build/new-campaign-evidence/a500 game/build/new-campaign-evidence/a500-aros
python3.12 tools/check-presentation-cost.py --out game/build/new-raster-cost
```

For each profile, run `tools/agk run --profile PROFILE --no-build -f SCENARIO -o
OUTPUT`. Focused final evidence is `game/build/precomputed-accepted/PROFILE/`;
the campaign is `game/build/precomputed-accepted-campaign/PROFILE/`.
Scenario and validator commands are also shown in the historical sections below.

## Historical first candidate — failures retained

Everything below describes the earlier rejected 640-byte/RLE candidate, not the
final build above. Its measurements and failure evidence remain available.

## Implementation

Static story and HUD graphics are compiled offline by
`game/tools/make-presentation.py`, with `tools/make-presentation.py` as the host
`runpy` entry point. CMake runs `--check` against the implementation inside the
game-only Docker mount. It fails on stale/missing generated output rather than
regenerating it. Inputs include scene text, scene font, stage names and HUD font.
The generated banner and data are unchanged by the approved path correction.

`game/art/presentation-rows.h` contains **28,196 bytes** of deduplicated byte-run
rows and row-offset tables: all 13 cards and eight sector/charge-label HUD variants.
`presentation_rows.c/.h` owns the planar writer. It writes up to eight card rows
or four HUD rows, **640 output bytes per step**. The host oracle verifies every
pixel and preservation of all bytes outside each step's destination.

`render_scenes.c` retains the five existing 96×56 manga sources and per-bitmap
cursors; generated rows replace clearing/frame/text composition, followed by the
existing bounded manga blits. The current 4×6 font, omitted entry headings and
removed continuation instruction are retained. `render_world.c` consumes static
HUD rows before dynamic numbers/bars. Dynamic HUD updates, stars, decor,
palette/copper, BOB restoration and atomic publication remain runtime-owned.
No framebuffer, staging bitmap, font atlas or runtime allocation was added.

**The current 640-byte decode budget is not accepted as frame-safe.** See the
measured regression below; byte bounds alone did not bound decode cost adequately.

## Completed checks

- `python3.12 -m unittest discover -s game/tests/unit -p 'test_*.py'`: **72 PASS**.
  Includes independent pixel comparisons of the production C decoder for all
  13 static card layers and all eight HUD variants, physical-title provenance,
  launch-validator regressions, both generator entry points from unrelated CWDs,
  a copied game-only layout, and nonwriting stale/missing freshness failures.
- `bash tools/agk unit`: **1/1 PASS**.
- `bash tools/agk build`: **PASS**, production executable **484,676 bytes**.
- Both `a500` and `a500-aros`: `title_latency`, `clean_transitions`, `live_opening`,
  `gameover_title` and `bob_restore` scenarios and companion validators **PASS**.
- Title validator checks 12,288 original pixels per illustration, all four sectors
  and wraps. Transition checks cover retained complete frames and independent repair
  identities. Live-opening checks cover visible movement, source-exact shots and
  BOB restoration. GAMEOVER retains 150 ready ticks and held-input protection.
- BOB checks cover 164 opaque/92 transparent artwork pixels, the full 768-pixel
  restore region, real drop/collection and the 40-tick hero pause.

Evidence directories are `game/build/precomputed-optimized-{a500,aros}` for title
latency, and `precomputed-optimized-{clean,live,gameover,bob}-{a500,aros}` for the
other checks. Preserved baseline evidence uses `precomputed-baseline-*`.
The A500 opening-ready capture was visually inspected. Full capture review,
native baseline-to-new image comparisons, remaining sector/decor source checks,
68000 hot-path disassembly audit and full campaign coverage remain unfinished
because work stopped on the new failure below. No goldens were changed.

## Measured latency and memory

Same sound-enabled title-latency scenario, both profiles:

| Measurement | Baseline | Precomputed |
|---|---:|---:|
| `cut_work` per opening bitmap (held incomplete iterations) | 166 | 95 |
| Opening transition to first visible | 167 vblanks / 3.34 s | 98 / 1.96 s |
| Opening transition to both ready/playable | 334 / 6.68 s | 196 / 3.92 s |
| Accepted fire to chime request | 44 / 0.88 s | 44 / 0.88 s |
| Accepted fire to first feedback | 45 / 0.90 s | 45 / 0.90 s |
| Accepted fire to playable opening | 384 / 7.68 s | 246 / 4.92 s |
| Accepted fire to combat ready | 567 / 11.34 s | 429 / 8.58 s |

Opening preparation elapsed time falls **41.3%**, including missed vblanks.
Elapsed clocks must not be equated with `cut_work`: the optimized run drops frames.
The window-close repair remains `cut_work=16` per bitmap and 17 elapsed vblanks
between first and second acknowledged repaired publications. Title-selection
latencies remain 21–24 vblanks first-visible / 42–48 both-ready for completed picks.

| Startup measurement | Baseline | Precomputed | Delta |
|---|---:|---:|---:|
| Production executable | 461,332 | 484,676 | +23,344 bytes |
| A500 free CHIP | 62,840 | 42,688 | −20,152 bytes |
| A500 total free RAM | 67,144 | 43,800 | −23,344 bytes |
| AROS free CHIP | 138,808 | 138,808 | 0 |
| AROS total free RAM | 1,377,880 | 1,354,536 | −23,344 bytes |

Generated payload size is not executable growth: removed runtime composition code
and state also affect the result. Resident ordinary data does consume CHIP on A500.
These are observed startup readings, not worst-case free-memory guarantees.

### Performance regression — acceptance blocked

Across emitted 50-frame windows in the title-latency scenario:

| Profile | Baseline drops / peak | Precomputed drops / peak |
|---|---:|---:|
| A500 | 0 / 97% | **4 / 114%** |
| AROS | 0 / 95% | **4 / 113%** |

The new dropped-frame windows occur during opening preparation. On A500 the
three affected windows report `(dropped, load, maxload)` of `(1,31,105)`,
`(1,21,104)` and `(2,35,114)`; AROS reports `(1,31,104)`, `(1,20,103)` and
`(2,34,113)`. The proposed correction is to reduce per-call row/output work and
bound decode-operation cost explicitly, then measure both profiles with sound
and audit generated 68000 code. Exact stage attribution still needs probes or
disassembly; current aggregate windows alone do not isolate individual rows.
No correction has been applied. Global 50fps acceptance remains blocked.

## New campaign failure and stop

Command:

```sh
python3.12 tools/check-campaign-native.py --out game/build/precomputed-campaign
```

Probe-ON build succeeded at **491,860 bytes**. The fresh A500 run failed before
any serial output:

```text
waitserial: timeout waiting for 'AGK ready'
waitserial: serial log tail (0 bytes total)
```

`a500/run.retrosh` and `a500/emulator.log` confirm the existing **6000-frame**
cold-boot allowance was actually used. Thus this is not the old 3000-frame
configuration issue. With no `AGK boot` marker, the evidence cannot establish
whether loading, memory admission or pre-main startup failed. Do not infer a
campaign gameplay/rendering failure from this empty trace.

The runner then hit a secondary reporting defect: `inspect()` invokes
`performance()` before its exception guard, so empty serial evidence raises
`ValueError: missing performance windows` while handling the original failure.
`report.json` retains the original command failure and `production_restored: true`.
The `finally` rebuild succeeded at **484,676 bytes**, and
`game/build/CMakeCache.txt` confirms `ASTRA_CAMPAIGN_PROBE:BOOL=OFF`.

Proposed next work, **not applied**: capture the failed cold-loader screen/state
and diagnose probe-ON startup at the unchanged timeout; repair the report path
to preserve empty-trace failures as structured errors rather than raising a
second exception. Separately correct the measured decoder budget regression.
AROS campaign, all-13 native scene capture review and remaining checks were not
run after this failure. No GUI, commit, cleanup or paid generation was performed.

The earlier approved Docker-path failure is preserved in
`precomputed-presentation-build-failure.txt`.
