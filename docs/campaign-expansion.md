# Expanded Astra campaign

## Status

**All 11 functional campaign features are implemented; performance acceptance is BLOCKED.**
This status describes the delivered source and latest parent-reported evidence
for sector enemies, release-only fire, F upgrades and clear Veil Nebula bands,
not completion of every task in the working plan.

| Delivered feature | Current behavior |
|---|---|
| Formations | Six homogeneous members, including six asteroids; exact quotas 18/21/24/24; boss entry waits for final retirement |
| Bosses | Four distinct 64×48 masked BOBs; HP 108/144/192/240 |
| Damage feedback | Six-tick white boss hit flash without flash invulnerability |
| Hostiles | Pool of 32; channels 6/7 in PLAY, 4–7 in BOSS; palette-safe 25–27 versus 29–31 inks |
| Explosions | Eight slots: six 16×16 small effects lasting 16 ticks, reserved 32×32 hero/40 ticks and 64×48 boss/75 ticks |
| Death phases | Retained effect origins; simulation pauses while video/effect age and audio continue; death phases cannot be skipped |
| Presentations | 13 scene IDs: entry/arrival/defeat per sector, then victory; 150 acknowledged display ticks, release-then-press skip after 25; WIN waits for a fresh press |
| Manga | Five distinct original local 160×96 panels; 13 narrative/frame treatments with scanner and helmet/salute glints |
| Music | Four original sector arrangements integrated after the licensed intros; title theme preserved; 13,624 new PCM bytes; mute continuity |
| Atomic double-buffer publication | Two 320×256×4bpp buffers with per-bitmap histories and incremental composition; pixels and streams published together |
| Hardware-scrolled decor | 57-command copper bands; old 144 KiB phase bank removed |

The new art is locally authored by `tools/make-campaign-art.py`, entirely offline,
not Retro Diffusion output. Original RD masters, title source plates, licensed
ACE/Micrix intros and exact ACE PCM remain preserved. One common Graveyard
**title-only** background saves 18,432 chip bytes; gameplay decor and manga stay
sector-specific, with Veil Nebula's gameplay decor disabled. See [rendering and memory](rendering.md) and
[campaign-art provenance](../game/art/CAMPAIGN-ART.md). Older integration-handoff
notes in the art/music records describe their original delivery, not current status.

### Evidence and open acceptance gates

- Latest ordinary production suite: **36/36 shared-golden tests PASS**;
  all **36 complete captures byte-identical across profiles**.
- [Non-shipping injected native fixture](campaign-native-fixture.md): both
  profiles **functional PASS**, all 40 captures each, all 13 scenes, F badge/F2/F3, four bosses
  and flashes, six simultaneous small effects, eight hero deaths and four boss
  deaths with pause/channel invariants. It does not prove an ordinary full-quota clear.
- Latest strict fixture performance: **A500 22 drops / 130% peak; AROS 17 drops /
  123% peak — FAIL**. The strict command ran and exited with failure. Added F
  probes and different waves prevent like-for-like comparison with older results.
  Zero drops and <=90% peak remain required. The 20 ms runtime
  budget is unchanged; the project-local 6000-frame cold-load allowance only
  accommodates AROS loading the larger executable.
- Latest actual production A500 boot: **40,440 free chip / 48,312 total free bytes**;
  initial executable **456,792 bytes**, with unused compiled art sections removed.
  This startup reading is not a formal worst-case memory bound.
- Persisted `tools/check-allocation-safety.py` **PASS** under ASAN/UBSAN for all
  15 audio allocation positions, BOB/bitmap faults and exact preservation of all
  20 generated data arrays. Native allocation failure has not been fault-injected.
- Full ordinary native campaign completion, real Amiga validation, final asset
  artistic approval and strict worst-case 50fps acceptance remain open.

See [final acceptance commands, ordinary timing and evidence](campaign-acceptance.md).
The four sector arrangements now run at **96/88/104/112 BPM**, with sixteen-bar
loops of **40.00/43.64/36.92/34.29 seconds**. This supports the slower mysterious
artistic direction; no measured performance benefit is established and the tempo
change has not closed the budget.

## Delivered design

1. Six enemies per homogeneous formation; six asteroids on asteroid waves.
2. Triple the reference number of waves before each boss, one formation at a time.
3. Larger, tougher BOB bosses. Freeze decor/star scrolling for boss fights, and
   lend channels4/5 to hostile fire while preserving the hero palette.
4. Flash the boss when hit. Animate deaths for enemies, asteroids, bosses and hero.
5. Boss and hero death phases pause gameplay, but continue50Hz effects/audio.
6. Different music in each sector, retaining the mysterious, strange synthwave tone.
7. Manga-style pilot/vessel presentations at sector entry, boss arrival, boss defeat
   and final victory. Presentation assets are new work, not existing portraits.
8. Acceptance still requires real PAL50fps, memory and visual correctness on the
   baseline A500; functional implementation alone does not satisfy this gate.

## Sector cycles and player fire

Each row repeats by zero-based `wave % 5`; each wave contains six homogeneous
members. Every fifth wave is six passive asteroids. Quotas remain 18/21/24/24.

| Displayed sector (zero-based level) | Repeating five-wave cycle |
|---|---|
| 1 — Orbital Graveyard (0) | SCOUT → WEAVER → GUNNER → DART → ASTEROID |
| 2 — Veil Nebula (1) | WEAVER → DART → WEAVER → GUNNER → ASTEROID |
| 3 — Imperial Foundry (2) | GUNNER → SCOUT → GUNNER → DART → ASTEROID |
| 4 — Stellar Citadel (3) | DART → GUNNER → WEAVER → DART → ASTEROID |

`sector_enemies.txt` supplies 24 16×16 frames in `level * 6 + kind` order.
Each six-frame group includes an unused legacy-boss slot; campaign bosses still
use their separate 64×48 art. Sector 1 preserves the original six master frames;
later sectors have offline-authored derivatives. Original PNGs and the fourteen
`actors16.txt` frames remain preserved. See [provenance](../game/art/SECTOR-ENEMIES.md).

Veil Nebula suppresses top/bottom decor in both bitmap composition and runtime
copper fetch switches. Its band background is ink 0 (`#102`); HUD and play/collision
bounds are unchanged. The original crystal PNG and decor strip remain preserved.

Holding fire only charges, with one charge-ready event at 50 combat ticks.
Release after 1–49 ticks requests a normal volley; release at full charge emits
one centered 16×10, vx4, six-damage lance. Neutral input at charge zero emits
nothing. Normal volleys are rate-limited to eight ticks; an early release is
discarded rather than queued. Scene/death transitions cancel held charge.

Five bonus kinds occupy the unchanged four pickup slots. Enum/storage order is
P/S/R/L/F (`BONUS_FIRE=4`); the explicit drop cycle is **P → F → S → R → L**.
F raises `shotLevel` 0–2 independently of P's `weaponLevel` damage upgrade:

| HUD | Normal volley | Vertical offsets from muzzle center | Damage per shot |
|---|---:|---|---|
| F1 | 1 | 0 | 1 + weaponLevel |
| F2 | 2 | −6, +6 | 1 + weaponLevel |
| F3 | 3 | −8, 0, +8 | 1 + weaponLevel |

All normal shots travel at vx6/vy0 and fit the hero's vertical body bounds.
The twelve-shot pool is preflighted for the entire volley: insufficient space
means no partial pattern and no firing event/sound. F persists across sectors,
falls one level on death, and resets to zero on a new game, like damage/speed
upgrades. W remains the damage counter; the footer adds F1–F3 and moves the stage
caption to x104. Charged fire is independent of both upgrades.

## Wave-count reference

The original implementation starts bosses after elapsed time, so there is no one
wave count shared by all player strategies. The frozen reference uses a stationary,
non-firing pilot, with invulnerability set only by the host fixture. It does not
alter enemy movement, spawn cadence or retirement. All spawns before the old boss
cutoff count, even if the final formation was cut short by that timer.

| Sector | Old duration (ticks) | Measured reference waves | Implemented exact quota |
|---|---:|---:|---:|
| Orbital Graveyard | 1800 | 6 | 18 |
| Veil Nebula | 2000 | 7 | 21 |
| Imperial Foundry | 2200 | 8 | 24 |
| Stellar Citadel | 2400 | 8 | 24 |

Evidence and original source hashes: `game/tests/fixtures/campaign-wave-reference.json`.
Probe source: `tools/probe-wave-reference.c`. Run it against the original hashed
logic, not after quota-based progression replaces the timer.

The new boss gate waits until the quota has spawned **and the final
formation has retired**. Killing enemies sooner shortens the sector, not its wave
count. Escaped waves count toward progression but still cannot award clear bonuses.

## Delivery and acceptance tracking

- **Implemented wave milestone:** agent constraints, frozen reference, six lanes, exact quotas,
  rule tests and regenerated no-cheat native replays.
- **Implemented lifecycle milestone:** explicit arrival/death/presentation phases, retained
  effect positions and durations, paused-simulation tests.
- **Implemented boss/effects milestone:** large BOB geometry, palette-safe
  channel handover, hit flashes and bounded explosion pools.
- **Implemented presentation/audio milestone:** original pilot/boss assets and animation,
  four arrangements without uncontrolled PCM duplication, mute-state preservation.
- **Acceptance BLOCKED:** shared visual regressions and measured worst-case50fps gates
  across sectors, bosses, overlapping effects and transitions. No25fps fallback.

Dependency plan: `.tmp/tasks/astra-campaign/task.json`. The plan is working
coordination data; source/tests and this status document define delivered behavior.
Do not mark all 25 tasks complete from the functional fixture result. Preserve
separate evidence for ordinary play, injected coverage, memory and strict performance.
Paid asset generation needs a verified price and spending ceiling before requests.
