# Combat performance investigation

Baseline: parent commit `52a37a1`. Target remains PAL A500 7 MHz OCS,
512 KiB CHIP + 512 KiB slow, zero drops and <=90% peak. AROS is supplementary.

**Final: both bounded optimizations accepted; production ADF validated with all
diagnostic flags OFF.** The capture race is corrected with an acknowledged-scanout
handshake. All final baseline/candidate full pixels and emitted gameplay states
match. Global 50fps acceptance remains **FAIL**, with the unchanged thresholds.
Historical failed capture trials and the original stop remain recorded below.

Full numerical tables for all 48 cases, ten stages, both profiles and each
measured iteration: [raw-counter tables](combat-performance-tables.md).

## Recap: where frame time is spent and which hardware is involved

A500 sector 1, timing-ON fenced matrix, stable windows over the left/centre/right
bands. Each cell is the **mean per frame / max of one call** in elapsed PAL raster
lines (audio and explicit waits sum 2 and 3 calls per frame in the mean), with the
share of the 313-line (20 ms) frame. Baseline is `perf-loop4-it3c-on` (commit
`973a764`); latest is `perf-loop5-it6-on` (it6, 48 stars). Earlier loop-3 figures
used `perf-loop-base-on` (HEAD `3aae85b`) and per-call means.

| Stage | PLAY dense, baseline it3c | PLAY dense, latest it6 | BOSS dense, baseline it3c | BOSS dense, latest it6 | Hardware involved |
|---|---:|---:|---:|---:|---|
| Restore + world animate | 92.9/124 (29.7%/39.6%) | 67.3/101 (21.5%/32.3%) | 54.4/85 (17.4%/27.2%) | 54.3/82 (17.3%/26.2%) | Blitter restores; 68000 stars/decor; Agnus chip-bus contention |
| Logic, including admission and collisions | 135.9/471 (43.4%/150.5%) | 133.6/471 (42.7%/150.5%) | 70.1/200 (22.4%/63.9%) | 69.1/202 (22.1%/64.5%) | 68000 only (slow-RAM state); stalled by DMA and interrupts |
| Audio, foreground | 4.8/9 (1.5%/2.9%) | 4.9/5 (1.6%/1.6%) | 5.0/9 (1.6%/2.9%) | 5.0/9 (1.6%/2.9%) | 68000; Paula DMA and interrupts are not isolated |
| Render inclusive (contains the next four rows) | 307.2/353 (98.1%/112.8%) | 305.4/347 (97.6%/110.9%) | 318.0/362 (101.6%/115.7%) | 317.2/357 (101.3%/114.1%) | All of the below |
| BOB submission (ACE internal blit waits included) | 169.1/200 (54.0%/63.9%) | 167.5/202 (53.5%/64.5%) | 205.1/245 (65.5%/78.3%) | 204.8/244 (65.4%/78.0%) | Blitter, 68000 setup, chip-bus contention |
| Sprite stream preparation | 108.6/148 (34.7%/47.3%) | 108.3/142 (34.6%/45.4%) | 93.7/131 (29.9%/41.9%) | 93.8/133 (30.0%/42.5%) | 68000 writes to chip RAM; this is **not** sprite DMA time |
| Copper list build | 13.9/34 (4.4%/10.9%) | 13.9/49 (4.4%/15.7%) | 3.7/26 (1.2%/8.3%) | 3.6/7 (1.2%/2.2%) | 68000 writes; Copper execution is not measured |
| Publication | 10.6/38 (3.4%/12.1%) | 10.8/18 (3.5%/5.8%) | 10.9/33 (3.5%/10.5%) | 11.0/32 (3.5%/10.2%) | 68000, Copper pointers and palette |
| Explicit `blitWait()` (overlaps restore/BOBs) | 5.1/7 (1.6%/2.2%) | 5.2/7 (1.7%/2.2%) | 5.3/24 (1.7%/7.7%) | 5.2/19 (1.7%/6.1%) | Blitter completion |
| Fixture injection (diagnostic only, not shipped) | 79.5/107 (25.4%/34.2%) | 80.0/113 (25.6%/36.1%) | 75.1/107 (24.0%/34.2%) | 75.2/108 (24.0%/34.5%) | 68000 |

Stars move only while the world scrolls (PLAY); bosses freeze the scroll, so BOSS
restore/world cost is unchanged by the star count, as measured.

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
