# Non-shipping native campaign fixture

This explicitly injected-state fixture is **not an ordinary campaign clear**.
`ASTRA_CAMPAIGN_PROBE` defaults OFF. Only the ON build compiles
`game/tests/native/campaign_probe.c`; the parent's guarded main-loop hooks are
the only integration points. The scenario is below `tests/native/`, outside
top-level test autodiscovery.

## Run

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
  Scene captures receive dimension/presence checks, not golden checks or artistic approval.

## Latest completed evidence — sector enemies and F upgrades

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
