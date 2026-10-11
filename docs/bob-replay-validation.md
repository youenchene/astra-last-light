# Ordinary BOB replay correction and verification

## Scope and result

The clean-presentation production build (477,368-byte executable, campaign probe
OFF) passes the regenerated ordinary-input `bob_restore`, `bonus` and `asteroids`
scenarios on **a500 and a500-aros**. The final shared-golden run passes **6/6**.
The strict BOB artwork/mask, full aligned restoration ROI and lifecycle checks
also pass on both profiles without a pixel-position adjustment. No gameplay,
balance, renderer, allocation or audio code was changed for this correction.

This is scoped functional verification, not global PAL 50fps acceptance. The
existing injected campaign budget remains failed: A500 16 drops / 123% peak,
AROS 11 drops / 120% peak. Zero drops and <=90% remain required. The historical
barrage mismatch and a complete ordinary campaign clear remain open.

## Diagnosis

The old replay expected first kill 63, death stage 186 and a six-kill drop at
stage 235. Native execution instead killed at stages 65, 75, 132, 164 and 181,
died at stage 237, and left one enemy alive: no bonus existed to restore.

An open-loop host replay against **current** `logic.c` reproduced the five-kill
failure. With the actual main-loop ready timing included, all five kill stages
and the death stage matched native exactly. Main emits `combat_ready` before
logic; `wait-serial` resumes at the next AGK tick, after that acknowledgement
iteration has consumed one neutral update. The planner now models this update
explicitly as `ready_updates=1`; no input wait or fitted coordinate offset is added.
The primary failure was stale inputs after balance changes, with an additional
planner mismatch at the first input boundary. It was not evidence of broken
BOB background restoration.

`tools/plan-bonus-flight.c` was dry-run before writing. Its regenerated route
uses only ordinary joystick input and public host lifecycle APIs, with no native
state injection. It proves six first-wave kills, bonus creation, collection,
three clear host states for the full aligned restore region, and six live
asteroids later in the route. `--check` replays and verifies all five generated
input files and capture ticks against the current plan.

| Milestone | New scenario-input tick | Native stage |
|---|---:|---:|
| First kill | 58 | 59 |
| First hero death | 166 | 167 |
| Sixth kill / bonus drop | 252 | 213 |
| Drop capture | 270 | — |
| Pickup | 276 | 237 |
| Upgrade capture | 278 | — |
| Restoration capture | 298 | — |
| Six live asteroids | 1361 | — |

The scenario-input clock excludes the one ready update and includes death-pause
ticks. The stage clock advances only during combat. Screenshots show the last
finished display frame, one publication behind current serial state; rendering
itself now happens **after** logic. The generator comment and death-capture ages
were corrected accordingly.

## Parser and pixel checks

`verify-bob-restoration.py` reuses the tested complete-frame parser from
`verify-gameover-title.py`, including current `enemy_acc` continuation lines. It
uses the acknowledged scene's actual `pf` to count exactly 150 display ticks;
the old unconditional `+1` was wrong for the new age-zero acknowledgement.

The verifier checks the ready boundary, first-kill timing, genuine six-kill drop,
collection and the unmodified 40-tick death pause. Eight new Python regressions
cover wrapped/truncated records, old and new acknowledgement ages, missing
drop/pickup events, timing drift and incorrect pause duration.

Both profiles pass **164 opaque artwork pixels + 92 transparent mask pixels**
at `(145,60)` and all **768 background pixels** in `[128,60,176,76)`. The region
is the union of ACE's aligned two-word save rectangles over the pickup lifetime,
including its spill word. It is not a cropped or weakened artwork assertion.

## Commands and evidence

From the repository root:

```sh
cc -std=c99 -Wall -Wextra -Werror -Igame/src tools/plan-bonus-flight.c game/src/logic.c -o game/build/plan-bonus-flight-current
game/build/plan-bonus-flight-current
game/build/plan-bonus-flight-current --write
game/build/plan-bonus-flight-current --check
bash tools/agk unit
python3 -B -m unittest discover -s game/tests/unit -p 'test_*.py' -v
bash tools/agk build
```

Host rules passed 1/1; Python tests passed 33; build passed. The generator writes
only `game/tests/{bonus,asteroids,bob_restore}.agk`,
`game/demo/{showcase,asteroids}.agk`, and `game/tests/bonus-flight.json`.

For each `profile` in `a500 a500-aros`:

```sh
bash tools/agk run --profile "$profile" --no-build -f game/tests/bob_restore.agk -o "game/build/agk/$profile/bob_restore-replanned"
python3.12 tools/verify-bob-restoration.py --drop "game/build/agk/$profile/bob_restore-replanned/bonus_drop.screen.png" --restored "game/build/agk/$profile/bob_restore-replanned/bob_restored.screen.png" --lifecycle-serial "game/build/agk/$profile/bob_restore-replanned/serial.txt"
```

`bonus` and `asteroids` were also run with the same flags to their respective
`*-replanned` output folders on both profiles. All **28 complete 320×256 captures**
were inspected in native-resolution, uncropped `review-1.png` sheets in those
six folders. Only the 14 shared references belonging to those three regenerated
scenarios were updated after inspection; their new trajectories explain the
changed screenshots. Then:

```sh
bash tools/agk test --no-build --profile a500 --only bob_restore --only bonus --only asteroids --update
bash tools/agk test --no-build --profile a500 --profile a500-aros --only bob_restore --only bonus --only asteroids
```

Results: update run 3/3; final no-update run **6/6**, all shared references match.
The two demo routes receive host replay verification and share the asteroid
scenario's generated input; they were not separately launched in a GUI.

Preserved failure/source evidence: `game/build/bob-replay-before-fix.tar`.
Preserved old references: `game/build/bob-replay-goldens-before-fix.tar`.
The diagnostic host replay source remains explicitly under
`.tmp/context/astra-clean-transitions/replay_bob_route.c`. No cleanup or deletion
was performed. The parent owns the subsequent interactive playtest.
