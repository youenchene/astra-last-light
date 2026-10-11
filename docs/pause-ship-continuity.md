# P pause, persistent narrative ship and 112×64 panels

## Status — implementation delivered; campaign validation stopped

The production replay passes on **a500 and a500-aros**, including source-pixel
checks, P/M independence, frozen clocks, fire cancellation, first-published
opening visibility and window-close continuity. Host C rules pass and **76 Python
tests pass**. The new injected A500 campaign fails in startup display/render
creation. Work stopped at that failure; no corrective runtime changes, further
builds/tests, golden updates, GUI, commits, cleanup or paid calls followed it.
The runner's mandatory `finally` production rebuild succeeded. Both
`ASTRA_CAMPAIGN_PROBE` and `ASTRA_PRESENTATION_TIMING` are verified **OFF** in
`game/build/CMakeCache.txt`.

## Implemented behavior

- **P** toggles manual pause separately from **M** audio mute and P damage pickups.
  TITLE, GAMEOVER and licensed intros consume/ignore P. Live openings, PLAY/BOSS,
  blocking stories and both death phases accept it. Restart clears pause state.
- Pause freezes movement, projectile pools, collisions, cooldowns, charge, wave/
  quiet-boss clocks, enemy motion clocks and story/death dwell. Video `frame`,
  effect age, boss flash animation, rendering and the music controller continue.
  Expired death effects do not advance the death phase or resurrect the hero.
- Toggling cancels charge and disarms fire until a release **after resume**.
  Neither a held pause-era fire nor its release fires a delayed shot or skips a
  story. Direction becomes live again on resume; it is not queued.
- A per-bitmap dirty **PAUSE** label replaces LANCE at `(8,18)`; resume restores
  the normal label. It uses existing font/label assets and only the unpublished
  bitmap. During hidden preparation it appears on the next complete publication,
  rather than modifying a held visible frame or forcing a full recomposition.
- Hero channels 0–3 use first-**target** completeness independently of hostile
  admission. Both-buffer readiness/publication still gates gameplay. The first
  visible opening contains the ship, and each completed closing target retains it.
  Entry invulnerability keeps its damage protection without blinking; actual
  shield-hit/respawn feedback still blinks during combat.
- BOSS_INTRO, BOSS_DYING, CLEAR and WIN show a stationary ship, with animated
  engine pixels. HERO_DYING and GAMEOVER do not show it.
- **Opaque-window policy:** opening flight is bounded to x≤120 so all 32 ship
  pixels remain left of the window. In blocking stories, an overlapping ship is
  displayed at x120 without changing its frozen logical position. Its y is kept.
  This is an explicit visual relocation for overlap, not clipping or whole-ship
  disappearance. Boss death without a window retains the actual position.
- Five panels are offline nearest-neighbor derivatives of the preserved 160×96
  masters, now **112×64** (+16.7% width / +14.3% height). Window remains
  `(152,56)`–`(312,192)`. Image starts `(176,72)`, framed by
  `(172,68)`–`(292,140)`. Existing 4×6 font is retained; captions start y144,
  replies y164. All 13 captions/replies and meaningful boss/defeat/victory titles
  remain. Opening titles and continuation instructions remain omitted.

## Validation performed

```sh
python3.12 tools/make-compact-manga.py
python3.12 tools/make-presentation.py
bash tools/agk unit
python3.12 -m unittest discover -s game/tests/unit -p 'test_*.py'
bash tools/agk build
bash tools/agk run --profile a500 --no-build -f game/tests/native/pause_continuity.agk -o game/build/pause-continuity-a500
python3.12 tools/verify-pause-continuity.py game/build/pause-continuity-a500
bash tools/agk run --profile a500-aros --no-build -f game/tests/native/pause_continuity.agk -o game/build/pause-continuity-aros
python3.12 tools/verify-pause-continuity.py game/build/pause-continuity-aros
python3.12 tools/check-campaign-native.py --out game/build/pause-ship-campaign
```

All commands before the last passed. The last failed on A500 native startup and
restored OFF. Its `report.json` preserves the nonzero native command, failed
profile evidence and `production_restored: true`; the runner returns 1 for this
incomplete, failed campaign. A successful OFF rebuild is not a campaign pass.

The C tests compare the whole paused simulation state in all eight supported
phases (allowing only frame/input-edge/effect changes), exercise cancellation and
fresh release-fire, blocking phases, opening lane/closing visibility, damage
blinking and no death resurrection. The independent Python painter checks all 13
static card layers and eight HUD variants, per-step write bounds and ≤64 decode
operations. New checks derive every enlarged panel pixel from its master and
verify all narrative wraps fit, plus explicit meaningful headings. The campaign
validator now requires a source-exact stationary hero in every story.

The production native replay captures nine full screens/profile. Its companion
checker requires source-exact hero pixels in all nine, exact PAUSE/LANCE pixels,
frozen paused backgrounds, first-visible/both-ready publication order, frozen
preparation/pause clocks and no delayed shots. Audio assertions establish sound
during pause and silence after M, then unmute and resume. All nine A500 full
320×256 captures were visually inspected. No goldens were changed. The all-13
native card validator was updated but could not run on a fresh campaign.

## Memory and scoped timing

| Measurement | Previous accepted production | This production |
|---|---:|---:|
| Executable bytes | 476,972 | 481,612 (+4,640) |
| Generated static-row payload | 20,234 | 20,234 |
| Manga CHIP bitmap payload | 13,440 | 17,920 (+4,480) |
| A500 startup free CHIP / total | 46,696 / 51,504 | 42,208 / 42,456 |
| AROS startup free CHIP / total | 138,808 / 1,362,240 | 134,328 / 1,353,192 |
| New production replay drops / peak | Different scenario | A500 0 / 90%; AROS 0 / 87% |

New scenario performance covers intro/title, opening preparation, manual pause
with sound/mute, closing, and early PLAY; it does not cover a crowded campaign.
Static decoding stays **320 output bytes / 64 operations**, ≤4 card or ≤2 HUD
rows per call. Manga copying stays ≤8 rows/call, now eight calls rather than
seven per bitmap. Opening hidden work is 123 held iterations/bitmap (previous
122); first visible is 124 vblanks from transition and both ready 248 (4.96 s).
Closing retains 16 held iterations/bitmap and 17 vblanks between acknowledgements.
There are still exactly two framebuffers and no new runtime allocation site.
The larger existing manga allocation and compiled source both consume memory;
startup free totals are not peak/largest-block bounds or loader-headroom proofs.

## New failure — exact established boundary and proposed next step

Command: the final campaign command above. Probe-ON executable **488,796 bytes**.
`game/build/pause-ship-campaign/a500/serial.txt` contains only:

```text
AGK boot astra
AGK allocation failure
```

Native harness error:

```text
waitserial: timeout waiting for 'AGK ready'
line 114: expected serial to match /AGK qa_NON_SHIPPING_injected_fixture/
```

The unchanged A500_OCS_1MB profile and **6000-frame** cold allowance are confirmed
in `a500/emulator.log`. Unlike the historical AmigaDOS error103, the loader entered
`genericCreate()`. The exact emitting branch is `main.c`'s combined
`!createDisplay() || !renderCreate(...)` check, **before audio allocation,
intro creation, free-memory telemetry and gameplay**. Therefore the missing perf
windows are downstream missing evidence, not a measured timing regression.

The trace cannot distinguish the failing child allocation/asset check. The
leading hypothesis is probe-ON startup peak/contiguous-CHIP pressure from the
larger resident executable plus larger strip; the successful production boot
does not establish that the probe build fits. No exact failed allocation size or
largest-free block is claimed.

**Proposed correction, not applied:** first add minimal startup-only stage/error
markers and total/largest-free CHIP readings around the existing display/render
constructors, then reproduce against the preserved ON artifact/profile. Once
the failed allocation is identified, reduce only the relevant startup peak or
resident manga duplication (for example, evaluate a single-panel CHIP staging
asset with bounded offline-row transfers if the strip is implicated). Preserve
112×64 content, two buffers, the decode budgets, sound and original hardware.
Do not extend the timeout, relax budgets or start broad optimization.

Failed ON binary/ADF and hashes remain in `pause-ship-campaign/probe-on/`.
The AROS injected campaign was not attempted after the A500 failure.

## Unfinished / clarification

- Diagnose and approve a fix for the new probe-ON startup failure.
- Fresh all-13 native story pixels, boss/death/CLEAR/WIN visual continuity,
  campaign/performance, BOB restoration regressions and complete AROS image review.
- Fresh allocation-safety/audio provenance checks after the enlarged allocation;
  production P/M audio behavior has passed, but this is a separate gate.
- More native manual-pause coverage in crowded BOSS and death phases; host rules
  cover these phases, the production native replay covers opening and early PLAY.
- Full-campaign 50fps, ordinary full-quota clear, native OOM injection and formal
  worst-case memory remain unproven. Previous global performance blockers stand.
- Clarify title instruction icons, whether “RetroFusion” means Retro Diffusion,
  **15 candidates** (five shared panels × three) versus **39** (13 beats × three),
  provider/pricing and an explicit spending ceiling. Icons and paid art untouched.
