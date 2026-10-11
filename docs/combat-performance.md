# Combat performance investigation

Baseline: parent commit `52a37a1`. Target remains PAL A500 7 MHz OCS,
512 KiB CHIP + 512 KiB slow, zero drops and <=90% peak. AROS is supplementary.

**Current it13: score candidate A2 accepted and applied after the user's “go A”.**
The non-inlined opaque writer hoists plane pointers/masks and removes its inner
byte loop. Repeated complete OFF results: A500 campaign5/109%, ordinary BOB1/104%;
AROS campaign3/100%, ordinary BOB0/97%. All other ordinary drops/peaks are unchanged.
Both profiles pass full pixel/state equivalence and the final exact OFF ADF boot.
Global0-drop/90% acceptance remains **FAIL**. See the
[dated A refinement report](score-A-refinement-2026-10-11-110133.md) and
[it13 iteration summary](#it13--user-selected-score-a-refined-to-a2).

**Historical it11b: physical score-digit cache and packed BOSS label accepted.**
Complete campaign improves6/116%→5/115% A500 and4/107%→3/107% AROS versus it10.
Ordinary BOB remains2/107% A500; AROS improves1/101%→1/100%. No scoped peak
regresses. Global0-drop/90% acceptance remains **FAIL**.
See [it11 complete results](#it11--physical-score-cache-and-packed-boss-label).
Latest measurement-only follow-up: [disjoint burst-frame breakdown](#it11b--disjoint-burst-frame-measurements).
Nested follow-up: [HUD blocks and BOB submission/flush](#it11b--nested-hud-and-bob-measurements).
Preceding native comparison: [opaque score cells and effect source-pair guard](hud-bob-native-comparison-2026-10-11-102053.md).
Both standalone candidates were tested twice; neither met the conservative
no-regression selection at that time. The later explicit “go A” supersedes that
selection; the full earlier decision/evidence remains preserved below.
All older tables without an explicit completion marker cover **emitted windows
only**, not complete replays; they remain historical evidence, not full-run gates.

**Historical final: both bounded optimizations accepted; production ADF validated with all
diagnostic flags OFF.** The capture race is corrected with an acknowledged-scanout
handshake. All final baseline/candidate full pixels and emitted gameplay states
match. Global 50fps acceptance remains **FAIL**, with the unchanged thresholds.
Historical failed capture trials and the original stop remain recorded below.

Full numerical tables for all 48 cases, ten stages, both profiles and each
measured iteration: [raw-counter tables](combat-performance-tables.md).

**Loop 5 / it8: no runtime candidate accepted.** Three trajectory models and two
bounded reservation caches were evaluated below. The restored production runtime
is it7 (`de9b415`); A500 acceptance remains **8 drops / 116% campaign** and
**3 drops / 114% ordinary BOB replay**. No 50fps gain is claimed for it8.

## Recap: where frame time is spent and which hardware is involved

**Latest accepted HUD step is it13 A2, with unchanged complete accounting.**
A500 complete campaign is5/109%, ordinary BOB1/104%; AROS3/100%,0/97%.
The [A refinement report](score-A-refinement-2026-10-11-110133.md) contains the
controlling complete OFF results. The it11 target-only hardware table and older
dense48-case matrix below remain historical attribution evidence.

**Latest accepted Step D is it9j:** fixed galaxies + 36 moving stars. Campaign
drops improve **8→7 A500, 7→6 AROS**; ordinary BOB improves **3→0, 2→0**. Global
0-drop/90% acceptance remains open. The it7 reference recap below is historical;
the latest raw-cost/hardware recap, latency and memory ledger are in
[it9](#it9--fixed-galaxy-step-d-accepted-at-it9j).

A500 sector 1, timing-ON fenced matrix, stable windows over the left/centre/right
bands. Each cell is the **mean per frame / max of one call** in elapsed PAL raster
lines (audio and explicit waits sum 2 and 3 calls per frame in the mean), with the
share of the 313-line (20 ms) frame. Baseline is `perf-loop4-it3c-on` (commit
`973a764`); latest is `perf-loop5-it7-on` (it7, fixed bullet streams, on top of
it6's 48 stars). Earlier loop-3 figures
used `perf-loop-base-on` (HEAD `3aae85b`) and per-call means.

| Stage | PLAY dense, baseline it3c | PLAY dense, latest it7 | BOSS dense, baseline it3c | BOSS dense, latest it7 | Hardware involved |
|---|---:|---:|---:|---:|---|
| Restore + world animate | 92.9/124 (29.7%/39.6%) | 67.1/93 (21.4%/29.7%) | 54.4/85 (17.4%/27.2%) | 54.5/88 (17.4%/28.1%) | Blitter restores; 68000 stars/decor; Agnus chip-bus contention |
| Logic, including admission and collisions | 135.9/471 (43.4%/150.5%) | 134.0/467 (42.8%/149.2%) | 70.1/200 (22.4%/63.9%) | 69.1/205 (22.1%/65.5%) | 68000 only (slow-RAM state); stalled by DMA and interrupts |
| Audio, foreground | 4.8/9 (1.5%/2.9%) | 4.8/5 (1.5%/1.6%) | 5.0/9 (1.6%/2.9%) | 4.9/9 (1.6%/2.9%) | 68000; Paula DMA and interrupts are not isolated |
| Render inclusive (contains the next four rows) | 307.2/353 (98.1%/112.8%) | 293.3/340 (93.7%/108.6%) | 318.0/362 (101.6%/115.7%) | 305.1/342 (97.5%/109.3%) | All of the below |
| BOB submission (ACE internal blit waits included) | 169.1/200 (54.0%/63.9%) | 167.4/201 (53.5%/64.2%) | 205.1/245 (65.5%/78.3%) | 204.5/239 (65.3%/76.4%) | Blitter, 68000 setup, chip-bus contention |
| Sprite stream preparation | 108.6/148 (34.7%/47.3%) | **96.4/136 (30.8%/43.5%)** | 93.7/131 (29.9%/41.9%) | **82.0/127 (26.2%/40.6%)** | 68000 writes to chip RAM; this is **not** sprite DMA time |
| Copper list build | 13.9/34 (4.4%/10.9%) | 13.8/30 (4.4%/9.6%) | 3.7/26 (1.2%/8.3%) | 3.6/9 (1.1%/2.9%) | 68000 writes; Copper execution is not measured |
| Publication | 10.6/38 (3.4%/12.1%) | 10.9/18 (3.5%/5.8%) | 10.9/33 (3.5%/10.5%) | 10.6/27 (3.4%/8.6%) | 68000, Copper pointers and palette |
| Explicit `blitWait()` (overlaps restore/BOBs) | 5.1/7 (1.6%/2.2%) | 5.3/9 (1.7%/2.9%) | 5.3/24 (1.7%/7.7%) | 5.2/12 (1.7%/3.8%) | Blitter completion |
| Fixture injection (diagnostic only, not shipped) | 79.5/107 (25.4%/34.2%) | 80.3/112 (25.7%/35.8%) | 75.1/107 (24.0%/34.2%) | 75.3/108 (24.1%/34.5%) | 68000 |

Stars move only while the world scrolls (PLAY); bosses freeze the scroll, so BOSS
restore/world cost is unchanged by the star count, as measured.
Sprite preparation is mostly hostile bullets: a diagnostic split at it6 (copper
counter retargeted to `renderBulletsDraw`, not shipped) measured bullets at
77.2 of 112.0 PLAY-dense lines and 21.5 of 43.3 sparse; hero + enemies are the rest.

Caveats:
- These are **elapsed raster times**, not pure CPU cycles. They include Agnus
  chip-bus DMA contention (bitplanes, sprites, Blitter, Copper, Paula) and
  interrupt time.
- Stages overlap: render inclusive contains BOBs, sprites, copper and HUD; the
  explicit wait overlaps restore and BOBs. Do not sum the rows.
- Maxima above 313 lines are multi-frame overruns in the **injected** density.
  They are not ordinary-play values.
- Timing ON is itself intrusive; acceptance uses the profiler-OFF runs.

## Optimization loop 5 (user-approved visual simplifications): per-iteration table

Base `973a764` (it3c accepted). Pixels change on purpose, so full-image identity
no longer applies; each step is reviewed against base captures instead.
Timing-ON stage means are A500 sector 1, dense (mean per frame / max of one call).
Ordinary production and the injected campaign are profiler-OFF; columns give
**drops/peak%**, base → candidate.

| Iteration | Change | Restore+world PLAY dense / BOSS dense | ON matrix drops/peak, A500; AROS | Ordinary A500 (pause, transitions, gameover, manga, bob_restore) | Ordinary AROS (same order) | Campaign A500; AROS | Decision |
|---|---|---|---|---|---|---|---|
| it6 stars 96->48 | `STARS_PER_LAYER` 24→12, four interleaved layers (periods 16/8/4/2) and widths kept; rows respread over the play area | 92.9/124 → **67.3/101**; 54.4/85 → 54.3/82 (stars frozen in BOSS) | 8957/368% → **7465/352%**; 6008/346% → 5577/336% | 0/90, 0/90, 0/92, 0/92, 7/117 → **0/79, 0/79, 0/87, 0/81, 3/114** | 0/88, 0/88, 0/89, 0/89, 5/115 → 0/77, 0/77, 0/84, 0/78, 2/107 | **15/122% → 9/117%**; 11/119% → 7/112% | **Accepted.** Every gameplay window except `bob_restore` is now <=90% on A500; campaign gate still fails |
| it7 fixed bullet streams | One hostile image fills all 16 slots of both buffers of each hostile channel once at creation (`spriteStreamFill`); frames write only control words (`spriteSlotPlace`) in Y order and terminate after the last used slot. Ordering keeps survivors' previous order and inserts on cached Y keys, carrying entity pointers (no per-compare pool-index multiply) | sprites 108.3/142 → **96.4/136**; 93.8/133 → **82.0/127** (render inclusive 305.4 → 293.3; 317.2 → 305.1) | 7465/352% → **6489/355%**; 5577/336% → 5501/324% | 0/79, 0/79, 0/87, 0/81, 3/114 → **0/79, 0/79, 0/85, 0/80, 3/114** | 0/77, 0/77, 0/84, 0/78, 2/107 → 0/76, 0/76, 0/82, 0/78, 2/107 | **9/117% → 8/116%**; 7/112% → 7/112% | **Accepted.** Output identical; every scenario equal or better; campaign gate still fails |

it7 review and caveats:
- The premise "bullet bitmaps are rewritten every frame" did not hold at it6: the
  generic writer already skipped pixel copies when a slot's cached source matched
  (`pLoaded`). The measured cost was per-bullet bookkeeping: source comparison,
  writer state spilled to the stack, and ×18 pool-index multiplies in the sort and
  draw loops. it7 removes those; the image was already single (strip frame 2) for
  every level, so no pixel changes were needed.
- Full-image identity holds: matrix **48/48 captures identical on both profiles**
  (`compare-combat-performance.py` vs `perf-loop5-it6-on`); ordinary **38 captures
  + 193 states** and campaign **53 + 246** per profile identical
  (`compare-combat-production.py`). Order is the same stable insertion order as
  before (survivors, then newcomers by pool index), so slot layout is unchanged.
- Kept: double buffering by back copper list, one-blank-line `nextY` guard,
  `bullet_hidden == 0` (campaign functional PASS both), PLAY 6/7 vs BOSS 4–7
  handover (enemies still own 4/5 streams in PLAY; separate allocations), palette
  25–27/29–31 mapping unchanged. Enemy/hero writers untouched (their pixel copies
  are already cached per slot).
- Production executable 487452 → **487536 bytes (+84)**; no new CHIP allocation
  (same stream sizes), no frame-loop allocation.
- Unit 1/1 PASS, Python 98/98 PASS. Evidence: `game/build/perf-loop5-it7-{on,prod,campaign}`
  and the diagnostic split `game/build/diag7a` (A500 only, not a shipped build).

it6 review and caveats:
- A500 sparse PLAY restore+world is 67.3 → 41.4 lines. BOSS is unchanged because
  the world does not scroll there. Logic, BOB and sprite means move by ≤2 lines
  (noise); no non-star stage regressed in mean.
- All 42 ordinary A500 captures were compared with base-HEAD captures from the
  same harness (`game/build/perf-loop5-head-captures`). Star pixels in the play
  area halve, for example 144 → 72, in every combat capture. Non-star differences
  are limited to animation phase: hero exhaust (14 px), charge-ready blink (400 px)
  and lance frame (75 px). World preparation now takes six fewer star steps per
  bitmap (`cut_work` 136 → 130), so each cut publishes six vblanks earlier.
- Star seeding uses an exact division-free row spread. Dirty flags, per-bitmap
  `HISTORY.stars` and the N−2 catch-up iterate `STAR_COUNT`. The layer helpers
  (`STAR_LAYER`, `STAR_WIDE`, `STAR_LAYERS`) keep dropping layer 0 (period 16)
  a local change for the planned static galaxy plane.
- `tools/verify-scrolling.py` now derives its 48-star row layout. Parallax is
  checked on each layer (8/8/8/6 samples) with exactly 72 star pixels.
- **Pre-existing, not caused by it6:** the shared goldens were already stale at
  base. Base HEAD passes only 6/19 `agk test` scenarios on A500, the same 13 fail
  with it6, and `verify-scrolling.py`'s title-decor assertion fails on base
  captures too. The goldens were last refreshed in `4e3e3bc`. Later art
  commits did not refresh them. No golden was updated in this step: a refresh would also
  accept that unreviewed earlier drift. It needs its own scoped review.
- Evidence: `game/build/perf-loop5-it6-{on,prod,campaign}`; logs alongside.

### it8 — sustained admission and rejected native trials

All evidence paths below are relative to `game/build/`. No enemy counts, boss HP,
fire periods, origins, 22px Y spacing, 6px X stagger, ray counts, vx−3, pool32,
hero geometry, display/collision gate, DMA ownership or publication bounds changed.
Only new rays used trial velocities; existing/injected mixed rays retained their
trajectories and analytic reservation fallback. Parallel pairs required |dy|>=11.
The lazy lifetime-bound trials did not use age as a retirement clock.

`tools/measure-hostile-admission.py` instruments a temporary **host-only** copy of
logic, counting acceptance immediately at spawn (including same-update exits), not
inferring it from end-of-tick pool differences. PLAY runs every sector's complete
quota without shooting; BOSS runs 20,000 ticks. The hero sweeps up/down every 100
ticks and receives invulnerability to prevent death clearing the pool. No live
bullet, enemy, countdown or trajectory is reset. This is sustained public-logic
density evidence, **not ordinary no-hit play or native timing**. The native stress
matrix still resets its actors every tick and cannot establish sustained density.

#### Opportunity and baseline table

An opportunity is an actual visible enemy fan or boss volley; eligible rays have
origins inside the corridor. All three trajectory trials and the measured per-fan
cache retain the exact opportunity/eligible counts and PLAY durations below.
Full-pool refusals are **zero in every measured row and trial**; therefore
`conflicts = eligible − accepted`. The raw JSON also retains explicit full/conflict
counts, mean occupancy and peak occupancy. Admitted rays per volley are accepted
divided by opportunities (including completely refused volleys).

| Sector / phase | Ticks | Opportunities | Eligible | Baseline accepted | Baseline conflicts | Accepted/volley | Baseline active bullet-ticks / peak pool |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 PLAY | 6877 | 252 | 768 | 313 | 455 | 1.24 | 26783 / 13 |
| 1 BOSS | 20000 | 312 | 1342 | 1342 | 0 | 4.30 | 137720 / 11 |
| 2 PLAY | 7480 | 312 | 1244 | 513 | 731 | 1.64 | 39343 / 14 |
| 2 BOSS | 20000 | 384 | 2258 | 2258 | 0 | 5.88 | 179472 / 14 |
| 3 PLAY | 8018 | 395 | 1795 | 593 | 1202 | 1.50 | 45752 / 15 |
| 3 BOSS | 20000 | 454 | 2979 | 2979 | 0 | 6.56 | 202370 / 16 |
| 4 PLAY | 7547 | 418 | 2125 | 684 | 1441 | 1.64 | 48371 / 16 |
| 4 BOSS | 20000 | 555 | 3145 | 2685 | 460 | 4.84 | 308280 / 24 |

#### Trial admission / sustained pool density

Each cell is **accepted rays (candidate/baseline %) ; active bullet-ticks / peak
pool**. Duration is identical, so bullet-tick ratios also give mean-density ratios.
The per-fan cache preserves every baseline value exactly. Shared-tick cache native
images/states match baseline, but it did not receive a separate sustained host run.

| Sector / phase | Horizontal vy0 | Parallel vy=aim | Parallel2 vy=2×aim |
|---|---|---|---|
| 1 PLAY | 388 (123.96%); 44651 / 18 | 315 (100.64%); 31580 / 14 | 361 (115.34%); 28765 / 15 |
| 1 BOSS | 1342 (100%); 218578 / 15 | 1250 (93.14%); 169844 / 14 | 1336 (99.55%); 114971 / 10 |
| 2 PLAY | 511 (99.61%); 58637 / 18 | 436 (84.99%); 41778 / 16 | 567 (110.53%); 45453 / 18 |
| 2 BOSS | 2258 (100%); 371669 / 28 | 2258 (100%); 371669 / 28 | 2258 (100%); 371669 / 28 |
| 3 PLAY | 555 (93.59%); 65854 / 19 | 464 (78.25%); 45810 / 16 | 671 (113.15%); 51831 / 18 |
| 3 BOSS | 2979 (100%); 427481 / 28 | 2676 (89.83%); 284804 / 21 | 2794 (93.79%); 199280 / 16 |
| 4 PLAY | 578 (84.50%); 68277 / 20 | 490 (71.64%); 47235 / 17 | 720 (105.26%); 54942 / 20 |
| 4 BOSS | 2993 (111.47%); 479278 / 31 | 2531 (94.26%); 338484 / 26 | 2441 (90.91%); 273284 / 24 |

Horizontal S4 PLAY loses **15.50%** of admissions. The original 85% planning floor
was explicitly relaxed to 84% for this row only, allowing native evaluation; the
ultimate rejection is for native regressions, not that initial floor. All three
models double sector-2 BOSS mean occupancy **8.9736→18.58345 (+107.09%)** because
that boss's level fan no longer diverges out of the corridor. Horizontal sector-3
BOSS also rises **10.1185→21.37405 (+111.24%)**. Increases are not treated as free.

Raw host evidence: `it8-admission-{baseline,horizontal,parallel,parallel2,cache}.json`.

#### Iteration decisions (drops / peak%)

Ordinary columns list pause / transitions / GAMEOVER / manga / BOB, in that order.
`†` means the unchanged BOB input no longer meets its kill/death/pickup timeline
and pixel assertions: raw timing is retained, **not an accepted BOB result or a
like-for-like benefit**. Replays were not replaced for rejected models; genuine
six-kill/pickup requirements and all goldens remain intact.

| Trial | Timing-ON matrix A500; AROS | Ordinary A500 | Ordinary AROS | Campaign OFF A500; AROS | Decision |
|---|---|---|---|---|---|
| it7 reference | 6489/355; 5501/324 | 0/79, 0/79, 0/85, 0/80, 3/114 | 0/76, 0/76, 0/82, 0/78, 2/107 | 8/116; 7/112 | Retained runtime |
| it8 parallel | Not run | Not run | Not run | Not run | Rejected on sustained admissions: S3/S4 PLAY 78.25%/71.64% |
| it8p2 parallel2 | 6521/369; 5468/342 | 0/79, 0/79, 0/88, 0/80, 2/128† | 0/76, 0/76, 0/86, 0/78, 1/124† | 9/116; 7/112 | Rejected: A500 campaign drops +1; doubled S2 BOSS occupancy; no gate improvement |
| it8h horizontal | 6455/345; 5444/316 | 0/79, 0/79, 0/92, 0/80, 3/105† | 0/76, 0/76, 0/90, 0/78, 1/99† | 12/116; 8/112 | Rejected: campaign drops +4/+1, GAMEOVER peak +7/+8 pp despite scoped admission exception |
| it8c per-fan cache, original curves | 6595/352; 5431/322 | 0/79, 0/79, 0/85, 0/80, 3/114 | 0/76, 0/76, 0/83, 0/78, 2/107 | 8/116; 6/112 | Rejected: no A500 gate gain; dense logic mean increases; AROS GAMEOVER +1 pp |
| it8c2 shared-tick cache, original curves | 6540/333; 5388/314 | 0/79, 0/79, 0/86, 0/80, 3/114 | 0/76, 0/76, 0/84, 0/78, 2/107 | 8/116; 6/112 | Rejected: dense logic improves only 0.76% across all sectors/phases on A500; no A500 gate gain; GAMEOVER +1/+2 pp |

Every executed campaign and timing matrix passes functional checks on both
profiles, including zero hidden bullets. Ordinary first-four-scenario source and
lifecycle checks pass for all four native candidates. Both cache trials also pass
the original BOB replay/source restoration checks. Native directories:
`perf-loop5-{it8p2,it8h,it8c,it8c2}-{on,prod,campaign}`. Strict campaign output says
budget FAIL even though this runner's existing process exit status is zero; the
recorded performance verdict, not exit status, determines acceptance.

#### Hardware-time recap for it8

Same A500 sector-1 dense windows and units as the main recap: **mean per frame /
maximum call raster lines**, with percentage of 313 lines. Latest attempted is
**rejected it8c2**, not the selected runtime; the main it7 hardware recap remains
the accepted reference. Audio sums two foreground calls; wait sums three. Inclusive
rows overlap, timing ON is intrusive, and matrix injection is not ordinary play.

| Stage / hardware | PLAY it7 → rejected it8c2 | BOSS it7 → rejected it8c2 |
|---|---|---|
| Restore/world — Blitter, 68000, chip-bus DMA | 67.07/93 (21.43%/29.71%) → 67.44/96 (21.55%/30.67%) | 54.49/88 (17.41%/28.12%) → 54.39/83 (17.38%/26.52%) |
| Logic — 68000, DMA/interrupt stalls included | 134.01/467 (42.82%/149.20%) → 133.15/430 (42.54%/137.38%) | 69.06/205 (22.06%/65.50%) → 69.32/185 (22.15%/59.11%) |
| Audio — foreground 68000, not isolated Paula IRQ | 4.82/5 (1.54%/1.60%) → 4.84/8 (1.55%/2.56%) | 4.95/9 (1.58%/2.88%) → 4.97/9 (1.59%/2.88%) |
| Render inclusive — all render hardware below | 293.28/340 (93.70%/108.63%) → 293.50/329 (93.77%/105.11%) | 305.11/342 (97.48%/109.27%) → 305.98/344 (97.76%/109.90%) |
| BOB — Blitter plus 68000 setup/internal waits | 167.41/201 (53.48%/64.22%) → 167.47/201 (53.50%/64.22%) | 204.52/239 (65.34%/76.36%) → 205.28/245 (65.58%/78.27%) |
| Sprite prep — 68000 CHIP writes, not DMA time | 96.42/136 (30.81%/43.45%) → 96.52/127 (30.84%/40.58%) | 82.03/127 (26.21%/40.58%) → 81.81/111 (26.14%/35.46%) |
| Copper build — 68000 CHIP writes | 13.79/30 (4.41%/9.58%) → 13.78/29 (4.40%/9.27%) | 3.57/9 (1.14%/2.88%) → 3.46/7 (1.11%/2.24%) |
| Publication — 68000 palette/pointers | 10.86/18 (3.47%/5.75%) → 10.77/33 (3.44%/10.54%) | 10.61/27 (3.39%/8.63%) → 10.61/21 (3.39%/6.71%) |
| Explicit wait — Blitter completion, overlapping | 5.27/9 (1.68%/2.88%) → 5.33/7 (1.70%/2.24%) | 5.19/12 (1.66%/3.83%) → 5.18/7 (1.66%/2.24%) |
| Injection — diagnostic 68000 only | 80.29/112 (25.65%/35.78%) → 79.94/112 (25.54%/35.78%) | 75.30/108 (24.06%/34.50%) → 75.18/108 (24.02%/34.50%) |

S1 PLAY/BOSS dense logic means/max for the other rejected trials are parallel2
**135.43/511, 69.96/208**, horizontal **132.66/445, 68.46/192**, per-fan cache
**135.53/486, 69.29/175**. These small changes do not resolve the large inclusive
BOB/render cost. All sectors/stages/raw samples are retained in `it8-stage-tables.md`
and each matrix's `{a500,a500-aros}-stages.json`, generated by
`tools/summarize-combat-performance.py`.

#### Validation and final state

- The known parallel2 pool-hole fixture was corrected without weakening it:
  gunner Y100/144, hero Y192, blockers Y104/148 on both channels, all vy2.
  Fan1 admits Y60/82/126 on channels6/7/6; fan2 admits Y126/170/192 on7/6/7.
  Four genuine refusals leave exactly six accepted rays in slots1/3/5/7/8/9;
  exact moved coordinates and channels passed. Horizontal used the same oracle
  with vy0. Rejected generators were then removed and the original mixed-curve
  fixture/oracles restored. New injected-trajectory checks remain separate from
  generator expectations: 10/11/12 separation, both parities, vy−2..2, pool holes,
  mixed convergence and lifetime bounds, and partial-left reservation until x<=−6.
  Existing pause, handover, visibility and collision-semantics tests remain.
- Parallel2 passed host C and all 98 Python tests before native evaluation.
  Horizontal and both caches passed host C. Both caches match **96/96 matrix
  images**, plus **182/182 ordinary/campaign captures and 878 state records**
  against it7. Visual review included native parallel2/horizontal boss2 curtains,
  both models' AROS boss1 trajectories, parallel2 dense PLAY and the restored
  ordinary bonus-drop image. No masking or golden refresh was used; the known
  pre-it6 stale shared goldens still require their own review.
- The runtime source is restored exactly to it7 (`git diff -- game/src/logic.c`
  is empty). No trajectory or cache is selected. Final host **1/1**, Python
  **98/98**, build and `git diff --check` pass. All four diagnostic flags are OFF.
  The fresh **487536-byte** production executable is byte-identical (`cmp`) to
  `perf-loop5-it7-prod/a500/astra`, SHA256
  `9168c261b88d734c2d9fa9b4d5de8f7d348d9bd403701661d2c26661683c2960`.
  Fresh ADF SHA256:
  `9fece8d458f5e81a823d813b29c4d0cf25984271e0f3ad47b4850b083ebc356d`.
  `perf-loop5-it8-restored-prod` reruns all five ordinary scenarios on both
  profiles, with functional/source checks PASS; A500 results exactly reproduce
  it7's drops/peaks. AROS GAMEOVER reports 83% versus archived it7's 82% despite
  the identical executable: one-point differences are not conclusive source
  regressions. BOB remains 3/114 A500, 2/107 AROS. Startup free CHIP/total RAM is
  **51616/64072 A500**, **152248/1374808 AROS**, not a worst-case bound.
  The host measurement harness and additional tests are retained as investigation
  work, not a claimed runtime optimization; no rejected candidate is committed.
- **Net accepted gain: zero.** Baseline hardware remains A500 7MHz OCS PAL,
  512KiB CHIP + 512KiB slow. Campaign still needs 8 drops removed and 26 percentage
  points of peak headroom; ordinary BOB needs 3 drops removed and 24 points. AROS
  has supplementary memory and cannot establish A500 feasibility.

### it10 — complete-window accounting and accepted HUD step

The user authorized correction of the previously reported accounting defect.
**Accept the HUD candidate:** independently dirty upgrade counters and narrow
number formatting, with unchanged glyph rendering, both physical-buffer caches,
same-frame visibility, logic, enemy quotas, health, effect counts/durations,
galaxy restoration and audio. The font-only trial stays rejected. The intermediate
dirty-only trial is not selected. This is a measured incremental improvement,
not completion of the50fps goal.

#### Local accounting correction and boundary contract

- The installed AGK provides `agkPerfReport()`, which prints its actual pending
  count and resets the accumulators. However, `agkPerfEnd()` used to report before
  the next `agkPerfBegin()` counted the preceding frame's missed vblanks. A naïve
  final flush loses the last frame's drops when the final window is exactly50.
- `game/tools/patch-perf.py` transforms a **build-local copy** of the installed
  `runtime/src/perf.c`, with exactly-one-match anchors. CMake replaces only that
  translation unit in this project's AGK target and rejects a changed source
  inventory. The installed kit is untouched. Original source SHA256:
  `fefcb992ba03b88dc41b915409b02ab4aef5ec34c46e979b28147ebb027ffe8c`.
- Full windows report at the following Begin, after counting the prior frame's
  missed vblanks. Begin's sampled timestamp still precedes regular reporting, so
  report CPU/serial time remains in the following measured gameplay frame. The
  report's timing position changes relative to old evidence; both baseline and
  candidate were rebuilt with the identical correction. This is not a comparison
  of a patched candidate with an old unpatched binary.
- The runners retain exact copies of each original replay and append only an F8
  key command, a completion-marker wait and a marker assertion. At that Begin,
  F8 flushes the pending samples and reports cumulative actual frames/drops plus
  `boundary_frame`. It does not execute a new logic/render tick or call End for
  the boundary itself. No fake50-frame window, padding wait, timer reset, warmed
  measurement interval or excluded original tail is used.
- The final report (partial **or full**), marker and subsequent display hold are
  explicitly **post-measurement overhead**. The hold emits harness ticks so serial
  and audio can be collected, but advances neither gameplay nor the meter. F8 is
  compiled only with the existing `AGK_SERIAL_ENABLED` debug channel and is absent
  from a non-debug build. All four ASTRA diagnostic flags remain OFF for ordinary
  production timing; campaign injection alone is ON in the injected fixture.
- Each completed-frame drop is assigned once to the window containing that
  frame. `astraPerfFinish` is idempotent; empty reports emit no zero-frame record.
  `agkPerfBegin()` remains the first frame-loop operation; after completion its
  finished latch allows harness ticks but cannot reopen the meter, even if End
  is accidentally called. Both final builds include and test this latch.
  Host tests execute the transformed actual AGK source for0/1/49/50/51/99/100/101
  frames, including1/3 missed vblanks on the final frame and duplicate flushes.
  Regular-report overhead is simulated and asserted inside the following sample.
- `perf_boundary.py` rejects missing/duplicate completion markers, malformed
  partial counts, reports after completion, mismatched raw serial/manifest windows,
  and inconsistent cumulative counts. Generated scenario inventory and complete
  source text are checked, not silently ignored. Historical `--check-only` reads
  label missing completion markers `complete=false`; strict acceptance requires
  complete evidence. Campaign build/finally restoration explicitly sets all flags.
- The optional combat-stage profiler also flushes partial windows and now reports
  their actual `frames` alongside call counts. An executable host test verifies
  exact frame/call/line counts and duplicate-flush behavior. No intrusive full
  stage-profile run was used to establish this acceptance.

The initial boundary trial emitted its marker then exited, which prevented the
harness from completing serial/audio capture. The retained failed run is
`perf-loop5-it10-complete-candidate-prod`; the explicit post-measurement hold fixes
that integration problem. The strict comparison's new input-directory rejection
was resolved by checking every generated replay against original+exact suffix.
Neither correction weakens gameplay, image, lifecycle or performance assertions.

#### Complete profiler-OFF results

Both builds use the accounting correction and original scenario inputs. Table
entries are **dropped vblanks / peak load%**. Every final window is included once.

| Scenario | Actual frames / final window | A500 it9j → accepted HUD | AROS it9j → accepted HUD |
|---|---:|---:|---:|
| Pause continuity | 1417 /17 | 0/80 → **0/77** | 0/77 → **0/75** |
| Clean transitions | 1000 /50 | 0/80 → **0/76** | 0/77 → **0/75** |
| GAMEOVER/title | 3054 /4 | 0/83 → 0/83 | 0/81 → 0/81 |
| Manga | 1159 /9 | 0/81 → **0/78** | 0/79 → **0/76** |
| Ordinary BOB | 1247 /47 | 3/108 → **2/107** | 2/105 → **1/101** |
| Injected campaign | 9172 /22 | 8/116 → **6/116** | 6/110 → **4/107** |

Counts are equal between builds and profiles. Their boundary logic-frame IDs are
1170/753/2807/911/1000/8925 respectively. Meter totals also include measured intro
iterations, explaining why they are not equal to the gameplay frame counter.
For BOB, the previously omitted47-frame tail exposes the remaining overruns.
For clean transitions, the final complete50-frame window is now properly included.
No arbitrary replay extension was added to reach a report boundary; any elapsed
iterations before key recognition are measured and their exact count is reported.

Weighted, quantized mean loads are not universally lower: A500 BOB
32.663→32.623%, campaign34.656→34.650%; AROS BOB31.350→31.392%,
campaign33.298→33.358%. These small changes are retained explicitly. Acceptance
is the requested drop reduction without peak regression, not a blanket mean-cost
improvement. The unchanged0-drop/90% global gate still fails.

Hardware recap: the prior targeted trace attributes the useful HUD savings to
removing redundant CPU formatting/font work and three unnecessary Blitter clears
when only one upgrade counter changes. Two S1 death HUD calls fall115→46 and
92→36 raster lines. Six-effect BOB bursts remain approximately95–112 lines,
including CPU setup, internal waits, masked Blitter DMA and chip-bus contention;
the second-buffer BOSS label redraw remains68–69 lines. The complete-window
correction measures whole iterations and does **not** isolate Paula interrupts,
Copper/sprite DMA occupancy or pure CPU cycles. No new stage-cost claim is inferred
from the corrected aggregate percentages. Actual final68000 instructions are
retained in `perf-loop5-it10-final-68000.txt` for world, BOB, boss and effects.

#### Identity, validation and final production

- **182/182 complete images and908 gameplay-state records identical** between
  complete baseline and candidate: per profile38 ordinary captures/199 states,
  53 campaign captures/255 states. The original906 records still match; one extra
  BOB heartbeat/frame1000 per profile is present identically before the boundary.
  No state field is ignored, no masking/golden change, no phase re-alignment.
- Functional/source/lifecycle checks pass for every ordinary case and all13
  campaign scenes, four bosses/flashes/deaths, six simultaneous effects and F
  fixtures. Final restored-OFF galaxy source checks pass all four sectors and
  pause continuity: **352256 exact pixels/profile**.
- C1/1 and Python107/107 pass, including actual patched counter execution, strict
  header/manifest validation, stage partial flushes, and narrow/full-width number
  formatting. No allocation change requires new allocation-failure injection.
- Final production executable **501576 bytes**, versus identically metered
  it9j501248 (+328 HUD bytes). A500 startup free CHIP/total is41104/50432;
  AROS152248/1361168. Startup figures are not formal worst-case memory bounds.
- All four ASTRA flags are OFF. Final executable SHA256
  `e31f49fd6c5b4776640c512ed864133e8ea6abacd604600e5a0c6d0441c5325e`, ADF
  `d01105e715a10120111754eeb18d49b8ace63a9572be2ff40ff2734d550d6d38`.
  `cmp` matches the measured candidate binary after restoration; the final ADF
  was booted/source-validated on both profiles.

Evidence under `game/build/`:
`perf-loop5-it10-complete-{base-final-prod,base-final-campaign,hud-final-prod,hud-final-campaign}`,
candidate `comparison.json`, `perf-loop5-it10-complete-final2-galaxy` and
`perf-loop5-it10-complete-off-final` (fresh both-profile BOB replay/source checks).
Earlier complete-meter trials remain retained, but the final paired rebuilds
above are authoritative and include the post-boundary finished latch.
The it8 pending documentation, tests and admission harness remain outside this
accepted step; no installed kit, other worktree, GUI or paid service was changed.

**Precise remaining complete-window gap:** A500 campaign6 dropped vblanks and
26 peak-load points; ordinary BOB2 drops and17 points. AROS campaign4 drops/107%,
BOB1/101%. Next bounded diagnosis remains the simultaneous effects/score bursts,
boss HUD recreation overlapping firing work, and the now-counted ordinary
wave-spawn/pickup tail. Global50fps is not achieved.

### it11 — physical score cache and packed BOSS label

Accepted it11b against `aa02d4b`, on isolated `perf/combat-loop`. The existing
build-local AGK accounting transform is unchanged: whole iterations, ordinary
report overhead, final full/partial windows and final-frame missed vblanks remain
included. The installed AGK source hash is verified unchanged. No timing evidence
from the older incomplete-window runs is used for acceptance.

#### Two bounded candidates and complete OFF results

1. **it11a:** retain nine score-text bytes per physical bitmap, initialized with
   the composition command and copied with that bitmap's frozen history. Dirty
   updates convert only the new score; the old digits come from actual history.
   Only changed glyphs/rectangles draw. Superseded as a standalone result: peak
   improves one point, but no drop is removed.
2. **it11b (selected):** retain it11a and pack the four fixed BOSS glyphs into
   seven32-bit masks at startup using the existing font. After the existing ink1
   clear, seven pairs of aligned OR.L writes set planes1/3 for ink11. Exterior
   bits are preserved. This removes the general glyph loop for this label only.

No failed/rejected runtime candidate is omitted: both measured trials are below;
it11a is retained as part of it11b. Incremental decimal carry and narrower bar
rectangles were inspected but not implemented or measured. Health and charge
still clear/refill their existing bars; score already had glyph-level dirtiness.

Entries are **dropped vblanks / peak load%**; each sequence is it10→it11a→it11b.

| Scenario | Actual frames / final window | A500 | AROS |
|---|---:|---:|---:|
| Pause continuity | 1417 /17 | 0/77→0/76→**0/76** | 0/75→0/74→**0/74** |
| Clean transitions | 1000 /50 | 0/76→0/76→**0/76** | 0/75→0/74→**0/74** |
| GAMEOVER/title | 3054 /4 | 0/83→0/83→**0/83** | 0/81→0/81→**0/81** |
| Manga | 1159 /9 | 0/78→0/78→**0/78** | 0/76→0/76→**0/76** |
| Ordinary BOB | 1247 /47 | 2/107→2/107→**2/107** | 1/101→1/100→**1/100** |
| Injected campaign | 9172 /22 | 6/116→6/115→**5/115** | 4/107→4/107→**3/107** |

Original replays and completion boundaries are unchanged; boundary logic-frame
IDs remain1170/753/2807/911/1000/8925. Both trials match the accepted it10 baseline
at **182 complete images and908 gameplay-state records**, without masks or ignored
state fields. All ordinary source/lifecycle checks and all13 campaign scenes pass.
The baseline is the retained identically metered it10 final pair, not an older
unpatched executable.

Weighted quantized mean load is not universally lower. it10→it11b A500 ordinary
BOB32.6231→32.5453%, campaign34.6502→34.5685%; AROS31.3921→31.3119% and
33.3583→33.2087%. A500 manga22.7688→22.8119% is a small increase. No claim of a
universal mean-time improvement or global50fps acceptance is made.

#### Exact targeted events and hardware attribution

The guarded trace retains only six campaign frames and four ordinary BOB frames,
with10 slots, zero omitted records and no timestamp reads on other frames. It
samples HUD begin/end, BOB end and score conversion begin/end; it does not run the
dense profiler or print during gameplay. F8 flushes it after the complete meter
boundary. `it10_counts` is the legacy trace-call counter (9175/1250), **not** the
completed-frame denominator (9172/1247).

The selected campaign IDs are751/2817/4879/6927 (six-kill bursts),7704 (S4 boss
tick86 with regular-report/firing workload),7780 (S4 second-bitmap post-respawn
BOSS-label redraw). The preliminary retained trace also sampled5550; the final
trace replaces that first-boss draw with7704, which belongs to the other remaining
drop window. Ordinary events cover816 (kill),954 (wave-spawn tail),977 (pickup),
981 (kill). These are target-call elapsed times, not exact OFF per-frame timers.

Each timing cell is **A500 / AROS raster lines**, it11b with targeted diagnostics ON.
HUD includes formatter time. BOB includes CPU setup, waits, masked DMA and bus
contention. Do not sum overlapping columns.

| Frame / event | Target elapsed | Score formatter | HUD | BOB submission |
|---|---:|---:|---:|---:|
| 751 S1 six effects/score | 336 /307 | 4 /3 | 27 /26 | 95 /70 |
| 2817 S2 six effects/score | 372 /343 | 3 /3 | 41 /39 | 109 /70 |
| 4879 S3 six effects/score | 367 /343 | 3 /3 | 41 /40 | 113 /90 |
| 6927 S4 six effects/score | 366 /341 | 3 /3 | 41 /40 | 110 /87 |
| 7704 S4 BOSS tick86 | 313 /295 | — | 5 /5 | 60 /50 |
| 7780 S4 BOSS label after respawn | 298 /288 | — | 29 /29 | 60 /49 |
| 816 ordinary kill | 304 /290 | 15 /3 | 42 /40 | 47 /39 |
| 954 ordinary wave-spawn tail | 338 /317 | 3 /3 | 26 /25 | 63 /49 |
| 977 ordinary pickup | 271 /260 | — | 20 /20 | 33 /27 |
| 981 ordinary kill | 296 /289 | 4 /3 | 45 /44 | 38 /31 |

**A500 targeted recap:** four-burst formatter mean/max3.25/4 lines
(1.04%/1.28% of313), HUD37.5/41 (11.98%/13.10%), BOB106.75/113
(34.11%/36.10%). The selected BOSS HUD calls mean/max17/29 (5.43%/9.27%),
BOB60/60 (19.17%). These are event samples, not steady-state dense averages.
The earlier it10 S4 label HUD was68–69 lines; its probes differ, so that comparison
is attribution, not a matched OFF delta. The new OFF drop reduction is authoritative.

Instrumentation is still material: OFF→ON A500 campaign5/115→5/120, BOB2/107→2/112;
AROS campaign3/107→3/111, BOB1/100→1/105. Same complete frame counts. No fixed
overhead is subtracted. `galaxyTraceBegin` follows AGK Begin, so target elapsed
excludes the regular AGK report that the whole-frame meter correctly includes.
Clock-call time, DMA alignment and Paula interrupts also perturb samples; the
15-line ordinary formatter sample is elapsed time, not evidence of15 CPU-only
lines. Window totals cannot prove the exact OFF duration of every named event.

Actual68000 audit: `numberText` retains MULU.W reciprocal arithmetic for narrow
values and bounded shifts/subtractions for full-width values; no division helper
is imported by world/BOB/effect objects. The BOSS path is inlined to14 aligned
OR.L writes after `blitWait()`. Boss HP retains its existing word division.
Pinned ACE header/source and installed BOB technique were inspected: background
saves precede masked draws, with N−2 restore histories. Moving stars mean a
stationary effect cannot safely skip save/restore/draw. No BOB early return,
effect suppression, scheduling delay, collision/audio/timeline change was added.

#### Validation, memory, artifacts and remaining gap

- C1/1 and Python108/108 PASS. Tests exercise non-alternating physical score
  histories, composition reset, decimal/uint32 wrap, unchanged-digit no-writes,
  and packed BOSS output versus the original writer across whole framebuffers
  with varying exterior bits. Existing source-glyph checks remain intact.
- The first host run exposed an extraction-harness compile error: newly called
  `numberText` was absent from `test_title_composition`'s extracted C. Reported
  before correction, retained in `.tmp/it11-first-failure.txt`; the harness now
  extracts the real formatter. No native functional failure or weakened assertion.
- Target static storage increases48 bytes: score histories204→224 bytes plus
  28-byte label. No allocation or additional bitmap. Production executable501636
  bytes (+60 versus it10); A500 startup free CHIP/total41104/50488, AROS
  152248/1361224. These startup readings are not a formal worst-case RAM proof.
- Final OFF ADF boot/source validation passes all four sectors on both profiles:
  **352256 exact galaxy pixels/profile** plus frozen-pause checks. `cmp` proves
  the restored executable equals the measured it11b ordinary executable.
- All four ASTRA flags OFF. Executable SHA256
  `b105cfd770f07089252652179023771f8f93908066e705c1fb226d9e3e0b9c06`;
  final ADF `12b0443be19928af5be4f4051aa853d5185370be3b83f2cfe8d6cca86b0f17ad`.
  A maintained trace-runner check regenerated the disk metadata after source-pixel
  validation; the executable remained identical. This final disk was then booted
  on both profiles with complete BOB replays, source-restoration validation and
  ten byte-identical captures (`off-boot/report.json`).

Evidence in `game/build/`: `perf-loop5-it11{a,b}-{prod,campaign}` (including both
`comparison.json` files), `perf-loop5-it11-targeted{,-final}`, and
`perf-loop5-it11-final/{validation.log,68000.txt,galaxy/,off-boot/}`. The previous it8 pending
docs, C tests and admission harness remain unstaged and unchanged.

**Remaining complete-window gap:** A500 campaign5 drops and25 peak-load points
above90; ordinary BOB2 drops and17 points. AROS campaign3/107%, BOB1/100%.
The six-effect BOB bursts dominate the measured selected HUD/BOB costs; the
S4 tick86 report/firing window and ordinary spawn/kill tail remain unresolved.
Two bounded candidates are measured; this accepted increment is not viability.

### it11b — disjoint burst-frame measurements

Measurement-only follow-up at HEAD `10f4f47`, in the isolated `astra-perf`
checkout. No optimization or gameplay change. **The previous 216-line / 13.80 ms
residual was not all sprite work:** it included logic, fixture injection, audio,
world work, state reporting and publication. The following are **new native
measurements**, not a proportional allocation of that old residual.

#### Boundary contract and units

`ASTRA_FRAME_BREAKDOWN` selects fixed timestamp stores on campaign frames
751/2817/4879/6927 only, or ordinary frames816/954/977/981. It requires the existing
presentation trace to be enabled for the experiment. Other frames perform no
trace clock reads. Arrays are fixed-size; diagnostic output is deferred to F8,
after the original replay's complete performance boundary. The full combat
profiler and stress matrix are OFF throughout.

The 24 successive intervals share endpoints: trace begin → main bookkeeping →
BOB restoration → world animation → music controller → input/pre-logic → fixture
injection → logic/filter → sound events → renderer setup → HUD → BOB submission →
display gate → copper build → pause overlay → hero → enemy → hostile streams →
renderer return → post-render bookkeeping → fixture QA → state report → final
blit wait → publish → trace end. The main table groups only the small bookkeeping
intervals; each interval appears once. Nested logic and score-format timestamps
are **inside** their parent and never added again to the frame sum.

Raw timestamps and parsed partitions are in
`game/build/it11b-frame-breakdown/report.json`, with original `serial.txt` files
under `{split,light,off}/{campaign,bob_restore}/{a500,a500-aros}`. The parser
`tools/frame_breakdown.py` rejects missing/duplicate frames, duplicate or backward
timestamps, nested boundaries outside their parent, and disagreement with AGK's
whole-iteration identity. Three host tests exercise sum identities and rejection
paths. All selected native split traces pass the identities.

Units: elapsed PAL raster lines; **ms = lines × 20 / 313**, **% of the 20 ms
budget = lines × 100 / 313**. Percentages are budget shares, not shares of an
overrunning frame. Rounding applies only to display, not to the exact integer sum.

#### A500 primary: four campaign bursts, disjoint table

Baseline hardware is 68000 7 MHz, OCS PAL, 512 KiB CHIP + 512 KiB slow. Each burst
is PLAY stage51 immediately after the fixture injects six collision shots.

| Segment | 751 | 2817 | 4879 | 6927 | Mean lines | Mean ms | %20 ms | Hardware/work covered |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Restoration | 8 | 5 | 5 | 5 | 5.75 | 0.367 | 1.84% | 68000 setup, N−2 Blitter restore and its wait |
| World animation | 25 | 25 | 25 | 25 | 25 | 1.597 | 7.99% | 68000 star writes to CHIP; no galaxy decode |
| Logic/filter, inclusive | 78 | 80 | 79 | 81 | 79.5 | 5.080 | 25.40% | 68000 rules; nested split below |
| Foreground music controller | 3 | 3 | 3 | 3 | 3 | 0.192 | 0.96% | 68000 controller call |
| Sound events + call setup | 14 | 14 | 15 | 15 | 14.5 | 0.927 | 4.63% | 68000 SFX dispatch |
| HUD, inclusive of formatting | 27 | 41 | 41 | 53 | 40.5 | 2.588 | 12.94% | CPU glyph work, clears, waits, contention |
| BOB submission | 96 | 105 | 108 | 93 | 100.5 | 6.422 | 32.11% | CPU queue/setup, save/masked Blitter DMA, internal waits |
| Copper build | 3 | 3 | 3 | 4 | 3.25 | 0.208 | 1.04% | CPU builds back-list commands |
| Hero sprite preparation | 10 | 17 | 9 | 9 | 11.25 | 0.719 | 3.59% | CPU writes back CHIP streams |
| Enemy sprite preparation | 7 | 7 | 8 | 7 | 7.25 | 0.463 | 2.32% | CPU prepares empty streams after six kills |
| Hostile sprite preparation | 12 | 12 | 11 | 12 | 11.75 | 0.751 | 3.75% | CPU sorts/places hostile streams |
| Fixture injection | 22 | 22 | 22 | 22 | 22 | 1.406 | 7.03% | Snapshot copies, six artificial shots, injection serial marker |
| Fixture after-frame QA | 6 | 5 | 6 | 6 | 5.75 | 0.367 | 1.84% | CPU lifecycle/visibility checks and capture predicates |
| State-report interval | 29 | 30 | 29 | 30 | 29.5 | 1.885 | 9.42% | Report predicate, state counting/formatting and debug output |
| Final explicit blit wait | 2 | 2 | 2 | 2 | 2 | 0.128 | 0.64% | Final wait only; earlier waits stay in their own stages |
| Publication | 10 | 10 | 10 | 10 | 10 | 0.639 | 3.19% | CPU palette/pointers, view/copper publication |
| Other bookkeeping/instrumentation | 30 | 30 | 30 | 30 | 30 | 1.917 | 9.58% | Binding/ack/input, routing, pause check, call returns and trace bookkeeping |
| **Exact target sum** | **382** | **411** | **406** | **407** | **401.5** | **25.655** | **128.27%** | Every main interval counted once |

In this new trace, the non-HUD/non-BOB sum is **260.5 lines / 16.645 ms**, not
the old216/13.80. Its main components are logic5.080 ms; restore/world1.965 ms;
sprite preparation1.933 ms; foreground audio1.118 ms; fixture injection/QA plus
state reporting3.658 ms; copper0.208 ms; final wait/publication0.767 ms; and
bookkeeping1.917 ms. This fully accounts for the **new** residual. Probe overhead
and shifted DMA/IRQ phase prevent assigning these numbers retrospectively to
the old336/372/367/366-line samples.

#### Nested logic: projectile calculations versus other rules

These rows partition the79.5-line parent above; **do not add them to the main
table**. Collisions include player shots versus enemies and hero interactions,
plus their kill/effect/reward consequences. Visibility scheduling is logical
admission/display bookkeeping, separate from hardware-stream rendering.

| Within logic | 751 | 2817 | 4879 | 6927 | Mean lines | Mean ms | %20 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| Setup, effects, clocks, hero | 7 | 6 | 6 | 6 | 6.25 | 0.399 | 2.00% |
| Enemy spawn/move/fire, including any hostile trajectory admission | 5 | 13 | 12 | 14 | 11 | 0.703 | 3.51% |
| Player + hostile projectile movement | 9 | 9 | 9 | 9 | 9 | 0.575 | 2.88% |
| Pickups update | 2 | 2 | 2 | 2 | 2 | 0.128 | 0.64% |
| Shot + hero collisions, inclusive | 34 | 30 | 30 | 30 | 31 | 1.981 | 9.90% |
| Visibility scheduling | 17 | 16 | 16 | 17 | 16.5 | 1.054 | 5.27% |
| Boss-entry gate | 2 | 2 | 2 | 1 | 1.75 | 0.112 | 0.56% |
| Logic return/filter tail | 2 | 2 | 2 | 2 | 2 | 0.128 | 0.64% |
| **Inclusive parent** | **78** | **80** | **79** | **81** | **79.5** | **5.080** | **25.40%** |

Thus straight projectile movement is0.575 ms in these samples, whereas collision
resolution is1.981 ms. The0.703 ms enemy block is **not an isolated admission
benchmark**: it also includes spawn, motion and firing decisions; no claim that
admission was called or consumed that entire interval is made. A dense firing
frame may have a very different breakdown. Nested timestamps add their own cost.

#### AROS supplement: same four IDs and partition

AROS has additional fast RAM and cannot establish baseline A500 memory feasibility.
Columns retain the same frame order and units. Hardware interpretation is the
same as the primary table.

| Segment | 751 | 2817 | 4879 | 6927 | Mean lines | Mean ms | %20 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| Restoration | 8 | 6 | 6 | 5 | 6.25 | 0.399 | 2.00% |
| World | 25 | 24 | 25 | 25 | 24.75 | 1.581 | 7.91% |
| Logic/filter | 75 | 77 | 77 | 79 | 77 | 4.920 | 24.60% |
| Music controller | 2 | 3 | 2 | 2 | 2.25 | 0.144 | 0.72% |
| Sound events | 18 | 18 | 18 | 18 | 18 | 1.150 | 5.75% |
| HUD | 26 | 40 | 39 | 51 | 39 | 2.492 | 12.46% |
| BOBs | 70 | 80 | 88 | 73 | 77.75 | 4.968 | 24.84% |
| Copper | 4 | 4 | 4 | 3 | 3.75 | 0.240 | 1.20% |
| Hero sprites | 9 | 18 | 10 | 10 | 11.75 | 0.751 | 3.75% |
| Enemy sprites | 7 | 8 | 8 | 7 | 7.5 | 0.479 | 2.40% |
| Hostile sprites | 12 | 11 | 11 | 11 | 11.25 | 0.719 | 3.59% |
| Injection | 22 | 22 | 22 | 22 | 22 | 1.406 | 7.03% |
| QA | 7 | 5 | 5 | 5 | 5.5 | 0.351 | 1.76% |
| State report | 29 | 29 | 29 | 29 | 29 | 1.853 | 9.27% |
| Final wait | 1 | 2 | 2 | 2 | 1.75 | 0.112 | 0.56% |
| Publish | 11 | 10 | 10 | 10 | 10.25 | 0.655 | 3.27% |
| Other bookkeeping/instrumentation | 27 | 32 | 29 | 32 | 30 | 1.917 | 9.58% |
| **Exact target sum** | **353** | **389** | **385** | **384** | **377.75** | **24.137** | **120.69%** |

#### AGK edges and ordinary wave-tail contrast

The build-local AGK transform exposes its **already sampled** Begin/End endpoints
under the presentation diagnostic flag; the installed AGK remains untouched.
`AGK whole = Begin-to-trace prefix + target sum + trace-to-End suffix` holds
exactly for every selected frame. Prefix includes ordinary periodic reporting
when it occurs. Suffix includes trace-record copying, the F10 check and the path
to AGK's endpoint. It is not silently dropped from whole-frame accounting.

| Frame | A500 prefix + target + suffix = AGK whole | AROS same identity | Regular AGK report in prefix? |
|---|---|---|---|
| 751 | 2 + 382 + 5 = 389 | 2 + 353 + 5 = 360 | No |
| 2817 | 3 + 411 + 5 = 419 | 2 + 389 + 4 = 395 | No |
| 4879 | 3 + 406 + 5 = 414 | 2 + 385 + 4 = 391 | No |
| 6927 | 2 + 407 + 5 = 414 | 2 + 384 + 5 = 391 | No |
| Ordinary954 | 10 + 384 + 5 = 399 | 10 + 362 + 5 = 377 | **Yes**, included in whole |

Campaign AGK whole means are409 lines /26.134 ms A500 and384.25 /24.553 ms AROS.
The10-line ordinary954 prefix is an **inclusive Begin/report interval**, not a
claim of10 isolated serial lines. The AGK sample begins after its harness tick;
that pre-sample tick and the vblank wait after End are outside both intervals.
F8's final report/marker/hold and deferred trace dump remain outside the completed
replay, as before; ordinary reports followed by gameplay stay inside it.

Ordinary954 is a real input-driven wave-spawn tail, not the six-shot fixture:
A500 logic95 lines (6.070 ms), including spawn/move/fire26, projectile movement9,
collisions14 and scheduling25; enemy sprite preparation40 lines (2.556 ms),
versus7–8 after the fixture kills every enemy. Hero/enemy/hostile preparation
totals62 lines (3.962 ms); restore/world38, HUD32, BOB63, copper14, music/SFX5,
state report31, wait/publication12, bookkeeping30. The remaining injection/QA
boundary slots are1+1 lines of **measurement overhead around compiled-out hooks**,
not fixture work. Sum384 lines exactly. AROS954 logic85, enemy sprites39, total362.
Both ordinary source-artwork/restoration checks pass. Raw816/977/981 records are
retained as additional ordinary kill/pickup evidence.

#### Instrumentation cost and measurement limitations

Two builds use identical selected IDs and deferred storage: `split` enables all
internal cuts; `light` sets `ASTRA_FRAME_BREAKDOWN=OFF`, retaining only selected
outer endpoints and the AGK edge capture. The latter is **not fully uninstrumented**.
The separate `off` runs disable the presentation trace too; campaign injection
remains ON only for campaign coverage. No exact per-frame timing is invented for
a fully OFF executable from window maxima.

| Campaign frame | A500 light → split target lines | Added lines | AROS light → split | Added lines |
|---|---:|---:|---:|---:|
| 751 | 329 → 382 | 53 | 299 → 353 | 54 |
| 2817 | 364 → 411 | 47 | 336 → 389 | 53 |
| 4879 | 359 → 406 | 47 | 333 → 385 | 52 |
| 6927 | 359 → 407 | 48 | 331 → 384 | 53 |
| **Mean** | **352.75 → 401.5** | **48.75 / 3.115 ms** | **324.75 → 377.75** | **53 / 3.387 ms** |

Ordinary954 light→split is330→384 A500 and309→362 AROS. The extra timestamps
materially perturb the selected frames and can change missed-vblank counts;
there is **no constant overhead subtraction** or claim that the larger split
totals represent a production regression. Even individual HUD/BOB intervals move
because later work starts at a different raster/interrupt phase.

Complete replay results below are **drops / peak load%**, with actual counted
frames and final partial windows. `OFF` means all timing/stress diagnostics OFF;
the campaign's state-injection flag necessarily remains ON for that fixture.

| Replay/profile | Frames / final window | Timing OFF | Light endpoints | Detailed split |
|---|---:|---:|---:|---:|
| Campaign A500 | 9172 /22 | **5 /115%** | 5 /118% | 5 /133% |
| Campaign AROS | 9172 /22 | **3 /107%** | 3 /109% | 4 /126% |
| Ordinary BOB A500 | 1247 /47 | **2 /107%** | 2 /110% | 5 /127% |
| Ordinary BOB AROS | 1247 /47 | **1 /100%** | 1 /103% | 3 /120% |

Each mode has identical completion IDs8925 (campaign) and1000 (ordinary BOB).
OFF reproduces the accepted it11b results exactly. The light trace itself adds
whole-run overhead; its per-frame values must not be called pure OFF timings.
Strict zero-drop/90% acceptance remains FAIL, as before.

All entries measure **elapsed intervals, not pure CPU time or isolated DMA
occupancy**. The CPU can stall behind bitplane, sprite, Copper, Blitter and Paula
DMA; music interrupts can occur in any interval. Sprite preparation measures CPU
stream construction, not sprite DMA; copper build is not Copper execution.
BOB elapsed time combines CPU setup, masked transfers and waits. Foreground
audio is not the entire audio subsystem. Injection and state-report intervals
include their serial/debug calls, but do not isolate serial transmission from
formatting/copying. Subtracting fixture cost cannot reconstruct an ordinary
six-kill frame: both state provenance and bus phase differ.

#### Validation and restored production

- All six campaign profile/mode runs pass functional, lifecycle, channel and
  source-pixel checks. All six ordinary BOB runs pass the source artwork and
  restoration verifier. Every run matches the retained accepted it11b captures
  and every emitted gameplay-state field: **348 complete-image comparisons and
  1764 state-record comparisons**, with zero differences (per mode/profile:
  campaign53 images/255 states; BOB5 images/39 states). This covers the requested
  campaign and ordinary contrast, not a rerun of every unrelated scenario.
- Host C1/1, existing Python108/108 with Python3.12, and new partition tests3/3
  pass. Exact native sums, nested nonoverlap and AGK prefix/target/suffix identities
  pass for all16 detailed selected-frame records; light identities pass too.
  `git diff --check` passes. No thresholds, goldens or gameplay tests were relaxed.
- Two invocation mistakes are retained, not disguised as native failures: the
  first Python run used system3.9 and its `ast.literal_eval` rejected the existing
  indented font fixture; unchanged tests pass on required3.12. The first ordinary
  validator invocation omitted required `--drop`/`--restored` arguments and exited2
  before validation; the runner restored OFF, then resumed from retained captures
  with the correct arguments. `commands.log`, `.tmp/frame-breakdown-run.log` and
  `prior_invocation_failure` preserve that history. No actual new functional,
  image, lifecycle or timing-accounting assertion failed.
- The serialized runner `.tmp/measure-frame-breakdown.py` rebuilt all flags OFF
  in `finally`. `CMakeCache.txt` confirms **CAMPAIGN_PROBE, COMBAT_STRESS,
  COMBAT_TIMING, PRESENTATION_TIMING and FRAME_BREAKDOWN all OFF**. The final
  501636-byte executable SHA256 is unchanged:
  `b105cfd770f07089252652179023771f8f93908066e705c1fb226d9e3e0b9c06`.
  Fresh fully-OFF ordinary replays booted that same executable on both profiles.
  Guarded instrumentation remains available; it has zero binary effect when OFF.
- Source SHA256s, full commit ID, per-mode executable hashes, complete window
  records, raw timestamps and equivalence results are retained in `report.json`.
  The pre-existing pending it8 tests/docs/admission harness remain preserved.
  No optimization, commit, GUI session or installed-kit change was performed.

### it11b — nested HUD and BOB measurements

**Measurement only, still HEAD `10f4f47`, isolated `astra-perf`.** This follows up
the preceding A500 HUD2.588 ms and BOB6.422 ms figures with new native samples.
No rendering algorithm, submission order, gameplay, wait placement or asset was
optimized. The new cuts and operation counters perturb timing, so their sums
are not forced to equal those earlier numbers.

Main finding: on each six-kill burst, **only score digits redraw in the HUD**;
there are **seven successful BOB submissions: six small explosions plus one
newly dropped bonus**, not six BOBs. The large BOB intervals are the effects
submission path and the common queue flush. Neither is pure effect-DMA time.

#### Measurement contract, source paths and execution validity

- Selected campaign frames751/2817/4879/6927 retain the same PLAY stage51 identity.
  Added7704 (ordinary report/BOSS tick86) and7780 (second-bitmap BOSS HUD return).
  Ordinary input-driven frames816/954/977/981 cover kills, wave spawn and pickup.
- `ASTRA_HUD_BOB_TIMING=ON` retains the HUD/BOB parent endpoints and extended
  campaign IDs. `ASTRA_HUD_BOB_DETAIL=ON` adds internal cuts and operation counts.
  The former with DETAIL OFF is the **light control**, not an uninstrumented
  executable. `ASTRA_FRAME_BREAKDOWN` is OFF in both modes to avoid running the
  earlier full-main-loop cuts. Fully OFF runs disable all timing diagnostics.
- Fixed storage: ten record slots,49 timestamp positions with explicit validity
  bytes,16 HUD operation counters and seven BOB category count/alignment pairs.
  Only selected frames read clocks. Counts use guarded increments, no per-entity
  clock reads, allocations or printing. The final F8 dump is deferred; the replay
  waits for its final marker **after** the completed performance boundary.
- `render_world.c`: `renderWorldHud` → `hudDraw`; its ordered blocks are DAMAGE,
  SPEED, SHIELD, FIRE, score, lives, charge labels/instructions, charge bar,
  boss label/bar, then physical-buffer history updates/return. `scoreDraw` nests
  `numberText` and counts actual changed digits, glyph draws and clear calls.
- `render_bobs.c`: HUD-end → BOB-call entry → boss queue → effects queue → pickup
  queue → shots queue → `bobEnd()` → the existing terminal `blitWait()` → close/
  return. `render_boss.c` and `render_effects.c` count **after** eligible `bobPush`
  calls; pickups/shots count after their actual push helpers. Rejected/offscreen,
  occluded and excess-lance objects are not counted. Seven categories are boss,
  small effect, hero effect, boss effect, pickup, normal shot and lance.
- No new flush or wait was inserted between categories. Earlier N−2 background
  restoration in `renderBobsBegin()` remains outside the BOB interval here.
- `tools/hud_bob_breakdown.py` requires the complete49/16/7 vectors, unique IDs,
  zero native bounds/duplicate faults and the exact executed timestamp set.
  A skipped formatter is **unmeasured/null**, not a zero-duration call. Light-mode
  operation counters are invalid/null, not evidence of zero work. A block with
  zero redraw operations still has a valid predicate/timestamp interval.
- The two partition identities are exact: sum(HUD blocks)=HUD-end−HUD-begin;
  sum(BOB blocks)=BOB-end−HUD-end. A separate disjoint outer partition is
  before-HUD + HUD + BOB + after-BOB = target. AGK's sampled prefix + target +
  suffix = whole also remains exact. Nested formatting is never added twice.

All timing below is **elapsed PAL raster lines**: ms=lines×20/313,
%20 ms=lines×100/313. Intervals include their diagnostic stores, CPU setup,
interrupts and chip-bus stalls; they are not isolated CPU cycles or DMA occupancy.

#### A500 HUD: ordered, disjoint blocks

Baseline hardware remains68000 7 MHz, OCS PAL,512 KiB CHIP +512 KiB slow.

| HUD block | 751 | 2817 | 4879 | 6927 | Mean lines | Mean ms | %20 ms | Actual work in these bursts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| DAMAGE counter / entry | 3 | 3 | 3 | 2 | 2.75 | 0.176 | 0.88% | Predicate only;0 redraws |
| SPEED counter | 2 | 2 | 2 | 2 | 2 | 0.128 | 0.64% | Predicate only;0 redraws |
| SHIELD counter | 2 | 2 | 2 | 2 | 2 | 0.128 | 0.64% | Predicate only;0 redraws |
| FIRE counter | 2 | 2 | 2 | 2 | 2 | 0.128 | 0.64% | Predicate only;0 redraws |
| **Score, inclusive** | **25** | **40** | **40** | **49** | **38.5** | **2.460** | **12.30%** | One format call;1/2/2/2 glyphs and clears |
| Lives | 2 | 2 | 2 | 2 | 2 | 0.128 | 0.64% | Predicate only;0 redraws |
| Charge labels/instructions | 2 | 2 | 2 | 2 | 2 | 0.128 | 0.64% | No label-pair blits |
| Charge bar | 2 | 2 | 2 | 3 | 2.25 | 0.144 | 0.72% | No clear/fill |
| Boss label/bar | 3 | 2 | 2 | 2 | 2.25 | 0.144 | 0.72% | No clear, label draw or fill |
| Physical history + return | 2 | 3 | 3 | 5 | 3.25 | 0.208 | 1.04% | CPU cache writes and return |
| **Exact HUD parent** | **45** | **60** | **60** | **71** | **59** | **3.770** | **18.85%** | Instrumented parent, not old2.588 ms |

The score dominates the **actual redraw work**, not every instrumented predicate.
The1–3-line inactive-block intervals must not be described as text/bar rendering
costs. Their timestamp/predicate overhead is a material fraction of the sample.

Nested within the score row, not additive to HUD:

| Score subinterval | 751 | 2817 | 4879 | 6927 | Mean lines | Mean ms | %20 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| Predicate/call/count setup | 2 | 2 | 2 | 2 | 2 | 0.128 | 0.64% |
| Eight-digit `numberText` format | 4 | 4 | 4 | 4 | 4 | 0.256 | 1.28% |
| Compare/history, dirty clears, glyph writes, return | 19 | 34 | 34 | 43 | 32.5 | 2.077 | 10.38% |
| **Inclusive score** | **25** | **40** | **40** | **49** | **38.5** | **2.460** | **12.30%** |
| Changed digits = glyph calls = clear calls | 1 | 2 | 2 | 2 | 1.75 | — | — |

Source sequence: convert eight decimal digits on the68000; compare against this
physical bitmap's eight cached characters; for each changed digit clear a6×7
rectangle to ink1 using the Blitter; `textDraw` waits for that blit, then applies
cached5×7 glyph masks with CPU byte writes across four interleaved CHIP planes.
The full48×7 score clear is not used in these dirty updates. The32.5-line row
does **not** isolate clears from glyph writing or CPU from Blitter waits.
The four numeric upgrade counters and lives use the same general number/text
writer when dirty. Charge labels are pre-rendered bitmap blits; charge and HP
bars use rectangular clears/fills. BOSS lettering uses the packed14 aligned
OR.L writes after its clear/wait, rather than the general glyph loop.

#### A500 BOBs: submission versus shared completion

| Ordered BOB interval | 751 | 2817 | 4879 | 6927 | Mean lines | Mean ms | %20 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| HUD return / BOB call setup | 3 | 2 | 2 | 3 | 2.5 | 0.160 | 0.80% |
| Boss eligibility/queue | 2 | 3 | 3 | 3 | 2.75 | 0.176 | 0.88% |
| **Effects queue** | **43** | **42** | **61** | **45** | **47.75** | **3.051** | **15.26%** |
| Pickup queue | 8 | 16 | 8 | 8 | 10 | 0.639 | 3.19% |
| Normal-shot/lance queue | 5 | 9 | 5 | 6 | 6.25 | 0.399 | 2.00% |
| **Common `bobEnd()` flush** | **45** | **43** | **39** | **38** | **41.25** | **2.636** | **13.18%** |
| Existing terminal `blitWait()` | 2 | 2 | 2 | 2 | 2 | 0.128 | 0.64% |
| Close queue / return | 2 | 2 | 2 | 2 | 2 | 0.128 | 0.64% |
| **Exact BOB parent** | **110** | **119** | **122** | **107** | **114.5** | **7.316** | **36.58%** |

Pinned ACE `game/vendor/ACE/src/ace/managers/bob.c` explains the boundary:

1. `bobPush` (lines221–228) enqueues unconditionally, then calls
   `bobProcessNext()` if the Blitter is idle. The measured application eligibility
   checks precede the push; the counter executes after it has returned.
2. `bobProcessNext` first saves pending backgrounds (lines315–367), with CPU
   pointer/modulo setup, internal waits and A→D Blitter copies. Until pushing is
   finished it returns before the masked drawing branch (lines369–371).
3. `bobEnd` (lines580–585) marks pushing finished and drains the shared queue.
   Remaining saves precede all masked draws. The latter use A mask, B image,
   C destination and D result, with the cookie-cut minterm (lines374–446).
4. The application's existing final wait completes the last launched operation.
   N−2 restoration already occurred earlier on the actual back bitmap.

Therefore effectsQueue3.051 ms includes effect frame selection, coordinates,
queue setup, opportunistic background saves and stalls. It is **not** the total
cost of drawing six explosions. The shared2.636 ms flush includes remaining
saves and masked drawing for **all seven objects**. Even a later pickup push may
advance an earlier explosion's save. No honest per-category complete drawing
time can be inferred from this unchanged asynchronous queue.

Actual successful pushes on **each** of the four frames, identical on AROS:

| Category | Pushes/frame | Source size | Non-16-aligned X | Save word-area | Masked-draw word-area |
|---|---:|---|---:|---:|---:|
| Boss | 0 | 64×48 | 0 | 0 | 0 |
| Small explosions | **6** | 16×16 | **6** | **768** | **768** |
| Hero explosion | 0 | 32×32 | 0 | 0 | 0 |
| Boss explosion | 0 | 64×48 | 0 | 0 | 0 |
| Newly dropped bonus | **1** | 16×16 | **1** | **128** | **128** |
| Normal shots | 0 | 16×4 | 0 | 0 | 0 |
| Charged lance | 0 | 16×10 | 0 | 0 | 0 |
| **Total** | **7** | Four planes | **7** | **896** | **896** |

The injected collision shots have been consumed by logic; the resulting bonus
is still drawn this tick. The fixture clears that pickup on the following
stage51-before-update hook, not before this stage51 image is rendered.

Word-areas are derived **offline** from observed successful pushes/alignment and
the actual ACE formulas: save width=`ceil(width/16)+1`; masked draw width=
`ceil((width+(x&15))/16)`; multiply by height×4 planes. Thus each small shifted
BOB covers128 word positions per operation. Each896-word destination area is
1792 bytes; this is neither measured DMA time nor total bus traffic. The six
explosions account for6/7 of these areas, not a proven6/7 of elapsed BOB time.

#### AROS supplement and ordinary/BOSS contrasts

AROS's additional fast RAM makes it supplementary to the baseline A500. These
are the same disjoint blocks, frame order751/2817/4879/6927:

| Block | Four AROS line samples | Mean lines | Mean ms | %20 ms |
|---|---|---:|---:|---:|
| HUD DAMAGE | 2/2/2/2 | 2 | 0.128 | 0.64% |
| HUD SPEED | 2/2/2/2 | 2 | 0.128 | 0.64% |
| HUD SHIELD | 2/2/2/2 | 2 | 0.128 | 0.64% |
| HUD FIRE | 2/2/2/2 | 2 | 0.128 | 0.64% |
| HUD score | 24/38/39/48 | 37.25 | 2.380 | 11.90% |
| HUD lives | 2/2/2/2 | 2 | 0.128 | 0.64% |
| HUD charge labels | 2/3/2/2 | 2.25 | 0.144 | 0.72% |
| HUD charge bar | 3/2/2/2 | 2.25 | 0.144 | 0.72% |
| HUD boss label/bar | 2/2/2/2 | 2 | 0.128 | 0.64% |
| HUD history/return | 2/2/2/6 | 3 | 0.192 | 0.96% |
| **HUD total** | **43/57/57/70** | **56.75** | **3.626** | **18.13%** |
| BOB call setup | 3/3/3/2 | 2.75 | 0.176 | 0.88% |
| Boss queue | 2/2/3/3 | 2.5 | 0.160 | 0.80% |
| Effects queue | 31/31/50/33 | 36.25 | 2.316 | 11.58% |
| Pickup queue | 6/6/6/6 | 6 | 0.383 | 1.92% |
| Shots queue | 5/5/5/5 | 5 | 0.319 | 1.60% |
| Common flush | 34/46/30/31 | 35.25 | 2.252 | 11.26% |
| Terminal wait | 2/2/2/2 | 2 | 0.128 | 0.64% |
| Close/return | 2/2/2/2 | 2 | 0.128 | 0.64% |
| **BOB total** | **85/97/101/84** | **91.75** | **5.863** | **29.31%** |

AROS score formatting is4 lines every sample; comparison/clear/glyph/return is
18/32/33/42 lines, mean31.25 /1.997 ms. Operation counts match A500 exactly.

| Contrast frame | A500 HUD / BOB lines | AROS HUD / BOB lines | Observed operations |
|---|---:|---:|---|
| Ordinary816, kill | 63 /59 | 61 /50 | One score glyph/clear; one small effect +3 normal shots |
| Ordinary954, wave tail | 57 /78 | 56 /63 | One score glyph/clear; one small effect +one bonus +4 normal shots |
| Ordinary977, pickup | 38 /47 | 36 /41 | **DAMAGE redraw only**;3 normal shots |
| Ordinary981, kill | 69 /53 | 62 /44 | Two score glyphs/clears; one small effect +2 normal shots |
| Campaign7704, BOSS tick86 | 22 /73 | 21 /69 | **No HUD redraw at all**; one64×48 boss BOB |
| Campaign7780, BOSS label return | 48 /73 | 46 /69 | One label clear/draw +one HP clear/fill; one64×48 boss BOB |

At977, the active DAMAGE interval is18 lines /1.150 ms A500 (17 /1.086 AROS).
At7780, the active boss-label/bar interval is28 lines /1.789 ms (26 /1.661 AROS),
including146×7 label clearing, packed lettering, HP width calculation and112×4
bar clearing/filling. BOSS submission/common flush is21/33 lines on both selected
A500 boss frames (20/31 AROS); the shifted boss has960 save and960 masked-draw
word positions. Charge-label/bar **redraws were not exercised** in these selected
frames; their predicate-only timings do not establish active-update costs.

An important elapsed-time caveat is visible at ordinary816: DAMAGE takes15 A500
lines despite **zero** redraws; AROS instead has14 lines in the inactive SPEED
block. Interrupt/bus phase can dominate tiny intervals. This is not evidence of
an expensive number renderer executing there, and no isolated IRQ duration is
claimed.

#### Light controls, whole-iteration edges and production OFF

Parent measurements from a matched light trace versus detailed trace. Each cell
is **light→detail raster lines**; no timing is normalized to the earlier run.

| Frame | A500 HUD | A500 BOB | A500 target | AROS HUD | AROS BOB | AROS target |
|---|---:|---:|---:|---:|---:|---:|
| 751 | 24→45 | 96→110 | 337→371 | 22→43 | 70→85 | 310→345 |
| 2817 | 38→60 | 109→119 | 371→403 | 36→57 | 70→97 | 344→379 |
| 4879 | 38→60 | 113→122 | 367→398 | 36→57 | 92→101 | 344→374 |
| 6927 | 38→71 | 110→107 | 366→396 | 36→70 | 89→84 | 342→371 |
| **Burst mean** | **34.5→59** | **107→114.5** | **360.25→392** | **32.5→56.75** | **80.25→91.75** | **335→367.25** |
| 7704 | 5→22 | 60→73 | 317→346 | 4→21 | 51→69 | 299→335 |
| 7780 | 30→48 | 59→73 | 301→333 | 29→46 | 49→69 | 292→322 |

Detailed cuts/counters add a net31.75 lines /2.029 ms per A500 burst and32.25
/2.061 ms on AROS versus this light control. The queue counters and timestamps
also change when the Blitter becomes idle: e.g. S4's BOB parent can get shorter
while its HUD gets longer. Do not subtract a fixed probe cost or assign the
flush to categories by proportional arithmetic. Light HUD/BOB means are2.204 /
6.837 ms A500; detailed means are3.770 /7.316 ms. Both differ from the prior
full-main-loop diagnostic's2.588 /6.422 ms for legitimate measurement reasons.

AGK edges stay explicit. A500 detailed burst identities are
`3+371+10=384`, `2+403+10=415`, `2+398+9=409`, `3+396+9=408` lines.
At7704 the regular-report prefix is included: `10+346+9=365` A500,
`10+335+9=354` AROS. The prefix is inclusive Begin/report bookkeeping, not
isolated serial cost. Record-copy/return work accounts for a measured suffix;
the post-End vblank wait and F8 final dump are outside the completed interval.

Complete replay controls, **dropped vblanks / peak load%**:

| Replay/profile | Actual frames / final window | Fully timing-OFF | Light parents | Detailed HUD/BOB |
|---|---:|---:|---:|---:|
| Campaign A500 | 9172 /22 | **5 /115%** | 5 /122% | 6 /132% |
| Campaign AROS | 9172 /22 | **3 /107%** | 3 /113% | 6 /124% |
| Ordinary BOB A500 | 1247 /47 | **2 /107%** | 2 /114% | 5 /125% |
| Ordinary BOB AROS | 1247 /47 | **1 /100%** | 1 /107% | 3 /118% |

Completion IDs remain8925 and1000. Campaign injection is enabled only for the
campaign fixture, including its timing-OFF control. These diagnostic overruns
quantify instrumentation impact, not a gameplay regression. Fresh timing-OFF
results exactly reproduce accepted it11b. The unchanged zero-drop/90% gate still
fails. No pure OFF per-frame values are inferred from aggregate windows.

#### Validation, reproducibility and final binary

- **All12 native profile/mode/replay runs pass functional checks.** Campaign
  source pixels, scene/death lifecycle and channel assertions pass; ordinary BOB
  artwork/restoration checks pass. Every complete image and emitted gameplay
  state matches accepted it11b: **348 image comparisons and1764 state-record
  comparisons**, no masks, ignored fields or golden updates.
- All20 detailed selected-frame records pass exact HUD/BOB/nested/outer sums and
  timestamp validity checks. Another20 light records pass parent and AGK edge
  identities. HUD operation vectors and all seven BOB count/alignment/work-area
  vectors are identical across profiles for all10 selected identities.
- C1/1 and Python3.12 **116/116** pass. New regression coverage includes invalid/
  missing/duplicate timestamps and vectors, native fault rejection, absent
  formatter validity, light counters reported as unavailable, and different
  save/masked alignment areas. A host test executes actual `scoreDraw` and BOB
  pickup/shot eligibility functions with counters enabled: unchanged digits do
  not draw, actual clear/glyph counts agree with spies, offscreen/invalid/hidden
  objects and excess lances do not inflate successful pushes. Existing source
  pixel oracles still pass with the diagnostic header compiled OFF.
- Runner `.tmp/measure-hud-bobs.py` serializes native commands and restores OFF
  in `finally`. `.tmp/finalize-hud-bobs.py` independently re-parses the retained
  serial evidence and asserts hashes, cross-profile counts and all flags. Final
  **all seven flags OFF**: COMBAT_TIMING, COMBAT_STRESS, CAMPAIGN_PROBE,
  PRESENTATION_TIMING, FRAME_BREAKDOWN, HUD_BOB_TIMING, HUD_BOB_DETAIL.
- Restored executable is the same **501636 bytes**, SHA256
  `b105cfd770f07089252652179023771f8f93908066e705c1fb226d9e3e0b9c06`.
  Fresh OFF ordinary replays booted that identical executable on both profiles.
  Native-measured source hashes, vendored ACE BOB sources and installed AGK perf
  source remain unchanged throughout the measurements. No unexpected functional
  or accounting validation failure occurred; no assertion was weakened.
- Evidence: `game/build/it11b-hud-bob-breakdown/report.json`, `commands.log`,
  `scenarios/`, and `{detail,light,off}/{campaign,bob_restore}/{a500,a500-aros}/`
  contain full windows, raw valid timestamps, operation vectors, complete
  captures/serial, executable copies, source hashes and final integrity results.
  `.tmp/summarize-hud-bobs.py` reproduces the tables from the report.
  Prior frame-breakdown evidence/tooling and unrelated pending it8 work are
  preserved. No optimization, GUI, commit, cleanup or paid generation was done.

### it13 — user-selected score A refined to A2

The user explicitly selected original A despite its known mean-load tradeoff,
prioritizing deadline gains. Original A was the fallback, not the older blitter
baseline. Fresh baseline controls and both refinements were measured on both
profiles; no B/source guard or combined change was applied. All earlier pending
diagnostics, tests, reports and rejected-trial evidence remain preserved.

| Variant | Ordinary BOB A500; AROS (drops/peak%) | Campaign A500; AROS | Decision |
|---|---|---|---|
| Fresh baseline | 2/107; 1/100 | 5/115; 3/107 | Control only |
| Original A, retained two runs | 1/106; 1/100 | 5/112; 3/103 | User-approved fallback, superseded |
| A1: non-inlined cell helper | 1/105; 0/99 | 5/111; 3/103 | Fully validated, superseded by A2 |
| A2: hoisted pointers/masks, explicit second byte, two runs | 1/104; 0/97 | 5/109; 3/100 | **Accepted and applied** |

All other ordinary drops/peaks remain unchanged. Original A→A2 campaign mean load
is34.688399→34.541212% A500 and33.404928→33.214130% AROS. AROS remains0.005451pp
above the fresh baseline mean, explicitly accepted under the deadline-first
selection. Both A2 runs reproduce every drop/peak; all full windows/tails count.

Actual68000 audit: HUD entry locals/saved registers return from48+44 bytes in
original A to12+40 in both refinements. A1 helper locals/saves are20+44; A2 is4+44,
with remaining mask spills. GCC unrolls A2, growing its helper308→1036 bytes.
Destination writes are bytes, glyph WORD/LONG loads are aligned, and no audited
module imports32-bit multiply/divide helpers. These are generated-code facts,
not isolated cycle measurements. Changed-score helper calls still add stack depth.

Final executable502740 bytes (+428 vs original A); startup free CHIP/total is
41104/49392 A500 and152248/1360128 AROS, 480 fewer total free bytes than original A.
No new cache/CHIP allocation; startup is not a worst-case memory bound. The
formatter, physical histories, sixth background column, hooks, one-wait batch,
dirty repaint, initial composition, gameplay and BOB order remain intact.

A1/A2 actual-source ASAN/UBSAN pixel oracles each pass2880 cell cases,5019 score
transitions and10038 unchanged redraws. Each native trial passes182 full-image
and908 state comparisons, C1/1 andPython3.12 116/116. Final exact ADF boots both
profiles with BOB source/restoration checks; all seven flags explicitly OFF.
Executable SHA256`3288785797373564ef654946f610163a33d406e084363e39dc7d7c9fa900bf6d`;
ADF SHA256`62456751103ec296e267a042f710a1145ca5e54d5b3a40c6745f7d8ab41f6878`.

Full per-run means, coverage, code/stack/memory tradeoffs, source hashes and open
gates: [dated report](score-A-refinement-2026-10-11-110133.md). Raw evidence and
candidate patches: `.tmp/score-refinement/`. Accepted source/build remain only
in isolated`astra-perf`, HEAD`10f4f47`; no main edit, GUI, commit or cleanup.
Global50fps, full ordinary campaign, real-hardware/OOM and formal memory/stack
proofs remain open.

### it12 — native score-cell and effect-source comparisons, baseline retained

Executed on isolated `astra-perf`, HEAD `10f4f47`, preserving the existing dirty
diagnostic/test/documentation baseline. Full dated results, repeated mean loads,
coverage, source hashes, actual 68000 audit and all pending gates are in the
[native comparison report](hud-bob-native-comparison-2026-10-11-102053.md).

| Trial | Ordinary BOB A500; AROS (drops/peak%) | Campaign A500; AROS | Decision |
|---|---|---|---|
| Fresh it11b baseline, two runs | 2/107; 1/100 | 5/115; 3/107 | Retained |
| A: opaque CPU score cells, two runs | 1/106; 1/100 | 5/112; 3/103 | Rejected under no-regression selection: reliable deadline gain, but campaign mean load rises to34.688399%/33.404928%; AROS GAMEOVER also rises |
| B: equal effect image/mask guard, two runs | 2/107; 1/100 | 5/115; 3/107 | Rejected: unchanged drops/peaks, tiny mixed mean changes; no credible overall timing gain |

All first-four ordinary peaks remain76/76/83/78% A500 and74/74/81/76% AROS,
with zero drops. A adds676 executable bytes and costs616 startup free bytes;
B removes124 executable bytes and restores104 startup free bytes. CHIP free
remains41104 A500 and152248 AROS. These are startup observations, not worst-case
bounds. The combined trial was not justified by the standalone prerequisites.

Each candidate/repeat passes182 full-image and908 state comparisons, C1/1 and
Python3.12 116/116. Actual integrated-source sanitizer oracles cover A's2880
cell cases/5019 score transitions/10038 unchanged draws and B's65617 queue
cases. Complete original replay accounting and strict zero-drop/90% gate remain
unchanged; strict campaign failures are expected performance failures only.

Only candidate-owned hunks were reversed. Before this publication note, all321
frozen files matched the initial dirty baseline. Final501636-byte executable
SHA256 remains`b105cfd770f07089252652179023771f8f93908066e705c1fb226d9e3e0b9c06`;
all seven ASTRA flags are explicitly OFF. Exact final ADF SHA256
`0f327e0e130edecb5f6807afc54a75c372949210bda450bd2add82fe5d7e344d` booted both
profiles with full BOB replay/source-restoration checks. Raw trials and rejected
patches remain in`.tmp/native-comparisons/`. No runtime optimization is selected;
global50fps remains blocked at the it11b baseline numbers.

### it10 — HUD trials and new measurement blocker

**Historical stop, subsequently resolved above.** This section preserves the
initial incomplete-window measurements and diagnosis; its unaccepted-candidate
status and hashes describe that earlier point, not the final selected runtime.

Work remains isolated on `perf/combat-loop`, HEAD `8171bfd`. Pending it8 docs,
tests and admission harness are preserved. No paid generation or GUI was used.

#### Stop condition: incomplete final performance window

Newly discovered **measurement-accounting defect**, not a new gameplay failure:
`perf-loop5-it9j-prod/a500/bob_restore/serial.txt` ends at line 208. Its last
`AGK perf frames=50` is line 193, after the frame953/stage213 kill report.
Frames954/stage214 (new wave), 961/stage221 (kill), 977/stage237 (pickup) and
981/stage241 (kill) are subsequently reported, then the final capture ends the
scenario without another perf report. These frames are absent from the aggregate
0/95%. The same omission affects candidate aggregation. A final partial-window
frame count is not exposed, so the exact missing denominator is **unknown**.

The ordinary diagnostic replay additionally flushes its trace with F10 after the
original assertions. It identifies frame816/stage116 as the original reported
95% peak (third kill: score300, 3 shots, 4 hostiles, 1 effect). Its identifier-only
trace measures 298 lines there. Later trace frames954 and977 exceed313 lines,
but instrumentation changes elapsed time and DMA/IRQ alignment: these are **not
proof of the corresponding OFF drop count**. They establish that the unreported
tail must be measured, not dismissed. Extended replay time is not counted as the
original scenario's timing.

Per the user's stop rule, no accounting correction was made and no optimization
was accepted. Proposed next correction: explicitly flush the final partial perf
window at the replay boundary, preserve its actual frame count, prevent duplicate
counting, and remeasure it9j and the candidate on both profiles. Audit the other
scenarios for the same missing-tail issue. Do not weaken thresholds or label the
current emitted-window aggregates as complete-run acceptance.

#### Exact event attribution and hardware-time recap

The retained it9j trace maps its seven A500 overrun frames to the following
identifiers. Canonical frame/phase/stage identities stay unchanged in it10c; no
preparation scheduling was changed. The final diagnostic checkpoints are enabled
only for 15 selected frame IDs; all other slow frames retain whole-frame records.
Both baseline and candidate campaign traces count **8974 iterations to flush,
15 targeted frames, 28 retained records, zero omitted**. No per-frame serial dump
is performed. The first exploratory split timed every combat frame and is kept
as exploratory evidence only.

The table reports elapsed **raster lines per selected call** (one call/frame),
baseline→candidate, not isolated CPU cycles or steady-state means. The final
baseline/candidate traces are `perf-loop5-it10-{base-targeted}` and
`perf-loop5-it10c-targeted`. The seven baseline whole-frame line counts come from
the older, lighter `perf-loop5-it9j-trace`; they are not checkpoint sums.

| Frame / event | it9j light total | HUD bounds it9j→it10c | BOB submission bounds it9j→it10c |
|---|---:|---:|---:|
| 751, S1 PLAY stage51, six kills, events66, six effects | 329 | 26→24 | 95→96 |
| 801, S1 HERO_DYING stage101, events6, hero effect | 353 | **115→46** | 33→30 |
| 1585, S1 HERO_DYING boss tick120, events6 | 358 | **92→36** | 71→72 |
| 2817, S2 PLAY stage51, six kills | 365 | 41→39 | 109→109 |
| 4879, S3 PLAY stage51, six kills | 361 | 40→38 | 112→112 |
| 6927, S4 PLAY stage51, six kills | 360 | 40→38 | 109→110 |
| 7780, S4 BOSS tick122, second bitmap after respawn, events0 | 340 | 68→69 | 61→60 |

- Four six-kill HUD calls: mean/max **36.75/41→34.75/39 lines**;
  candidate **11.10%/12.46%** of313 lines. Their BOB mean/max is
  **106.25/112→106.75/112 lines** (**34.11%/35.78%**). This trial does not solve
  that burst.
- Two S1 death HUD calls: **103.5/115→41/46 lines**, candidate
  **13.10%/14.70%**. Unchanged counters previously caused four clears, four
  number conversions and four glyph writes when only one counter changed.
- Four first-boss foreground frames1416/3487/5550/7597 retain HUD
  **69/68/68/68 lines** and BOB **80/80/80/85 lines** in both builds. Galaxy decode
  is zero; repair completion remains separated from foreground publication.
- S4 post-respawn redraw recreates the BOSS label/bar on the second bitmap;
  its HUD cost remains68–69 lines. Before that HUD, logic/fixture/audio/input
  span from restore-end to audio-end is117→109 lines. The targeted checkpoints
  do not isolate fixture copies from logic or foreground music from that span.
- Audio event calls on the seven frames are approximately13–15 lines when
  events66/6 fire, versus2–3 on the event-free resume frame. Sound ordering and
  event counts are unchanged. Paula IRQ execution is not isolated.

Hardware inspection: actual pinned ACE `bobPush` queues objects and may start a
save when idle; `bobProcessNext` saves **all backgrounds before drawing**, waits
internally, then issues masked A/B/C/D blits. `bobEnd` drains the queue. Thus BOB
elapsed time includes 68000 pointer/setup work, Blitter DMA, internal waits and
chip-bus contention. Effect sizes/counts/lifetimes remain16×16×6,32×32 hero and
64×48 boss; no queue item or restore order was removed. Boss first draw copies
576 mask words into the existing flash bitmap; it is a once-per-sector CPU CHIP
copy, not steady BOB DMA. The HUD uses CPU font-mask writes plus Blitter clears;
large elapsed HUD costs cannot all be attributed to glyph pixels alone.

Actual production68000 `numberText` audit shows the new narrow path uses
`MULU.W #0xCCCD` via a register, SWAP and word shifts, not DIVU or a32-bit helper.
The retained full-width path has register-count long shifts/subtractions and
stack spills; no large-score formatting shortcut is claimed. The frame-buffer
font writer, BOB implementation, audio and logic remain unchanged in it10c.

Instrumentation is material: for the seven mapped frames, final targeted baseline
totals355/374/369/377/372/371/353 are **11–26 lines above** the older light trace.
Do not subtract a fixed overhead to manufacture OFF timing; recording also adds
work after the last timestamp. This is attribution only. The production-OFF
binary is byte-identical before/after the diagnostic additions.

#### Bounded HUD trials — emitted complete-window results only

Ordinary lists are pause / transitions / GAMEOVER / manga / BOB. Numbers are
drops/peak%. The accounting blocker above applies to every acceptance claim.

| Trial | Ordinary A500 | Ordinary AROS | Campaign A500; AROS | Decision |
|---|---|---|---|---|
| it9j reference | 0/80,0/80,0/83,0/81,0/95 | 0/77,0/77,0/81,0/79,0/90 | 7/116;6/110 | Existing accepted runtime; timing coverage now qualified |
| it10 font-only | 0/80,0/80,0/83,0/81,0/95 | 0/77,0/77,0/81,0/79,0/90 | 7/115;6/107 | Rejected: no drop or ordinary peak improvement; removed |
| it10b independent counter dirtiness | 0/80,0/80,0/83,0/81,0/95 | 0/77,0/77,0/81,0/79,0/91 | 5/116;4/107 | Not selected: AROS BOB crosses90% |
| it10c independent dirtiness + narrow number formatting | 0/76,0/76,0/83,0/78,0/94 | 0/74,0/74,0/81,0/76,0/90 | 5/115;4/107 | **Unaccepted candidate, stopped for accounting defect** |

Candidate changes only `render_world.c`'s HUD work: each physical bitmap redraws
only changed upgrade counters, and values≤65535 use bounded word arithmetic.
All changed values still draw on the same iteration. Full-width scores retain
their existing formatting path. No presentation delay, collision postponement,
asset/galaxy write, effect-duration/count, health, firing or audio change.

Full comparison against it9j passes for every trial: per profile **38 ordinary
captures/198 states plus53 campaign captures/255 states**, totaling **182 full
captures and906 state records**. No masks, changed goldens or dynamic-phase
exclusions. Scene acknowledgements, simulation frame IDs and preparation lengths
match exactly; canonical re-alignment was unnecessary. All13 scene pairs,
campaign lifecycle, source effect/flash/F checks and ordinary source/restoration
checks pass. These checks validate functionality, not missing timing samples.

#### Preserved state and final OFF evidence

Current source is the **uncommitted it10c candidate**, not an accepted replacement
for it9j. Diagnostic code is guarded by PRESENTATION_TIMING, which is OFF along
with CAMPAIGN_PROBE, COMBAT_TIMING and COMBAT_STRESS. Final build is500708 bytes;
SHA256 `0404df1594d15ff58a7dce0210d20c6045b6c78013d0971fdd5c1eab659e415b`;
ADF `957a49e896133095db569631ff5c1449826c23d7e9669d4605190fa29c3a8878`.
`cmp` matches the measured it10c ordinary binary. Final OFF native BOB replay
passes on both profiles in `perf-loop5-it10-stop-final`; C1/1 and Python104/104
pass. New number tests cover all65536 narrow values,65536 boundary, byte counters,
decimal/uint32 wraps and100000 deterministic full-width values. Existing glyph
oracle now exercises all eight alignments and all inks for its representative
glyph. No allocation was added.

Patches are retained in `.tmp/it10-font-and-diagnostic.patch`,
`.tmp/it10b-dirty-and-diagnostic.patch`, `.tmp/it10c-blocked-candidate.patch`;
the new untracked `test_hud_numbers.py` remains alongside the candidate.
Evidence prefixes are `perf-loop5-it10{,b,c}-campaign`,
`perf-loop5-it10{,b,c2}-prod`, and the targeted/ordinary trace directories above.
The first font extraction test failure was corrected by including its helper;
the rejected helper was then removed. A shutdown-only trace flush was unsuitable
for a script ending at WIN and was corrected. One c-run was refused by the stale
ADF guard after a comment edit; `it10c2-prod` is its rebuilt replacement. Those
failed attempts remain retained, not reported as passing runs.

**Remaining gap, incomplete-window scope:** it10c still has5 reported A500 campaign
drops/115% (25pp above90), ordinary BOB94% (4pp above90), and AROS campaign4/107%.
The full-run gap is not yet known because final partial windows are missing.
After correcting accounting, next diagnosis is the four six-effect/score bursts,
the S4 second-bitmap boss HUD redraw with firing work, and ordinary wave-spawn /
pickup tail frames. No global50fps completion or accepted progress commit is claimed.

### it9 — fixed galaxy Step D: accepted at it9j

**Final measured decision: accept it9j for the approved visuals and no-regression
gain against it7.** Campaign is **7 drops/116% A500, 6/110% AROS**, compared with
it7's 8/116%, 7/112%. Ordinary BOB is **0/95%, 0/90%**, versus 3/114%, 2/107%.
All other ordinary scenarios remain zero-drop and below 90%. The original it9g
rejection and evidence below remain historical; the user approved continuing the
implementation loop rather than rejecting the galaxy visual itself.

#### Continuation attribution and accepted correction

The fail-closed `attribute-campaign-drops.py` comparison was run **before** the
sparse rewrite: it9g's additional A500 drops cluster in sector-2/4 boss-opening
repair windows, not full-image world composition. AROS adds three drops there
while removing one earlier PLAY drop. Whole 50-frame windows are coarse and can
contain multiple phases; they were kept mixed, not relabelled by final state.
Retained comparisons: `it9{g,h,j}-drop-attribution.json` under `game/build`.

1. **it9h sparse painting:** retain the exact quantization and all four images;
   index deduplicated nonzero spans per row. Ordinary-data payload falls
   **16682→10508 bytes**. Full/patch painting requires an explicit per-bitmap
   cleared-base flag and writes no zero spans. Scanned row metadata and off-patch
   spans count against the 64-op budget, including a refused row lookup; writes
   are bounded at 320 bytes, rows at eight. Source-derived full and masked patch
   oracles pass on all planes. Campaign improves to **10/116%, 8/113%** but still
   regresses, so sparse painting alone is not claimed to fix deadline crossings.
2. **Bounded diagnostic trace:** under existing `ASTRA_PRESENTATION_TIMING`, keep
   the first 32 ≥280-line frames and decoder cost, and emit only at acknowledged
   WIN. No per-frame serial output; overflow is explicit and was zero. In it9h,
   the sector-2 final patch/publication frames take **360/346 lines**, including
   **43 decoder lines**. Sector-1 first publication is 326 lines with 34 decoding.
   The final patch and first large BOB/HUD/sprite draw occur in the same frame.
3. **it9i/j separate work steps:** finish the last patch, retaining the complete
   old visible frame. On the next iteration, mark the repaired background ready,
   add foreground BOBs/HUD/sprites and publish one complete image. No timed idle,
   hidden window, removed work or simulation-rate change. The host regression
   executes the actual scene-close functions for both independently progressing
   bitmap histories and forbids repair calls in the foreground-ready step.
   it9j additionally charges metadata preflight before deciding to admit a row.
   The final trace has **no ≥280-line frame with galaxy decoding**, with no
   records omitted. OFF native runs, not this intrusive trace, establish acceptance.

`check-galaxy-trace.py` reproduces the diagnostic run and restores all flags OFF
in `finally`. Both it9i and it9j independently reproduce the OFF results below.
The prior candidate is preserved at `.tmp/it9g-preserved/it9g-code.patch`, with an
ownership manifest and source snapshot; prior it8 work is not folded into Step D.

#### Final profiler-OFF results (drops / peak%)

| Profile | Scenario | it7 | accepted it9j |
|---|---|---|---|
| A500 | Pause / clean transitions | 0/79, 0/79 | 0/80, 0/80 |
| A500 | GAMEOVER / manga | 0/85, 0/80 | 0/83, 0/81 |
| A500 | Ordinary BOB | 3/114 | **0/95** |
| A500 | Injected campaign | 8/116 | **7/116** |
| AROS | Pause / clean transitions | 0/76, 0/76 | 0/77, 0/77 |
| AROS | GAMEOVER / manga | 0/82, 0/78 | 0/81, 0/79 |
| AROS | Ordinary BOB | 2/107 | **0/90** |
| AROS | Injected campaign | 7/112 | **6/110** |

The +1 pp ordinary peaks are retained explicitly; all remain under the budget.
This accepts the requested no-extra-drops step and ordinary BOB gain, not a
blanket claim that every peak decreases or the full 50fps problem is solved.
Final OFF attribution has no extra drops in the boss-opening repair windows.
Remaining dropped windows are PLAY firing/effects and death/resume transitions.

#### Latest raw-cost/hardware recap — it7 → it9j

A500 sector-1 dense across the same left/centre/right bands. Mean per frame / max
single call in elapsed raster lines. Candidate percentages use 313-line/20 ms PAL.
Audio sums two foreground calls, waits three. Inclusive stages overlap; DMA bus
contention and IRQs are included. Timing ON is attribution only.

| Stage / hardware | PLAY it7 → it9j mean/max | it9j % mean/max | BOSS it7 → it9j mean/max | it9j % mean/max |
|---|---|---|---|---|
| Restore/world — CPU, Blitter, Agnus contention | 67.07/93 → 64.20/92 | 20.51/29.39 | 54.49/88 → 54.55/89 | 17.43/28.43 |
| Logic — CPU + bus/IRQ stalls | 134.01/467 → 134.06/471 | 42.83/150.48 | 69.06/205 → 69.88/205 | 22.33/65.50 |
| Audio foreground — CPU, not isolated Paula IRQ | 4.82/5 → 4.90/6 | 1.57/1.92 | 4.95/9 → 4.68/8 | 1.50/2.56 |
| Render inclusive — hardware below | 293.28/340 → 293.20/329 | 93.67/105.11 | 305.11/342 → 305.13/343 | 97.49/109.58 |
| BOBs — CPU setup, Blitter/internal waits | 167.41/201 → 167.42/201 | 53.49/64.22 | 204.52/239 → 204.68/242 | 65.39/77.32 |
| Sprite prep — CPU CHIP writes, not sprite DMA | 96.42/136 → 96.52/137 | 30.84/43.77 | 82.03/127 → 81.85/113 | 26.15/36.10 |
| Copper build — CPU CHIP writes | 13.79/30 → 13.85/34 | 4.42/10.86 | 3.57/9 → 3.60/9 | 1.15/2.88 |
| Publication — CPU palette/pointers | 10.86/18 → 10.79/17 | 3.45/5.43 | 10.61/27 → 10.77/34 | 3.44/10.86 |
| Explicit wait — overlapping Blitter completion | 5.27/9 → 5.34/12 | 1.71/3.83 | 5.19/12 → 5.17/25 | 1.65/7.99 |
| Injection — diagnostic CPU | 80.29/112 → 79.94/112 | 25.54/35.78 | 75.30/108 → 75.38/103 | 24.08/32.91 |

Matrix ON whole metrics: **6489/355→6307/353 A500**, **5501/324→5483/325 AROS**.
The AROS peak rises one point in this deliberately injected timing-ON stress;
acceptance uses OFF ordinary/campaign results. All 48 cases and 96 fenced events
per profile pass. Galaxy decode is absent from steady PLAY/BOSS. Dense PLAY
restore/world saves 2.87 lines; dense BOSS is essentially unchanged. No broad
steady CPU benefit is inferred from repair scheduling.

Raw ready-PLAY OFF windows: ordinary BOB A500 **73.00→67.33% mean** (150 frames
each), AROS **68.33→64.00%** (150 each). Campaign PLAY A500 **56.56→57.63%**,
AROS **54.22→55.13%** (450→400 frames). Reporting boundaries move with preparation,
so these are not identical simulation windows. All emitted windows, including
mixed/preparation windows, remain in the acceptance reports.

#### Final latency, resident memory, code and tests

- First-target cold composition (including existing story work) is **150/151/151/151
  ticks** by sector: **3.00–3.02 s**, both targets **6.00–6.04 s**. This improves
  rejected it9g's 6.16–6.60 s; S1 it7 remains faster at 5.24 s. There is no claim
  of equal cold latency: the new image adds **0.76 s** across the two S1 targets.
  Disk/OS loading and deliberate scene dwell are excluded. TITLE remains 104
  ticks/bitmap. S1 patch-close is **18 ticks/bitmap**, only one more than it7's
  17: **0.72 s** both versus 0.68 s. The extra tick does foreground work.
- Production executable **500380 bytes**, versus it7 487536 (**+12844**) and
  it9g 506060 (**−5680**). A500 free CHIP/total **41104/51416**, versus
  it7 51616/64072 (**−10512/−12656**) and it9g 34928/45736. AROS is
  **152248/1362152**, total −12656 versus it7. Startup readings are not formal
  high-water bounds. No RAM profile, allocation, framebuffer or timeout increase.
- The diagnostic A500 boot reports `code_flags=5` (PUBLIC|FAST, baseline slow
  RAM), `data_flags=3` (PUBLIC|CHIP), code address 12683812 and data address 100768.
  Thus the observed diagnostic code did **not** move into CHIP; ordinary asset
  data did spill into CHIP. This is direct evidence for that build, not a formal
  loader-placement proof for every environment. The sparse representation reduces
  that pressure by 6176 observed CHIP bytes versus it9g.
- Actual OFF 68000 audit (`perf-loop5-it9j-68000.txt`) has no 32-bit multiply/divide
  helpers in world/galaxy modules. Sparse writes compile to byte `MOVE`/masked
  `OR`; repeated spans may use compiler-generated `memset`. The row-stride
  calculation is a word multiply, not a `___mulsi3` call. No hidden CHIP image or
  full-screen copy is introduced. The retained ordinary bank is 10508 bytes.
- Host C **1/1**, Python **103/103** PASS; the final metadata-bound adjustment also
  passes all five focused galaxy/closure tests. Both profiles pass all ordinary
  lifecycle/source checks; all four native galaxies, paused backgrounds and
  repaired openings pass **352256 exact pixels/profile**. All **13 scene pairs**
  additionally pass **686080 source-exact pixels/profile**. Scrolling, Nebula bands,
  original TITLE plate/caption and BOB restoration pass on the final restored OFF
  ADF on both profiles. Full intentional-background captures were visually inspected.
- All four flags are OFF. Final executable SHA256
  `ae992e83537191ce340752f92b81469cf4d6eeb46ccd63e2356c7983cdd1904c` matches
  the tested ordinary production binary. Diagnostic trace functions/storage emit
  no production runtime code: OFF identity is unchanged after trace additions.
  Main worktree, pending it8 tests/harness/docs, paid APIs and GUI were untouched.

The persisted diagnostic runner was also executed as `perf-loop5-it9j-trace-runner`;
its final OFF ADF was freshly boot/source validated on both profiles in
`perf-loop5-it9j-final`. Final ADF SHA256:
`a648d146cb5da3f297ab2d5093ec302cd19253f74e6770bb4f2f5652687c42bf`.

Evidence prefixes: `game/build/perf-loop5-it9j-{prod,campaign,on,galaxy,scrolling,trace}`;
summary `perf-loop5-it9j-summary.json`, raw stage tables `it9j-stage-tables.md`.
**Remaining A500 gap: campaign 7 drops and 26 peak-load points; ordinary BOB zero
drops but 5 peak-load points.** AROS campaign still has 6 drops/110%. These remaining
limits, real-hardware verification, ordinary full-campaign clear and formal memory
bounds are not concealed by accepting Step D.

#### Historical it9g investigation (superseded by the acceptance above)

User-approved visual scope: four selected RD masters, fixed farthest layer and
36 remaining moving stars. No new paid generation, planet, firing/trajectory,
logic, wave, HP or audio changes. This is an **uncommitted candidate**, not the
selected runtime. HEAD remains `de9b415`; the pre-existing it8 docs, rule tests
and admission harness are preserved. No accepted-step commit was made because
the explicit no-extra-overruns condition fails.

#### Implementation and source validation

- Durable originals/prompts/seeds/task IDs/hashes/costs live in `game/art/galaxy`.
  Original batch USD 2.16, additional integration USD 0.00. Four selected jobs
  account for USD 0.72 within that existing batch, not a new charge.
- 256×128→320×160 floor-coordinate nearest neighbour; RGB gain 3/4, Nebula 1/2;
  effective sector ink 0 and live ink 4 are respected. Background inks 0–3 have
  bright plane-2 XOR partners 4–7. Global palette is unchanged. All four source
  masters and native derivatives were inspected; Citadel's distant round motif
  is retained. Foundry's warm source details become existing cool low inks.
- Independent row-plane RLE in ordinary data, 16,682 payload bytes. No heap,
  staging bitmap, framebuffer backreferences or steady-frame galaxy decoding.
  Zero planes are skipped only because the caller clears all planes first.
  Generated row costs admit ≤320 written bytes / ≤64 decode ops / ≤8 rows.
  Patch edges preserve outside bits; patch completion XORs `HISTORY.stars` after
  this bitmap's BOB cleanup. Partial cursors and dirty histories stay per bitmap.
- Preserve every step of the original 48-position LFSR/Y sequence; discard only
  `i%4==0`, compact 36 stars and clamp the last eight-star composition batch.
  Remaining periods/widths/staggers are unchanged. Latest trial visits only due
  star groups since each bitmap's last rendered byte-clock tick; host coverage
  crosses pause/resume, N−2 catch-up and 255→0 wrap.
- Independent PNG oracle tests all four full images, unaligned/clipped patch
  rectangles, all-plane exterior preservation, two differently progressing
  targets and actual production star functions. It independently counts RLE ops
  and emitted bytes rather than trusting generated cost metadata.
- Native ordinary source oracle: **352,256 exact corridor pixels per profile**
  across all four sectors at completed ticks 10/26, plus pause stability.
  First capture checks full width except the exact hero rectangle; second checks
  x<240 because the first six-enemy formation occupies the right edge. This is
  source validation, not a masked full-image equivalence claim. Opening closure
  precedes these captures, so each sector's repaired window is also checked.
- Scrolling validator now asserts coordinate-exact fixed PNG pixels and XOR
  partners instead of rejecting any static picture; three parallax groups pass
  with 8/8/6 samples. The old title assertion is corrected to source-exact title
  plate + font caption, not a blanket exclusion. Both 15,360-pixel Nebula-band
  checks still pass. BOB validator checks all 768 restored pixels and 256 drop
  pixels against the PNG/exact tick, including transparent artwork pixels.
- Campaign F-badge/shot transparency uses the exact fixture background at
  completed ticks 11/15/25. Opaque art checks remain unchanged. Both profiles
  pass all campaign scenes/deaths/flashes/visibility, including zero hidden
  bullets; ordinary pause, clean transitions, GAMEOVER, manga and BOB checks pass.

#### Trial table (drops / peak%, profiler OFF)

Ordinary columns are pause / transitions / GAMEOVER / manga / BOB. Native output
directories are `game/build/perf-loop5-it9{suffix}-{prod,campaign,on,galaxy}`;
the initial unsuffixed run is `it9`. Rejected attempts and logs remain available.

| Trial | Decoder / stars | Ordinary A500 | Campaign A500; AROS | Decision |
|---|---|---|---|---|
| it7 baseline | No galaxy, 48 movers | 0/79, 0/79, 0/85, 0/80, 3/114 | 8/116; 7/112 | Committed reference |
| it9 | Charge all four planes, two rows/call | 0/80, 0/80, 0/83, 0/81, BOB old-oracle failure | Not run | Too slow: 209 preparation work steps/bitmap, about 8.4 s both targets |
| it9b | Skip zero planes in byte charge | 0/92, 0/94, 0/86, 0/85, 1/106 | Not run | Preparation peaks regress |
| it9c | Four-row cap + direct full-row writes | 0/90, 0/98, 0/89, 0/89, 4/106 | Not run | Rejected |
| it9d | Generated costs + token-clipped masked patch path | 0/80, 0/80, 0/81, 0/81, 4/106 | 14/119; not run | Rejected; old F transparency oracle halted A500 validation |
| it9e | Constant-shape star triples | 0/80, 0/80, 0/81, 0/81, 4/106 | Not run | No ordinary improvement |
| it9f | Optimized decoder returns to eight-row cap | 0/80, 0/80, 0/81, 0/81, 1/106 | 12/120; 9/111 | Functional PASS both; campaign regression |
| it9g | Per-bitmap due-star catch-up | 0/80, 0/80, 0/81, 0/81, 1/106 | 12/120; 9/111 | **Not accepted**; same OFF results as it9f |

Latest ordinary AROS: **0/77, 0/77, 0/79, 0/79, 1/99**, versus it7
0/76, 0/76, 0/82, 0/78, 2/107. Thus BOB improves on both machines but campaign
adds **4/2 drops**, and A500 campaign peak rises **116→120%**. Ordinary +1 pp
peaks remain visible, even below 90%; this is not a universal improvement.

Actual timing-ON stress matrix it7→it9g: A500 **6489/355→6346/347**; AROS
**5501/324→5496/324**. Both complete 48-case inventories and 96 fenced events
pass. This is intentionally injected density, not ordinary acceptance.

#### it9 hardware-time recap

A500 sector-1 dense, same three X bands as the accepted it7 recap. Mean per frame
/ maximum call in **elapsed PAL raster lines**; candidate percentages are of 313
lines/20 ms. Audio sums two foreground calls, waits three. Inclusive rows overlap;
timing ON adds overhead and includes interrupts/DMA contention. Not pure CPU or
isolated Copper/Paula/Blitter occupancy.

| Stage / hardware | PLAY it7 → it9g mean/max | it9g % mean/max | BOSS it7 → it9g mean/max | it9g % mean/max |
|---|---|---|---|---|
| Restore/world — 68000, Blitter, Agnus bus | 67.07/93 → 64.64/97 | 20.65/30.99 | 54.49/88 → 54.73/80 | 17.49/25.56 |
| Logic — 68000 + bus/IRQ stalls | 134.01/467 → 133.56/476 | 42.67/152.08 | 69.06/205 → 69.54/200 | 22.22/63.90 |
| Audio foreground — 68000, not isolated Paula IRQ | 4.82/5 → 4.82/8 | 1.54/2.56 | 4.95/9 → 4.61/7 | 1.47/2.24 |
| Render inclusive — all render hardware below | 293.28/340 → 293.55/331 | 93.79/105.75 | 305.11/342 → 305.89/349 | 97.73/111.50 |
| BOBs — Blitter + 68000 setup/internal waits | 167.41/201 → 166.99/200 | 53.35/63.90 | 204.52/239 → 204.85/245 | 65.45/78.27 |
| Sprites — CPU CHIP writes, not sprite DMA | 96.42/136 → 96.76/128 | 30.91/40.89 | 82.03/127 → 82.07/121 | 26.22/38.66 |
| Copper build — CPU CHIP writes | 13.79/30 → 14.18/42 | 4.53/13.42 | 3.57/9 → 3.59/14 | 1.15/4.47 |
| Publication — palette/pointers | 10.86/18 → 10.84/34 | 3.46/10.86 | 10.61/27 → 10.63/16 | 3.40/5.11 |
| Explicit wait — overlapping Blitter completion | 5.27/9 → 5.28/30 | 1.69/9.58 | 5.19/12 → 5.16/7 | 1.65/2.24 |
| Fixture injection — diagnostic CPU | 80.29/112 → 79.92/113 | 25.53/36.10 | 75.30/108 → 75.00/105 | 23.96/33.55 |

Raw stable PLAY windows, profiler OFF (mean of emitted quantized load%, peak%, drops):

| Profile / scenario | it7 frames; mean/peak/drops | it9g frames; mean/peak/drops |
|---|---|---|
| A500 ordinary BOB | 150; 73.00/114/3 | 200; 66.50/106/1 |
| AROS ordinary BOB | 150; 68.33/107/2 | 200; 63.00/99/1 |
| A500 injected campaign PLAY | 450; 56.56/115/4 | 400; 57.50/117/5 |
| AROS injected campaign PLAY | 450; 54.22/106/4 | 400; 55.38/108/3 |

These are ready-PLAY-only whole windows, not equal simulation intervals: changed
preparation moves the fixed 50-frame reporting boundaries. They cannot establish
a like-for-like percentage speedup. Every emitted window remains in the original
reports; whole-campaign acceptance above does not discard preparations or mixed
windows. Raw stage means show only **2.43 lines** saved in dense PLAY restore/world,
not a solution to the dominant BOB/render cost.

#### Latency, memory and final validation

No new artificial wait, timeout or hardware change. `cut_work` is one less than
composition iterations. At 50 Hz, sector-1 opening goes from **131→160 ticks per
bitmap**: first target **2.62→3.20 s**, both targets **5.24→6.40 s**. Acknowledgement
is after publication, not before. Candidate sectors 1/2/3/4 take **160/165/154/163
ticks per bitmap**, so all both-target preparations stay **6.16–6.60 s**, below
seven seconds. This includes existing story composition, excludes deliberate
scene dwell and OS/disk loading. TITLE remains 104 ticks per bitmap. S1 opening
closure grows **17→31 ticks per bitmap** (0.68→1.24 s both targets). The galaxy
adds 30 S1 full-compose calls/bitmap while one star batch disappears. Decoder is
never called on ready steady PLAY/BOSS frames.

| Production measurement | it7 | it9g | Delta |
|---|---:|---:|---:|
| Executable bytes | 487536 | 506060 | +18524 |
| A500 free CHIP | 51616 | 34928 | −16688 |
| A500 total free | 64072 | 45736 | −18336 |
| AROS free CHIP | 152248 | 152248 | 0 |
| AROS total free | 1374808 | 1356472 | −18336 |

The read-only payload is ordinary data but spills into CHIP on baseline A500.
No full CHIP galaxy allocation is introduced. Startup telemetry is not a formal
worst-case/high-water memory proof; AROS extra RAM cannot establish A500 fit.

Host C **1/1 PASS**, Python **101/101 PASS**, build and `git diff --check` PASS.
Four diagnostic flags are OFF. The restored OFF production is boot/source checked
on both profiles (`perf-loop5-it9g-scrolling`); it is a **functional candidate**,
not performance-approved shipping output. Source-derived all-sector checks are
`perf-loop5-it9g-galaxy`; ordinary/campaign/ON evidence is under the same prefix.
`perf-loop5-it9g-summary.json` and `it9-stage-tables.md` retain derived values;
`report-galaxy-performance.py` regenerates the summary from raw evidence.
Actual 68000 audits are `perf-loop5-it9g-{68000,galaxy-68000}.txt`.

Failures were kept visible: missing local Pillow was avoided through the stdlib
PNG/RGB-extraction pipeline; the Amiga data attribute is guarded for host Mach-O;
the title harness rejects galaxy calls in TITLE; BOB module loading uses its local
oracle path. The initial tick-11 native expectation was corrected to completed
scanout tick 10 (tick 26 for the second capture), with exact full-source agreement,
not a tolerance search in the validator. Old flat-background tests were replaced
with coordinate-exact expectations. No shared golden was refreshed. The it9d
matrix tool timed out in its final rebuild: OFF was immediately rebuilt explicitly;
the final it9g runner completed both profiles and its `finally` restoration.

**Remaining gate:** candidate A500 campaign still needs **12 drops removed and
30 percentage points** of peak load removed to reach 0/90; ordinary BOB needs
**1 drop and 16 points**. This is worse than it7's campaign gap (8 drops/26 points),
so the candidate is **not commit-ready** despite requested visuals working and
ordinary BOB gains. The exact cause of the changed campaign deadline crossings
is not established; changed preparation/report/audio alignment is a hypothesis,
not permission to dismiss the regression. Real-hardware timing, full ordinary
campaign clear and formal memory bounds remain unproven.

## Optimization loop 3 (HEAD `3aae85b`): per-iteration table

All runs use the identical fenced matrix (timing ON and OFF), the ordinary
production scenarios and the profiler-OFF injected campaign, with full images
compared fail-closed. Baselines: `perf-loop-base-{on,off,prod,campaign}`.

| Iteration | Change | Pixels/states | Logic mean/max, A500, ON (sparse; dense) | OFF matrix drops/peak (A500; AROS) | Decision |
|---|---|---|---|---|---|
| Base | HEAD | reference | 36.20/130; 105.71/589 | 5807/361%; 5270/339% | reference |
| it1, it2 (crashed session) | Code not retained in the tree | 96/96 images identical in both | it1: BOB stage +116%; it2: logic −0.9% | it1 5925/355%; it2 5729/350% | Not accepted; the code is not recoverable, so not re-evaluated |
| **it3** (logic.c, all three parts) | `staysApart` takes candidate fields in registers; pointer-walk scan skips the candidate via channel 0; per-tick free-slot cursor shared by `fireHostile`/`fireFan`/`bossVolley` | 96/96 images ON and OFF, both profiles; ordinary 38 captures + 194 states, and campaign 53 + 249, identical | 36.28/148; 105.17/547. Firing PLAY spikes 497→448 and 589→536; **non-firing PLAY dense +2.2 lines** | **5844/341%**; 5209/320% | **Rejected.** A500 OFF drops rise (+37) despite the peak −20 pp; campaign A500 is unchanged at 17/122%. AROS ordinary means rise slightly. |
| it3b | Free-slot cursor only | 96/96 images ON, both profiles | 36.64/157; 106.10/579 | not run (ON already worse) | **Rejected.** The cursor makes `fireFan` out-of-line and the cursor address-taken, which causes the +2-line non-firing regression. |
| it3c | Register `staysApart` + pointer scan only, no cursor | A500 48 images ON identical; **AROS run not executed** | 35.88/139; 104.74/578 (no left regression) | not run | **Unvalidated, reverted.** The run was blocked by a concurrent session (see below). It is the most promising candidate; the patch is retained. |

Equivalence review of it3 (all parts):
- `staysApart`: `dy = e.y − o.y` replaces `d0 = 2·dy`. The comparisons halve
  exactly. `d1 = 2dy + Δvy·t`, with |Δvy| ≤ 4 and t ≤ 219, cannot overflow int16.
  The redundant `d0 ≥ need` term is already implied by the earlier test.
- Skipping the candidate through channel 0 is equivalent to `o == e`. The
  original `default: continue` already skipped any other active channel-0
  hostile, so equivalence does not depend on others never having channel 0.
  This also holds for the `scheduleBullets` re-admission caller.
- Cursor: within one `updateEnemies` or `bossVolley` call, only firing activates
  hostile slots. The only deactivation is a rejected candidate, and the cursor
  stays on that slot. Slots below the cursor therefore stay active, so the slot
  chosen equals `spawn()`'s first free slot.

The new host test `testSameTickFansFillLowestFreeSlots` fires two gunner fans
in one tick, with a refused centre ray and interleaved pool holes. It passes on
HEAD and on the candidate, and fails on a deliberately broken cursor.

Retained patches: `.tmp/perf-loop-candidates/{it3-full,it3b-cursor-only,it3c-register-admission}.patch`.
Evidence: `game/build/perf-loop-{it3v-on,it3v-off,it3b-on,it3c-on}` and the
crashed session's identical-binary runs `perf-loop-it3-{prod,campaign}`. The
it3v OFF matrix reproduced those runs' figures exactly.

**Blocking condition:** at 14:21, a concurrent session in this same worktree
modified `game/src/main.c` (F9 ending preview) and added
`game/tests/native/ending_preview.agk`. It also ran its own emulator against the
shared `game/build`. The AROS step of it3c was refused by the stale-ADF guard.
The production build restored by the runner (488512 bytes) contains that
session's `main.c` and it3c. It is **not** a validated release build. Production
must be rebuilt with flags OFF and boot-validated after that session finishes;
the HEAD production executable is 488176 bytes. The CMake cache shows all four
diagnostic flags OFF.

## Final accepted changes and production evidence

1. `render_bullets.c`: rolling gather bit and 128-byte survivor bit lookup remove
   register-count membership shifts, retaining order, admission and visibility.
2. `render_world.c`: two physical-bitmap dirty bytes avoid repeated comparisons of
   96 frozen star coordinates, retaining each bitmap's first N−2 catch-up.
3. Non-shipping guarded stage profiler and deterministic stress/capture fixture;
   host tools retain raw JSON, hashes, comparison identities and derived tables.

No art, balance, quantities, audio, production pause or publication rules changed.
No additional hotspot was attempted: the credible measured gains remain modest,
and the next dominant BOB/admission work needs its own bounded investigation.

### Profiler-OFF ordinary production: baseline → final

Each row uses identical ordinary input and source/lifecycle validators. Mean load
is the weighted mean of **quantized AGK load percentages**, not raster-stage cost.
The full 50-frame windows are preserved, including preparations and transitions.

| Profile | Scenario | Drops | Peak % | Mean load % | Functional / full pixels / states |
|---|---|---:|---:|---:|---|
| A500 | pause_continuity | 0 → 0 | 90 → 90 | 23.926 → 23.296 | PASS / identical / identical |
| A500 | clean_transitions | 0 → 0 | 90 → 90 | 22.895 → 22.789 | PASS / identical / identical |
| A500 | gameover_title | 0 → 0 | 92 → 92 | 32.288 → 32.119 | PASS / identical / identical |
| A500 | large_manga | 0 → 0 | 92 → 92 | 22.955 → 22.864 | PASS / identical / identical |
| A500 | bob_restore | 7 → 7 | 116 → 117 | 34.500 → 34.250 | PASS / identical / identical |
| AROS | pause_continuity | 0 → 0 | 88 → 88 | 23.481 → 23.037 | PASS / identical / identical |
| AROS | clean_transitions | 0 → 0 | 88 → 88 | 22.579 → 22.632 | PASS / identical / identical |
| AROS | gameover_title | 0 → 0 | 89 → 89 | 31.373 → 31.237 | PASS / identical / identical |
| AROS | large_manga | 0 → 0 | 89 → 89 | 22.364 → 22.409 | PASS / identical / identical |
| AROS | bob_restore | 5 → 5 | 115 → 115 | 33.125 → 33.125 | PASS / identical / identical |

Production evidence: `game/build/perf-prod-{baseline,final}/{a500,a500-aros}`.
There are **38 complete captures and 194 gameplay-state records per profile**;
all compare exactly. Small increases remain visible: A500 BOB peak rises one
percentage point, and two AROS scenario means rise slightly. No universal
worst-case improvement or unchanged peak everywhere is claimed.

### Stage-profiler-OFF injected campaign: baseline → final

Campaign injection remains ON solely for accelerated coverage; stress and stage
profiler are OFF. This is **not an ordinary full-quota campaign clear**.

| Profile | Emitted frames | Drops | Peak % | Mean load % | Functional |
|---|---:|---:|---:|---:|---|
| A500 | 8750 → 8750 | **21 → 17** | 122 → 122 | **36.474 → 35.583** | PASS both |
| AROS | 8750 → 8750 | **15 → 12** | 119 → 119 | **35.234 → 34.354** | PASS both |

`perf-baseline-campaign` versus `perf-campaign-final`: all **53 full captures and
249 gameplay-state records per profile** are identical. Combined ordinary plus
campaign comparisons: **182/182 complete images and 886/886 state records**.
Campaign checks cover all four bosses/white flashes, effects, channel ownership,
zero hidden bullets, eight hero/four boss death pauses and 13 scene pairs. The
independent source oracle additionally passes **686080 native pixels per profile**
across all 13 scenes twice. Shared-image identity is not a substitute for those
source-derived and lifecycle checks.

### Corrected matrix iteration table

Only `perf-fenced-*` uses the final matched-identity capture protocol. Every
candidate below matches **96/96 full images** against the corresponding baseline,
for both timing ON and OFF; no masks or golden updates.

| Trial | A500 drops / peak | AROS drops / peak | Decision |
|---|---:|---:|---|
| Baseline timing ON | 9287 / 371% | 6208 / 349% | Attribution reference |
| Iteration 1 timing ON | 9273 / 370% | 6140 / 348% | Sprite-prep mean improvement |
| Iterations 1+2 timing ON | 8947 / 371% | 6054 / 355% | Restore/world mean improvement; ON peak is not consistently better |
| Baseline timing OFF | 5857 / 356% | 5379 / 340% | Same injection/capture, no stage counters |
| Iteration 1 timing OFF | 5799 / 355% | 5372 / 330% | Modest synthetic improvement |
| Iterations 1+2 timing OFF | 5807 / 361% | 5270 / 339% | A500 peak rises; acceptance relies on correctness and scoped campaign/ordinary gains, not blanket matrix superiority |

Corrected timing-ON dense sprite mean: A500 **103.608 → 101.235** after iteration1,
AROS **100.542 → 98.103**. After both changes, restore/world sparse/dense means:
A500 **56.031/81.406 → 48.421/73.779**, AROS **53.708/72.560 → 46.297/65.224**.
All individual sectors, bands, stages, maxima and sample counts are in the linked
tables and corresponding `*-stages.json` files.

**Instrumentation is intrusive:** corrected baseline ON adds **3430 A500 / 829
AROS drops** relative to OFF, and raises peaks by **15 / 9 percentage points**.
Repeated actor injection itself costs roughly 45 sparse / 77 dense lines on A500;
capture completion holds also remain in whole metrics. Neither synthetic ON drops
nor stage deltas alone prove production speedup. The ordinary and campaign OFF
measurements above provide the scoped runtime evidence. No window was hidden to
turn a budget result green.

### Final memory, artifacts and validation

| Build / profile | Executable bytes | Free CHIP | Total free RAM |
|---|---:|---:|---:|
| Baseline production A500 | 487888 | 51616 | 63432 |
| Final production A500 | **488176** | **51616** | **63152** |
| Baseline production AROS | 487888 | 152248 | 1374168 |
| Final production AROS | **488176** | **152248** | **1373888** |
| Final stress ON / timing OFF A500 | 490916 | 51616 | 60680 |
| Final stress ON / timing ON A500 | 492320 | 51616 | 59336 |

Accepted code costs **288 executable bytes / 280 observed total-free bytes**;
free CHIP is unchanged. Final profiler adds **1404 executable bytes / 1344
observed total-free bytes** over stress-only. Startup readings are not formal
worst-case memory bounds. There are no new frame-loop allocations.

- `game/build/astra`: **488176 bytes**, SHA256
  `879cb3d52e72055e47fa06af048b17aae17afe6588d7419b890562dd6b2f4ec5`.
- `game/build/astra.adf`: **901120 bytes**, SHA256
  `686944090703aaeb65eab8251c120f4cde6e7e2e34ab43735b634616a51823f8`.
- `ASTRA_COMBAT_STRESS`, `ASTRA_COMBAT_TIMING`, `ASTRA_CAMPAIGN_PROBE`,
  `ASTRA_PRESENTATION_TIMING`: all **OFF**, checked by final manifest generation.
- Final restored ADF additionally booted and passed opening/source/title-return
  checks on both profiles in `perf-final-adf-{a500,aros}`. Executable identity
  matches the fully tested ordinary-production build on both profiles.
- Host C rules **1/1 PASS**; Python suite **98/98 PASS**, including 15 new evidence
  validation tests. Original ACE PCM hash and
  all five music channel checks PASS. `git diff --check` PASS.
- Actual baseline/iteration1/final 68000 audit files are retained as
  `perf-{baseline,iteration1,final}-68000.txt`. Final evidence hashes and source
  identities: `perf-prod-final/final-evidence.json`.

Baseline production rebuilt with diagnostic hooks OFF has exactly the same
487888-byte executable SHA256 `d17ec043...` as before candidate edits. This supports
zero emitted diagnostic runtime code OFF; no pure hardware-cycle overhead claim
is inferred from source size alone. No GUI, commit, cleanup, hardware/timeout
increase, golden refresh or further speculative optimization was performed.

Remaining limits: strict global 50fps, a full ordinary native campaign clear,
real-hardware validation, formal memory high-water bounds, pure CPU-versus-DMA
attribution, and vendor-internal blitter wait isolation remain unproven. The
profiler retains all emitted windows but does not flush its last partial window.
Both changes are accepted for their measured scoped benefit and complete functional
equivalence, **not** as satisfaction of the unchanged global performance gate.

## Independent review finding — closed: fail-open evidence inventories

The review identified that the matrix inspector collected only captures that
existed, and comparisons could accept matching incomplete inventories or iterate
only the baseline's remaining scenarios. Negative tests reproduced the missing
evidence passes before correction. This was a host evidence-validation defect;
the retained successful runs already contained the full evidence.

`tools/combat_evidence.py` now supplies shared fail-closed inventory checks:

- Matrix inspection and comparison require **exactly** `case00.screen.png` through
  `case47.screen.png` on each side; missing, extra or empty files fail. Report
  capture hashes must match the actual files, rather than substituting for them.
- Require all **96 ordered case/tick events**, valid expected phase/sector and
  bitmap/copper identities, and increasing submission/acknowledgement/scanout
  clocks. Comparison also checks event manifests against actual serial records
  and requires equal case/tick/phase/sector/bitmap/copper identities across builds.
  Absolute vblank timestamps are intentionally not required to match.
- Production requires exactly the five known ordinary scenarios in both report
  manifests and directories. Each scenario, including the separate campaign,
  requires the exact nonempty capture set declared by its authoritative `.agk`
  fixture. Extras cannot be silently ignored and equally missing files fail.
- State evidence must be nonempty on **both** sides for every scenario, including
  campaign. Its definition remains complete `AGK frame=` gameplay records with
  wrapped continuation fields assembled by `frame_states`; QA, performance and
  completion markers are not gameplay-state evidence. This parser already rejected
  empty logs; mandatory scenario coverage now prevents bypassing it.

Validation after the fix:

| Check | Result |
|---|---|
| New evidence tests | **15 PASS**, covering complete input, one/both-side missing captures, all captures absent, incomplete manifests, missing/unequal events, extra captures/scenarios, omitted scenarios, empty/event-only state logs for all six scenarios |
| Complete Python suite | **98/98 PASS** |
| Retained matrix inspector `--check-only` | All six fenced builds × both profiles PASS: **48 files / 96 acknowledged events** in each profile |
| Retained candidate comparisons, iterations 1 and 2, timing ON and OFF | **96/96 full images identical per comparison**, matched event identities |
| Retained ordinary + campaign comparison | **182/182 complete images and 886/886 gameplay states identical** |
| Production flags / artifacts | All four flags still OFF; executable and ADF SHA256 unchanged |

Regression source: `game/tests/unit/test_combat_evidence.py`. Reinspection uses
`check-combat-performance.py --check-only --out game/build/perf-fenced-...`; it
does not build, launch an emulator, rewrite raw reports or alter flags. Both
comparison tools were rerun against the saved complete baseline/candidates.
No runtime/source-asset change, rebuild, emulator, golden update, commit or cleanup
was needed to close this finding. Performance results and remaining limits above
are unchanged.

## Measurement contract

`ASTRA_COMBAT_STRESS` and `ASTRA_COMBAT_TIMING` default OFF. The runner
`tools/check-combat-performance.py` restores all four diagnostic flags OFF in
`finally`. All allocation is static; no per-frame heap/OS calls are added.
`agkPerfBegin()` remains first and `agkPerfEnd()` remains before vblank waiting.
Aggregate serial reporting stays **inside** whole-frame measurement.

Stages use actual timer/raster counters, PAL 313-line wrap, raw call counts,
line sums and peaks. Means are sums divided by calls, never inferred from load
percentages. `render_inclusive` contains BOBs, sprite preparation, copper build,
HUD and composition. `explicit_wait` overlaps restore/BOBs and records only the
game's three instrumented `blitWait()` sites; ACE internal waits remain inclusive
in BOB work. Do not sum overlapping columns or call the remainder pure CPU time.
All stages include interrupts and DMA bus contention. Sprite preparation is CPU
stream construction, **not sprite DMA occupancy**; copper build/publication is
software work, **not copper bus occupancy**. Paula interrupt work is not isolated
by the foreground audio calls. These are emulator observations, not real-hardware
cycle accounting.

## Deterministic injected matrix

48 cases: four sectors × PLAY/BOSS × sparse/dense × left/center/right. Each case
runs 200 ready updates with all sixteen BOB alignments. X bases are 16/112/208,
plus tick modulo 16. Sparse/dense pre-update inventories: 1/6 gunner enemies in
PLAY, 2/24 corridor hostiles plus two partial-left retirement probes, 1/12 normal
shots, 1/6 small effects; BOSS replaces enemies with one boss. Channel-6/7 Y lanes
and actor types are identical across bands. Boss uses a fixed reference origin
across bands, with public sector motion retained. Public logic still processes
collisions, firing and trajectory admission. Every sixteenth tick requests a
volley using normal countdown logic. Left enemies are below the existing x>40
firing threshold: that real branch explains unequal admission work despite the
same supplied inventory. No production firing-rate change is involved.

The fixture resets pre-update state each tick; this is explicitly **injected**,
not an ordinary campaign or sustainable naturally occurring density. It does not
prove a reachable worst case. The repeated reset has its own measured cost.
The v1 exploratory run is retained under `perf-matrix-baseline-on`; v2 moves shot
lanes above the reference boss to avoid density-changing collision overlap.
Only v2 is the optimization comparison. Mixed/preparing windows remain in raw JSON;
the derived stable table excludes them with explicit first/last-case and busy tags.

## Baseline evidence

All paths below are under `game/build/`. Each matrix report retains every emitted
whole-frame window, raw stage counters, startup RAM, binary/ADF SHA256 and capture
SHA256. Derived per-case tables are `a500-stages.json` and `a500-aros-stages.json`,
generated by `tools/summarize-combat-performance.py`.

| Baseline | A500 drops / peak | AROS drops / peak | Functional scope |
|---|---:|---:|---|
| `perf-baseline-campaign` | 21 / 122% | 15 / 119% | Injected campaign PASS both, 53 captures each |
| `perf-matrix-v2-baseline-on` | 9003 / 373% | 5981 / 347% | 48-case injected matrix PASS both |
| `perf-matrix-v2-baseline-off-repeat` | 5700 / 362% | 5258 / 333% | Same matrix, stage timing OFF, PASS both |

The large matrix overruns include intentionally dense BOBs and injection work.
Instrumentation itself materially perturbs deadline crossings (+3303/+723 drops
and +11/+14 peak percentage points). Timing-ON is attribution, not production
acceptance. OFF still includes stress injection. The interrupted first OFF attempt
is retained in `perf-matrix-v2-baseline-off`: the outer shell's combined-command
wall-time limit interrupted it. Production was explicitly restored immediately;
the complete repeat uses unchanged emulator timeouts and hardware.

### Representative A500 raw stage mean / max raster lines

Sector 1 stable windows; all sectors and both profiles are retained in derived JSON.

| Phase / density / band | Restore+world | Logic | BOB inclusive | Sprite prep | Copper build | Publication | Explicit wait/call | Injection |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| PLAY sparse left | 66.35/100 | 38.33/44 | 34.53/62 | 40.11/75 | 14.08/29 | 10.32/15 | 1.94/29 | 44.68/54 |
| PLAY dense left | 92.46/124 | 121.29/128 | 169.10/203 | 110.93/135 | 13.99/52 | 9.97/16 | 1.60/7 | 79.27/84 |
| PLAY dense center | 91.71/101 | 145.07/499 | 169.00/200 | 110.64/142 | 13.83/34 | 9.93/15 | 1.62/6 | 79.19/113 |
| PLAY dense right | 92.01/120 | 144.29/480 | 169.07/196 | 110.81/140 | 13.95/30 | 9.92/16 | 1.66/7 | 79.19/107 |
| BOSS dense left | 70.83/80 | 70.53/187 | 208.11/240 | 96.25/121 | 3.57/9 | 10.25/16 | 1.56/7 | 75.21/103 |
| BOSS dense center | 70.99/99 | 70.03/187 | 208.62/232 | 96.29/125 | 3.63/9 | 10.08/13 | 1.62/2 | 75.29/107 |
| BOSS dense right | 71.05/80 | 72.27/217 | 210.57/241 | 96.21/128 | 3.64/9 | 10.21/16 | 1.66/5 | 74.78/84 |

### Memory and diagnostic overhead

| Build | Executable bytes | A500 free CHIP / total | AROS free CHIP / total |
|---|---:|---:|---:|
| Parent production | 487888 | 51616 / 63432 (parent validated) | 152248 / 1374168 (parent validated) |
| Stress ON, timing OFF | 489836 | 51616 / 61584 | 152248 / 1372320 |
| Stress ON, timing ON | 491300 | 51616 / 60184 | 152248 / 1370920 |

Static instrumentation adds 1464 executable bytes versus stress-only, and 1400
observed total RAM bytes. Both flags OFF reconstruct a 487888-byte executable;
fresh production validation and exact baseline identity checks follow iterations.
Startup free RAM is not a formal worst-case allocation bound.

## Iterations

### Approved capture correction trials

| Trial | Result | Decision |
|---|---|---|
| `perf-ack-*` | Activation-acknowledged case/tick/bitmap/copper matched, but iteration 1 had 4 A500 / 3 AROS differing captures | Insufficient: activation does not prove full scanout and host capture completion |
| `perf-scanout-*` | Full scanout fence reduced differences to 1 A500 / 2 AROS | Insufficient: next simulation/publication could still race the host screenshot command |
| `perf-fenced-*` | Full scanout plus explicit harness release after copying the capture; iteration 1 **96/96 full captures identical** at matching case/tick/bitmap/copper | Accepted fixture correction; no arbitrary wait, masks or golden changes |

The fixture remembers the submitted case/tick and physical bitmap/copper. At
actual vblank acknowledgement it checks those identities, retains the immutable
front submission until its full scanout completes, emits submission/ack/scanout
clocks, and holds the submission until the harness sends F10 **after** its image
copy. This is a diagnostic-only producer/consumer handshake, not production pause.
All held ticks and scanout fence costs remain in AGK whole metrics. Stage aggregates
cover work calls; capture-held ticks have no gameplay/render stage calls.

Corrected baseline/iteration1 ON matrix: A500 **9287/371% → 9273/370%**;
AROS **6208/349% → 6140/348%**. Dense sprite mean: **103.608 → 101.235**
A500, **100.542 → 98.103** AROS. These still do not establish ordinary runtime
benefit. Fresh ordinary production baseline (`perf-prod-baseline`) passes all five
source/lifecycle scenarios on both profiles; candidate comparison follows.

| Iteration | Evidence / decision | Status |
|---|---|---|
| Baseline | BOB inclusive is dominant sustained work; sprite preparation is ~111 PLAY dense / ~96 BOSS dense lines. Logic spikes reach 599 lines in sector 4 dense right. | Measured both profiles |
| 1 | Actual `perf-baseline-68000.txt` has register-count `lsll` at renderBulletsDraw +0x1d6, +0x242 and repeated survivor paths. Replaced index-dependent 32-bit membership shifts with a rolling gather bit and fixed bit lookup for survivors; preserved order, masks, visibility and stream ownership. | Native matrix functional PASS both; 96/96 complete captures byte-identical to baseline |

### Iteration 1 measured result

Evidence: `perf-iteration1-on/{report,comparison}.json`. Stable ready windows,
weighted by actual stage calls over all sectors/phases/bands:

| Profile / density | Baseline sprite mean lines | Iteration 1 | Change |
|---|---:|---:|---:|
| A500 sparse | 39.383 | 38.958 | −1.08% |
| A500 dense | 103.440 | 101.365 | −2.01% |
| AROS sparse | 38.381 | 38.028 | −0.92% |
| AROS dense | 100.545 | 98.123 | −2.41% |

Whole matrix ON: A500 **8956 drops / 373%**, AROS **5902 / 355%**.
AROS observed peak rises from 347% despite lower stage means/drops; no claim of
improved worst-case load or acceptance. Timing/OFF repeat and production checks
are needed to determine whether retaining this modest candidate is justified.
Production executable grows **236 bytes**, including a 128-byte read-only table.

Iteration 1 timing-OFF matrix: A500 **5652 / 355%** versus baseline **5700 / 362%**;
AROS **5243 / 333%** versus **5258 / 333%**. The higher ON-only AROS peak does not
persist with the profiler OFF. Retain provisionally for final production tests.

Iteration 2 candidate: `renderWorldAnimate` still scans 96 old/new star positions
on every frozen BOSS/death/pause frame. Actual 68000 object at `82ca` loads both
arrays, compares and branches, in a 48×two unrolled loop even when all match.
Add two per-physical-bitmap dirty bytes: mark both on star-coordinate changes,
clear only the bound back bitmap after catch-up. Preserve the first N−2 catch-up,
all pixels, the explicit wait, scrolling rates and buffer ownership. This targets
the measured BOSS restore/world mean (~46 sparse, ~71 dense), not BOB DMA itself.

### Historical iteration 2 result and mandatory stop — resolved above

Evidence: `perf-iteration2-on/{report,comparison,pixel-failure}.json`.

| Profile / density | Baseline restore/world mean | Iterations 1+2 mean | Change |
|---|---:|---:|---:|
| A500 sparse | 56.080 | 48.357 | −13.77% |
| A500 dense | 81.614 | 73.752 | −9.63% |
| AROS sparse | 53.649 | 46.418 | −13.48% |
| AROS dense | 72.558 | 65.263 | −10.05% |

These are weighted means across PLAY and BOSS, not isolated BOSS-only savings.
Whole timing-ON matrix: **A500 8734 drops / 369%; AROS 5865 / 348%**.
All 48 A500 full captures match baseline; **47/48 AROS captures match**.
The serial/visibility matrix checks passed on both, but the separate complete-frame
comparison failed and takes precedence over that narrower functional result:

```text
python3.12 tools/compare-combat-performance.py \
  game/build/perf-matrix-v2-baseline-on game/build/perf-iteration2-on
STOP: complete pixel identities differ; inspect before proceeding
```

AROS `case02.screen.png` (sector 1 PLAY, sparse, right) differs in **3253 pixels**,
bounding box **(0,29)–(319,211)**. The differences include the top scrolling decor
(rows 29–50), enemy/effect pixels (58–74), stars and partial-left bullet pixels.
Both full images were inspected; the discrepancy resembles a neighbouring display
tick, not solely missing frozen-star catch-up. That is a hypothesis, not a proven
explanation. Current `stress_case` is emitted after `renderFrame()` but **before**
`publishFrame()` and vblank acknowledgement. `run.retrosh` captures immediately on
that serial marker, so changed elapsed work can expose a different visible frame.
No screenshot masks or golden refresh were used.

**Precise proposed correction, not applied:** make fixture capture markers carry
the submitted case/tick plus actual bitmap/copper identity, and emit the capture
ready marker only after that submission's vblank acknowledgement. Preserve all
whole-frame performance windows and complete pixel comparisons. Repeat baseline
and both candidates with that identical publication-aware harness to distinguish
a sampling race from a renderer regression. If differences persist at identical
acknowledged identities, investigate/reject the two-byte dirty-star optimization.
Do not treat the present evidence as acceptance of iteration 2.

### Historical build state at the stop — superseded by final validation above

The runner restored production in `finally` before comparison. Cache verified:
`ASTRA_COMBAT_STRESS`, `ASTRA_COMBAT_TIMING`, `ASTRA_CAMPAIGN_PROBE` and
`ASTRA_PRESENTATION_TIMING` are all **OFF**.

| Artifact / build | Bytes | SHA256 or observed free RAM |
|---|---:|---|
| `game/build/astra` | 488176 | `879cb3d52e72055e47fa06af048b17aae17afe6588d7419b890562dd6b2f4ec5` |
| `game/build/astra.adf` | 901120 | `1652ed68a815f91c56667f49051c21458b990deae693b3e26ad1fc339f69570a` |
| Final timing+stress ON A500 | 491588 executable | 51616 CHIP / 59912 total free |
| Final timing+stress ON AROS | 491588 executable | 152248 CHIP / 1370648 total free |

Production executable growth versus parent: **288 bytes**. Iteration 2 adds two
static dirty bytes and 52 executable bytes versus iteration 1; observed diagnostic
free total memory decreases 40 bytes, CHIP is unchanged. The final OFF artifact
compiled successfully but was **not boot-validated after the pixel failure**;
it contains the unaccepted second candidate. It is not a validated release build.

No host rule/Python suite, final campaign rerun, ordinary production pause/BOB/
publication tests, iteration-2 timing-OFF matrix, or production timing acceptance
was run after the stop. The pre-change campaign covers all bosses, effects, death
pauses and stories functionally, but stage-resolved all-death/story and ordinary
production baselines remain unmeasured. The matrix pins pre-update clocks (including
the enemy accumulator); it is not proof of ordinary sector movement/cadence.
The last partial stage window is not emitted; every *emitted* stage and AGK whole
window is preserved. Foreground work and vendor-internal wait attribution remain
inclusive rather than pure CPU/blitter separation. Static instrumentation is
compiled out OFF; executable-size identity with the original 487888-byte baseline
was observed before optimizations, but no fresh OFF timing-overhead proof was run.

Global 50fps remains unmet. The requested stop on a new regression prevents
claiming final-production readiness or completion of the entire investigation.
