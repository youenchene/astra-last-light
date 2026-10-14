# End-wave preparation investigation (2026-10-14)

## Result: preparation burst reduced, global 50fps acceptance still open

The hypothesis is partly confirmed. A new formation changes its sprite image,
invalidating all six slots in each attached channel's two physical DMA buffers.
Those cache misses overlap with spawning, the previous wave's explosion/pickup,
score updates and state reporting. There is no full-screen next-wave composition:
ordinary waves stay in PLAY with the same prepared world.

`render_enemies.c` now prepares **one unused attached slot pair per quiet frame**
for the next wave. It writes only pixel rows behind the back stream's terminator;
front buffers, control words and visible enemies are untouched. Event frames,
death/boss phases and the final quota do not perform speculative preparation.
Rapid kills still use the normal image-cache fallback, preserving exact output.
The renderer and spawning share the existing cycle table rather than duplicating
sector rules. No wave timing, entity pool, art, audio or allocation changes.

## Measured production replay

`bob_restore.agk`, with `tools/perf_boundary.py`'s F8 completion appended, exercises
real six-member kills, hero death, final retirement, next-wave spawn and pickup.
All seven diagnostic/probe flags are OFF. Audio remains enabled. Complete-window
accounting covers **1,228 iterations**, including the final **28-frame window**.

| Build/profile | Missed vblanks | Peak load | Strict <=90% verdict |
|---|---:|---:|---|
| Baseline A500 | 0 | 98% | FAIL |
| Revised A500 | 0 | 96% | FAIL |
| Revised A500-AROS | 0 | 90% | PASS for this replay only |

The remaining A500 peak is the **final kill/bonus-drop frame**, not next-wave
spawning. A temporary peak-iteration probe identified iteration1180 / logic
frame787. It has been removed; acceptance numbers above are diagnostics-OFF.
Detailed AROS traces identified the enemy-image reload burst (39–44 scanlines
versus14 on the sampled ordinary combat frame); these instrumented values are
attribution evidence, not production timings or baseline A500 acceptance.
Detailed A500 profiler builds failed ACE intro audio allocation and are rejected.

Raw evidence is under `game/build/wave-baseline-a500/`, `wave-accepted-a500/`,
`wave-accepted-aros/`, `wave-trace-aros/` and `wave-peak-a500/`.
`game/build/wave-performance.json` retains complete-window verdicts and memory.

## Validation and limits

- C logic tests PASS; Python discovery172/172 PASS. The final preparation-loop
  revision also passes its focused ASAN/UBSAN test independently.
- The new production-writer regression covers all four sectors/five cycle entries,
  alternating physical buffers, bounded copying, unchanged front streams,
  visible pixels/termination, rapid kills, final quotas and death/boss ownership.
  With warmed spare slots, spawn reloads fall from12 images to at most2 per buffer.
- Both-profile ordinary BOB and natural six-ship/barrage replays PASS, with sound.
  All five complete BOB captures on each profile match the baseline byte-for-byte.
  The independent badge/restoration checker passes164 opaque,92 transparent and
  all768 restored pixels. The revised bonus capture was visually inspected.
- Native transition replays PASS, but their separate strict pixel checker FAILS
  on both profiles:2,560 intro-hold pixels change. Preparation cannot run in intro;
  this remains visible and unresolved. No checker/golden relaxation was made.
- Actual68000 `render_enemies` object has no32-bit multiply/divide helpers after
  removing an initially generated `___mulsi3`. Audit: `wave-accepted-68000.txt`.
- Final executable545,852 bytes. Actual A500 startup free CHIP/total:3,792/3,792
  bytes; AROS150,008/1,314,528. No new allocation, but code residency still costs
  memory. These are startup readings, not a formal worst-case bound.

Full campaign/worst-case50fps, especially coincident final kills/bonuses/shots,
is **not achieved or claimed**. No injected full campaign was run in this scope.
