# Expanded Astra campaign

## Status

### Current larger selected images / dedicated WIN — functional scope passed

Ordinary selected manga is **140×84**, with a dedicated **320×192** ending and
no WIN HUD/world/sprites. Both-profile source checks cover all 13 mappings,
held-fire/restart/ESC, ordinary scene dwell and death pauses. Production and
probe-ON startup now fit unchanged A500 hardware after the loader-hunk correction;
production OFF is restored. See [current geometry, memory and complete evidence](selected-rd-story-images.md).
The known pause-sampling harness issue is corrected without relaxing assertions.
Performance optimization is deferred until the parent commit; global 50fps
acceptance remains blocked. The following revision notes are historical.

### Latest pause/ship/panel revision — native campaign blocked

P pause, narrative ship visibility and 112×64 offline panels are implemented.
Host checks and the production opening/PLAY pause replay pass on both profiles.
The new injected A500 build fails during display/render startup; production OFF
was restored and work stopped. [Exact evidence, overlap policy and remaining
validation](pause-ship-continuity.md) supersede the older layout/status below.

### Static presentation optimization — scoped validation passed

All 13 cards and shared HUD layers now use offline compressed rows. The latest
both-profile functional campaign and full-card source pixels pass; production
probe-OFF is restored. Opening preparation is 4.92 s versus 6.68 s, with zero
drops in its focused latency scenario. Global performance remains blocked:
the injected campaign reports 19/12 drops and 125% peak. See
[complete evidence and preserved failed candidates](precomputed-presentation.md).

### Latest playtest correction — focused functional validation passed

Fresh both-profile production checks and their exact limits are recorded in
[playtest stabilization](playtest-stabilization.md). Performance work is deferred.

Boss HP is now **216/336/432/480**; ordinary enemy HP is unchanged. After the
quota's final kill/escape, PLAY continues through both projectile pools draining
and **50 full empty combat ticks**. The retirement/last-projectile tick does not
count. Any new player shot resets the interval, even if it leaves immediately.
Preparation and hero death pause the gate; lethal collisions take precedence.

Sector-opening windows now permit hero movement and release fire after the
two-buffer ready acknowledgement, while wave spawning and combat clocks wait
until the window closes. Later stories stay blocking. All 13 beats retain their
text in compact top-right windows with offline panel derivatives; TITLE alone
uses the centered layout. See the current correction in [rendering](rendering.md).
Historical evidence and behavior descriptions below predate this correction;
full campaign visual, worst-case memory and performance acceptance remain pending.

**All 11 functional campaign features are implemented; performance acceptance is BLOCKED.**
This status describes the delivered source and latest parent-reported evidence
for sector enemies, release-only fire and F upgrades, plus freshly verified
sector-specific titles and restored Veil Nebula crystal bands,
not completion of every task in the working plan.

| Delivered feature | Current behavior |
|---|---|
| Formations | Six homogeneous members, including six asteroids; exact quotas 18/21/24/27; boss entry waits for final retirement |
| Bosses | Four distinct 64×48 masked BOBs; HP 108/168/216/240; only sectors 2/3 received the latest HP increase |
| Damage feedback | Six-tick white boss hit flash without flash invulnerability |
| Hostiles | Pool of 32; channels 6/7 in PLAY, 4–7 in BOSS; palette-safe 25–27 versus 29–31 inks |
| Explosions | Eight slots: six 16×16 small effects lasting 16 ticks, reserved 32×32 hero/40 ticks and 64×48 boss/75 ticks |
| Death phases | Retained effect origins; simulation pauses while video/effect age and audio continue; death phases cannot be skipped |
| Presentations | 13 scene IDs: entry/arrival/defeat per sector, then victory; 150 acknowledged display ticks, release-then-press skip after 25; WIN waits for a fresh press |
| Manga | Five distinct original local 160×96 panels; 13 static image/text windows over frozen sector gameplay scenery; all 13 static pairs pass on both native profiles |
| Music | Four original sector arrangements integrated after the licensed intros; title theme preserved; 13,624 new PCM bytes; mute continuity |
| Atomic double-buffer publication | Two 320×256×4bpp buffers; retain complete visible frame during hidden composition, cut to first complete target, repair second target before simulation resumes; focused publication/pixel checks pass on both profiles |
| Hardware-scrolled decor | 57-command copper bands; old 144 KiB phase bank removed |

The new art is locally authored by `tools/make-campaign-art.py`, entirely offline,
not Retro Diffusion output. Original RD masters, title source plates, licensed
ACE/Micrix intros and exact ACE PCM remain preserved. Four original title plates
use read-only arrays and one shared 6,144-byte CHIP staging bitmap, retaining the
18,432-byte bitmap payload saving versus four resident CHIP plates. Gameplay
decor and manga remain distinct; Veil Nebula retains its crystal borders with
corridor-connected dark background cleared to space. See [rendering and memory](rendering.md) and
[campaign-art provenance](../game/art/CAMPAIGN-ART.md). Older integration-handoff
notes in the art/music records describe their original delivery, not current status.

### Evidence and open acceptance gates

Clean-presentation revision: focused transition/pixel checks and 10/10 scoped
boot/skip/title-sector/music/ACE-audio tests pass across both profiles. The fresh
injected campaign passes functional checks on both (53 captures each, all 106
visually inspected), including all 13 static scenes and snapshot-parity-correct
white flashes. Strict campaign performance remains **FAIL: A500 16 drops / 123%
peak; AROS 11 drops / 120% peak**. Production probe-OFF restoration succeeded.
See [fixture evidence](campaign-native-fixture.md#clean-presentation-revision--fresh-campaign-evidence).

The latest independent-clock balance has passed host rules, parser tests, build,
cross-profile combat with one reviewed shared-reference update, and fresh GAMEOVER
scenarios/validators on both profiles. See the scoped commands and limitations in
[the acceptance record](campaign-acceptance.md#latest-per-sector-balance-scoped-validation).
Full native campaign and strict-performance acceptance remain open.

The results below predate the GAMEOVER return, per-sector motion clock and revised
sector cadence/quota changes. Fresh host/build/native results must be reported
separately; these historical results do not validate the new balance.

- Latest ordinary production suite: **38/38 shared-golden tests PASS**;
  all **42 complete captures byte-identical across profiles**. Source-derived
  checks cover all four original titles, both selection wraps and 15,360 Nebula
  band pixels on each profile.
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
- Latest actual production A500 boot: **24,056 free chip / 30,112 total free bytes**;
  initial executable **474,992 bytes**, with the duplicate Graveyard registration removed.
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
2. Quotas 18/21/24/27 before each boss, one formation at a time.
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
members. Every fifth wave is six passive asteroids. Quotas are 18/21/24/27.

| Displayed sector (zero-based level) | Repeating five-wave cycle |
|---|---|
| 1 — Orbital Graveyard (0) | SCOUT → WEAVER → GUNNER → DART → ASTEROID |
| 2 — Veil Nebula (1) | WEAVER → DART → WEAVER → GUNNER → ASTEROID |
| 3 — Imperial Foundry (2) | GUNNER → SCOUT → GUNNER → DART → ASTEROID |
| 4 — Stellar Citadel (3) | DART → GUNNER → WEAVER → DART → ASTEROID |

Enemy/asteroid motion and age, and boss motion/tick, advance 16/17/18/20 times
per 20 combat updates by sector. The accumulator adds that sector's numerator
and subtracts 20 on a step; half-pixel parity uses a separate enemy motion clock.
Firing countdowns advance every combat tick, independently of body movement.
Both clocks freeze during
preparation and noncombat phases, and retain their phase across lifecycle resets.
Hero, shots, hostile bullets, pickups, charge, effects and world timing are unchanged.
Boss hit flash still lasts six updates, independently of skipped enemy steps.

| Sector | Motion steps / 20 | Ordinary rays (other/gunner) | Ordinary period | Boss fan rays | Boss period | Boss HP |
|---|---:|---:|---:|---:|---:|---:|
| 1 — easy | 16 | 3/5 | 96 | 5 | 64 | 108 |
| 2 — medium easy | 17 | 5/5 | 76 | 7 | 52 | 168 |
| 3 — medium harder | 18 | 5/7 | 64 | 7 | 44 | 216 |
| 4 — hard | 20 | 7/7 | 52 | 9 | 36 | 240 |

Periods are combat ticks, implemented as countdowns rather than bit masks.
Initial ordinary delay is `50 + member * 10` combat ticks (spawn update counts
as tick one); the first boss volley is after 50 combat ticks. Ordinary HP remains
one for scouts/weavers/darts and three for gunners/asteroids; extra HP is bosses
only in sectors 2/3. Sector 4 keeps its alternate lane barrage. Fan spacing,
stagger, velocities, pools and trajectory admission are unchanged: ray counts
are attempted fan sizes, not a promise of accepted/lifetime bullet totals.

After the last unskippable 40-tick hero explosion, GAMEOVER starts busy and
waits for composition. Its 150-ready-tick dwell can be dismissed by release then
fresh fire after 25 ready ticks. Both paths reset through `logicInit` to TITLE,
preserving frame/simulation/enemy clocks and scene epoch. Returned TITLE consumes
held fire/direction and requires an idle fire tick after composition before a
fresh press starts SECTOR_INTRO. Initial title and sector-selection input retain
their existing behavior; WIN and nonfinal respawn are unchanged. Audio selection
uses the existing controller and retains mute state.

`sector_enemies.txt` supplies 24 16×16 frames in `level * 6 + kind` order.
Each six-frame group includes an unused legacy-boss slot; campaign bosses still
use their separate 64×48 art. Sector 1 preserves the original six master frames;
later sectors have offline-authored derivatives. Original PNGs and the fourteen
`actors16.txt` frames remain preserved. See [provenance](../game/art/SECTOR-ENEMIES.md).

Veil Nebula renders top/bottom crystal decor through both bitmap composition and
runtime copper fetch switches. Only corridor-connected dark inks 0/1 are cleared
to background ink 0 (`#102`) after crop/seam processing: 293 top and 251 bottom
ink-1 pixels change, while 53 top and 105 bottom disconnected ink-1 shadows and
all other crystal inks remain. The original PNG, HUD and play/collision bounds
are unchanged. See the independent source/pixel checks in [rendering](rendering.md).

Holding fire only charges, with one charge-ready event at 50 combat ticks.
Release after 1–49 ticks requests a normal volley; release at full charge emits
one centered 16×10, vx4, six-damage lance. Neutral input at charge zero emits
nothing. Normal volleys are rate-limited to eight ticks; an early release is
discarded rather than queued. Scene/death transitions cancel held charge.

Five bonus kinds occupy the unchanged four pickup slots. Enum/storage order is
D/S/R/L/F (`BONUS_POWER=0`, `BONUS_FIRE=4`); the explicit drop cycle is **D → F → S → R → L**.
F raises `shotLevel` 0–2 independently of D's `weaponLevel` damage upgrade:

| HUD | Normal volley | Vertical offsets from muzzle center | Damage per shot |
|---|---:|---|---|
| F1 | 1 | 0 | 1 + weaponLevel |
| F2 | 2 | −6, +6 | 1 + weaponLevel |
| F3 | 3 | −8, 0, +8 | 1 + weaponLevel |

All normal shots travel at vx6/vy0 and fit the hero's vertical body bounds.
The twelve-shot pool is preflighted for the entire volley: insufficient space
means no partial pattern and no firing event/sound. F persists across sectors,
falls one level on death, and resets to zero on a new game, like damage/speed
upgrades. The footer's DAMAGE counter still shows `weaponLevel` 0–2, not per-shot
damage; FIRE shows shot count 1–3. DAMAGE/D is a display-only rename of POWER/P;
internal IDs and capture names retain power. Charged fire remains six damage,
independent of both upgrades.

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
| Stellar Citadel | 2400 | 8 | 27 |

Evidence and original source hashes: `game/tests/fixtures/campaign-wave-reference.json`.
Probe source: `tools/probe-wave-reference.c`. Run it against the original hashed
logic, not after quota-based progression replaces the timer.
The first three quotas remain triple the frozen reference. The fourth adds three
waves to that baseline for the new increasing-difficulty balance.

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
