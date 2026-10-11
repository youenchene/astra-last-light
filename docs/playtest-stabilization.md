# Playtest functional stabilization

## Scope

The wrapped-state assertion correction and focused functional validation pass on
`a500` and `a500-aros`, using the 452,076-byte production executable. This pass
changes test infrastructure and eight inspected shared TITLE references; it does
not change gameplay, rendering, the installed AGK kit or performance thresholds.

`tools/verify-sector-state.py` reuses `frame_states()` from
`verify-gameover-title.py`. It joins only contiguous known state fragments and
requires phase, level, scene, readiness and preparation in the **same record**.
It also requires the subsequent ready six-member PLAY formation. `campaign_waves`
retains its zero opening stage/sim clocks and positive hostile-barrage assertion.
The project-local `agk-launch.py` invokes the companion automatically for
`sector2`, `sector3`, `sector4` and `campaign_waves`, in both `run` and `test`.
The scenarios retain their pixel, sound, music and native-error checks.

Zero `stage`/`sim` during a fresh opening is intentional: `logicUpdate` services
hero movement and player projectiles in SECTOR_INTRO, but advances combat clocks
and the wave timer only in PLAY/BOSS. This avoids consuming the first formation's
delay during the panel. This behavior was investigated and preserved, not altered
to satisfy an assertion. Existing live-opening host and native tests verify it.

## Results

- C host rules: **1/1 PASS**.
- Python: **47 tests PASS** (39 existing plus eight sector-state regressions).
  Negative cases cover wrong scene, cross-record readiness/scene, missing fields,
  interrupted fragments, invalid ordering, changed opening clocks and no barrage.
- Build: **PASS**, 452,076-byte executable.
- Both profiles: `sector2`, `sector3`, `sector4`, `campaign_waves`, `title_sectors`,
  `gameover_title`, `bob_restore`, `clean_transitions`, `live_opening`, `boot`,
  and `skip` scenarios **PASS**.
- Source pixels: all **12,288 original plate pixels per title**, four distinct
  titles and both wraps pass on both profiles. All **15,360 Nebula band pixels**
  match their source derivative, with phases `[30,29]` and unchanged connectivity
  counts (544 cleared / 158 retained shadow pixels).
- GAMEOVER verifier: exact 150-ready-tick dwell, clock preservation, held-input
  guard, reset and fresh restart pass on both profiles.
- BOB verifier: **164 opaque + 92 transparent pixels**, the full **768-pixel**
  restore region, real six-kill drop/collection, 150-tick scene dwell and 40-tick
  death pause pass on both profiles. Combat-ready frame is now 760; the first
  hero death remains combat stage 167.
- Transition verifier: atomic complete-frame holds, bitmap/copper repair identity,
  publication acknowledgement and music-controller invocation alignment pass.
- Ordinary-input opening verifier: visible nine-pixel hero movement, exact moving
  shot artwork, intact window and per-bitmap BOB restoration pass.

All **96 complete 320×256 captures** from these fresh runs were visually inspected
in uncropped, native-resolution review sheets beside their source captures under
`game/build/stabilization/{profile}/{scenario}/review-*.png`. These are functional
and source-pixel checks, not final artistic approval or a full campaign clear.

## Golden scope

After inspection and source checks, only these eight shared references changed:

- `game/tests/golden/boot/title.png`
- `game/tests/golden/skip/title_after_skip.png`
- The six files under `game/tests/golden/title_sectors/`

ACE/Micrix captures matched their existing references. No profile-specific
references or screenshot masks were introduced. The update run passed **3/3**;
fresh no-update runs passed **6/6** across both profiles. Ordinary BOB checks above
use strict source pixels and lifecycle evidence; this pass does not claim a full
ordinary-suite shared-golden rerun, or refresh campaign/combat reference images.

## Commands

```sh
bash tools/agk unit
python3 -B -m unittest discover -s game/tests/unit -p 'test_*.py' -v
bash tools/agk build
```

For each profile `a500` and `a500-aros`, run ordinary scenarios using:

```sh
bash tools/agk run --profile "$profile" --no-build -f "game/tests/$scenario.agk" -o "game/build/stabilization/$profile/$scenario"
```

Use `game/tests/native/$scenario.agk` for `gameover_title`, `clean_transitions`
and `live_opening`. Companion checks:

```sh
python3.12 tools/verify-sector-presentation.py --base game/build/stabilization
python3 tools/verify-gameover-title.py "game/build/stabilization/$profile/gameover_title/serial.txt"
python3.12 tools/verify-bob-restoration.py --drop "game/build/stabilization/$profile/bob_restore/bonus_drop.screen.png" --restored "game/build/stabilization/$profile/bob_restore/bob_restored.screen.png" --lifecycle-serial "game/build/stabilization/$profile/bob_restore/serial.txt"
python3.12 tools/verify-clean-transitions.py "game/build/stabilization/$profile/clean_transitions"
python3.12 tools/verify-live-opening.py "game/build/stabilization/$profile/live_opening"
bash tools/agk test --no-build --profile a500 --only boot --only skip --only title_sectors --update
bash tools/agk test --no-build --profile a500 --profile a500-aros --only boot --only skip --only title_sectors
```

## Remaining boundary

No new functional/test/build failure occurred in this focused stabilization pass.
Full ordinary-suite golden acceptance remains outside the scoped result above.
The prior injected campaign functional pass covers all 13 scenes, but its complete
image-review backlog is separate from these 96 inspected production captures.

Performance optimization is deferred. The previous strict fixture remains failed:
**A500 21 drops / 127% peak; AROS 18 drops / 123% peak**. It was not rerun here.
Zero drops, <=90% peak and the 20 ms runtime budget are unchanged. This work does
not establish 50fps acceptance. No commit, GUI action or cleanup was performed.
