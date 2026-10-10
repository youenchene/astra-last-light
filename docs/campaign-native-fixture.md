# Non-shipping native campaign fixture

This explicitly injected-state fixture is **not an ordinary campaign clear**.
`ASTRA_CAMPAIGN_PROBE` defaults OFF. Only the ON build compiles
`game/tests/native/campaign_probe.c`; the parent's guarded main-loop hooks are
the only integration points. The scenario is below `tests/native/`, outside
top-level test autodiscovery.

## Run

### Precomputed presentation — fresh functional campaign passed

Final evidence is `game/build/precomputed-accepted-campaign/`: **53 captures per
profile, functional PASS on both**, but performance remains **19 drops / 125%**
on A500 and **12 / 125%** on AROS. All captures match across profiles. All 13 native
windows additionally pass independent full source-pixel comparisons. Production
OFF restoration succeeded (476,972-byte executable). The runner now preserves
probe-ON binary/ADF hashes and reports missing performance as unavailable.

The earlier zero-serial failure in `precomputed-campaign/` was diagnosed by a
6000-frame cold-loader capture showing AmigaDOS error 103. Smaller literal/run
data fixes startup without hardware/timeout changes. Failed evidence remains.
See [implementation, exact measurements and limits](precomputed-presentation.md).

### Clean-presentation revision — fresh campaign evidence

After replacing the fixed tick-82 flash marker with the even pre-update snapshot
predicate, `python3.12 tools/check-campaign-native.py --strict-performance` ran
fresh on both profiles. **Functional PASS; strict performance FAIL** (exit 1).

| Profile | Captures checked | Functional | Dropped frames | Peak load | Strict budget |
|---|---:|---|---:|---:|---|
| `a500` | 53 | PASS | 16 | 123% | FAIL |
| `a500-aros` | 53 | PASS | 11 | 120% | FAIL |

All 106 complete captures were visually inspected in native-resolution, uncropped
review sheets (`game/build/campaign-native/{profile}/review-1.png` through
`review-5.png`). The checker passed all 13 static-scene pairs, lifecycle/channel
invariants, F upgrades, bosses, four white flashes and explosion pixels. The old
A500 flash failure sampled countdown 5 (normal-art half); the fixture now selects
the white half without changing runtime blink behavior or weakening pixels.

The runner restored `ASTRA_CAMPAIGN_PROBE:BOOL=OFF` in `finally`, rebuilding the
477,368-byte production executable (probe build: 484,684 bytes). Host validation:
`bash tools/agk unit` passed 1/1 and
`python3 -B -m unittest discover -s game/tests/unit -p 'test_*.py' -v` passed 25
tests, including seven flash-evidence regressions. `bash tools/agk build` passed.
This injected fixture does not prove an ordinary full-quota campaign clear;
zero drops and <=90% peak remain unchanged requirements.

The fixture now captures each of the 13 scenes twice (first acknowledgement and
display tick 40), requiring all 81,920 pixels to remain identical. Total expected
captures become 53. Scene waits allow up to 1000 harness ticks for bounded world
plus overlay preparation of both buffers; this is a timeout, not a runtime delay
or performance-budget change. The scene dwell remains 150 acknowledged ticks.
Historical results below do not validate this revision.

Ordinary combat-entry wait timeouts are now 1000 ticks: world-plus-window
composition, 150 acknowledged display ticks and world restoration must all finish
before `combat_ready`. Input replays after that marker and gameplay assertions
are unchanged. GAMEOVER restart capture now waits for that marker rather than
assuming a fixed 600-tick interval. These harness timeouts do not alter runtime
simulation timing, 50fps gates or the known old barrage replay mismatch.

The separate production scenario provides publication and restoration evidence:

```sh
bash tools/agk run --profile a500 --no-build -f game/tests/native/clean_transitions.agk -o game/build/agk/a500/clean_transitions
python3.12 tools/verify-clean-transitions.py game/build/agk/a500/clean_transitions
```

Repeat for `a500-aros`. Inspect all complete captures before any intended golden
updates. The checker requires first-title music invocation in its acknowledged
vblank, identity-safe repair, unchanged complete hold frames, a static scene and
restored exterior scenery. Actual audio and strict performance remain separate
validation gates. Python negative tests reject premature readiness/publication,
missing repair, changed DMA identities and early/late music invocation.

### Full campaign fixture

```sh
python3 tools/check-campaign-native.py --strict-performance
```

The runner builds ON, uses the same scenario for `a500` and `a500-aros`, and
rebuilds OFF in `finally`, including after errors. It stops at the first
unexpected functional failure. Without `--strict-performance`, functional
success can exit zero despite an explicitly reported budget failure; strict
mode requires zero drops and peak load at most 90%. No budgets are relaxed.
`--check-only` examines existing evidence without touching the build.

Evidence is under `game/build/campaign-native/`: complete serial logs, 320×256
screenshots, full captures, audio, emulator logs and `report.json`. The report
retains all emitted 50-frame performance windows, not just selected combat
windows. Last-state context is approximate: a window can straddle phases.

## Injection and assertions

- Idle hero invulnerability except explicitly injected deaths; refill lives to
  five before each death so eight independent death cases can complete.
- Sector 1 stages 10/18: inject F pickups, then reposition them at 12/20 for
  actual collection collisions. At 14/24, clear shots and inject a one-tick
  charge latch for neutral-input release. These are explicit state injections,
  not ordinary player-input evidence. Capture the F badge and F2/F3 volleys;
  check shot count, offsets, HUD and unchanged damage one (`weaponLevel=0`).
- Stage 50: six visible enemies each receive a fixture shot with damage three.
- Stage 51: clear the resulting pickup so its foreground badge cannot obscure
  a small explosion. Ordinary-input scenarios cover actual reward collection.
- Stage 100: one collision-driven hero death per level.
- Stage 160: retire remaining enemies/trackers and set the actual quota;
  production logic enters boss arrival.
- Boss tick 80: six-damage shot; tick 120: hero death; tick 220: lower HP to six
  and inject a killing shot. Preserve `maxHp` throughout.
  The per-sector motion clock repeats boss ticks on skipped updates: hit/kill injection
  and boss/flash capture markers have explicit per-sector once-only guards.
  Flash capture requires BOSS outside preparation, an injected hit and a nonzero
  **even** pre-update `s_drawnBoss.flashTicks`, sharing the recorded coordinates.
  Fixed motion tick 82 is not a flash-phase clock. The checker requires exactly
  one white-half capture per sector, unchanged maximum HP and six damage, followed
  by the unchanged strict white-artwork pixel comparison. Runtime blinking is unchanged.
- No joystick input injection, manual phase advancement or scene acknowledgements;
  the F probe explicitly injects the release latch described above.
- All 13 scene markers require `sceneReady`; scenes dwell 150 acknowledged ticks.
- Native checks run on every death update: frame advances while simulation,
  stage, boss tick and life count remain fixed; pause lengths are 40/75 ticks.
- Every on-screen admitted hostile is checked for visibility and valid phase
  ownership; each boss must actually use channels 4, 5, 6 and 7.
- Capture metadata records pre-update BOB coordinates/effect ages. The checker
  compares opaque artwork pixels for bosses, white flashes and explosions.
  Small effects are sampled at stage 55, inside an animation frame rather than
  on its two-tick boundary; screenshots describe the completed video frame.
  Each scene's two complete captures must be pixel-identical and retain exterior
  scenery. This is not a scene-golden check or final artistic approval.

## Latest completed evidence — sector enemies and F upgrades

This historical evidence predates the 4/5 enemy clock and revised balance;
the guarded probes need a fresh native run before claiming the same coverage.

Command: `python3 tools/check-campaign-native.py --strict-performance`.

**Functional PASS on both profiles; strict performance FAIL on both.** The
current `report.json` supersedes the first-run small-effect pixel mismatch and
pending AROS result. All emitted performance windows remain in the report.

| Profile | Captures checked | Functional | Dropped frames | Peak load | Strict budget |
|---|---:|---|---:|---:|---|
| `a500` | 40 | PASS | 22 | 130% | FAIL |
| `a500-aros` | 40 | PASS | 17 | 123% | FAIL |

These are instrumented injected-fixture measurements, not a production 50fps
pass. The strict command **ran and exited with failure**, despite functional
checks passing. Runtime acceptance remains zero drops and <=90% peak; the gate
has not been relaxed and global 50fps is not achieved.
Added F probes and different sector waves prevent a like-for-like performance
comparison with the earlier 37-capture fixture; the totals alone do not establish
an improvement or regression.

Coverage on each profile:

- All scene IDs 0–12 acknowledged in order; twelve outgoing scenes passed their
  exact 150-tick dwell checks, and WIN reached its acknowledged 150-tick marker.
- Eight hero deaths paused exactly 40 ticks, four boss deaths exactly 75 ticks;
  simulation/stage/tick/life invariants passed.
- All four bosses reported channel mask 240 (`4/5/6/7`); no `qa_fail`, hidden
  hostile, allocation failure or runtime error was reported.
- All four normal boss and white-flash opaque-pixel checks passed; original
  maximum health values 108/144/192/240 were preserved.
- All four boss-death and eight hero-death opaque-pixel checks passed, together
  with all six simultaneous small-effect slots in each sector.
- All 40 captures have the expected 320×256 dimensions: 13 scenes, four each of
  bosses/flashes/boss deaths/small-effect groups, eight hero deaths, and three
  F-badge/F2/F3 captures. The F checks verify double offsets −6/+6 and triple
  offsets −8/0/+8, with normal damage still one independently of F upgrades.

Production restoration succeeded; the cache contains
`ASTRA_CAMPAIGN_PROBE:BOOL=OFF`. The runner rebuilds production in `finally` and
reports restoration failure separately. Keep probe code behind the compile-time
option and outside ordinary scenario discovery; never ship an ON-built ADF.

## Measurement scope and remaining work

Latest actual **production** A500 boot telemetry is **40,440 free chip / 48,312
total free bytes**, with a **456,792-byte** initial executable after unused
compiled art removal. This is separate from injected-fixture coverage, not a
formal minimum free-memory bound or allocation high-water proof.
See [memory ledger](rendering.md#memory-ledger).

Persisted `python3 tools/check-allocation-safety.py` passed under ASAN/UBSAN for
all 15 audio allocation positions, BOB/bitmap faults and exact preservation of
all 20 generated data arrays. The native fixture does not fault-inject OOM.
A normal startup without an allocation error is not native OOM-cleanup evidence.

The latest ordinary production suite passed **36/36
shared-golden tests**, with **36 complete captures byte-identical across profiles**.
That result is separate from this injected fixture report; see the
[final acceptance record](campaign-acceptance.md). Full ordinary native/human campaign completion,
artistic approval and strict 50fps acceptance remain open. Preserve the failed
performance gate while addressing measured overruns; do not relax assertions or
blindly update goldens to turn this report green.

## Ordinary GAMEOVER return scenario

Fresh clean-presentation production validation passed on **both profiles** with
the 477,368-byte probe-OFF build: scenario plus `verify-gameover-title.py` confirmed
150 ready ticks, reset state, preserved clocks, held-input protection and fresh
restart. All eight complete captures were inspected. The `fresh_intro` capture
now retains the whole prior title during hidden composition; the completed combat
capture waits for `combat_ready`. These results are separate from the historical
uniform-clock evidence below.

The subsequent ordinary BOB replay failure was diagnosed and corrected in the
host generator and telemetry parser, without changing gameplay. Its replanned
route, strict artwork/mask/restore/lifecycle verifier and shared-golden reruns pass
on both profiles. See [exact BOB replay commands and evidence](bob-replay-validation.md).

`game/tests/native/gameover_title.agk` runs the production build using ordinary
joystick input until all lives are lost, holds fire/right across the ready-gated
timeout and title composition, then releases and starts again. Run on each profile:

```sh
bash tools/agk run --profile a500 -f game/tests/native/gameover_title.agk -o game/build/agk/a500/gameover_title
python3 tools/verify-gameover-title.py game/build/agk/a500/gameover_title/serial.txt
```

Repeat with `a500-aros`. The serial checker requires exactly 150 ticks between
`gameover_ready` and `gameover_title`, reset state, preserved clocks, a ready
held-input title and a later deliberate SECTOR_INTRO→PLAY. Inspect all four
320×256 captures; this scenario does not create or update goldens and does not
establish global 50fps acceptance.

### GAMEOVER validation after the 4/5-clock changes

This subsection records the earlier uniform 4/5-clock revision. The later
16/17/18/20 motion rates, combat-tick firing and boss HP 108/168/216/240 require
fresh validation; this evidence does not establish acceptance of that revision.

Production `gameover_title` scenario and serial validation **PASS on a500 and
a500-aros**. The saved A500 run was rechecked after fixing wrapped telemetry;
AROS was run with `--no-build` against the same 475,180-byte production executable.
The parser assembles contiguous numeric state fragments (including `enemy_acc`),
retains the original frame line index, and rejects incomplete reports without
borrowing fields from prior states or event/music/performance records.

```sh
python3 -B -m unittest discover -s game/tests/unit -p test_gameover_title_validator.py -v
python3 -B tools/verify-gameover-title.py game/build/agk/a500/gameover_title/serial.txt
bash tools/agk run --profile a500-aros --no-build -f game/tests/native/gameover_title.agk -o game/build/agk/a500-aros/gameover_title
python3 -B tools/verify-gameover-title.py game/build/agk/a500-aros/gameover_title/serial.txt
bash tools/agk unit
bash tools/agk build
```

All nine deterministic Python tests passed; the separate C host suite passed
1/1, and the production rebuild succeeded (475,180 bytes). All eight 320×256
screenshots were visually inspected: GAMEOVER caption, returned sector-1 title,
early intro recomposition and restored combat background. `fresh_intro` is taken
only two ticks after the press and still shows title pixels during bounded
composition; it is not a completed manga-scene capture. Both validators confirm
150 ready ticks, reset state, preserved clocks, the held-input guard and subsequent
SECTOR_INTRO→PLAY. This scoped lifecycle evidence does not validate all ordinary
replays, the revised boss probes or campaign performance. Historical strict
50fps failure above remains unchanged.
