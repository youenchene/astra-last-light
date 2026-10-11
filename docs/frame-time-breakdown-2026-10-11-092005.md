# it11b A500 frame-time breakdown — 2026-10-11 snapshot

- **Snapshot requested / clock recorded:** 2026-10-11 09:20:05 CEST (`2026-10-11T09:20:05+02:00`); UTC `2026-10-11T07:20:05Z`.
- **Document generation clock:** `2026-10-11T09:20:51+02:00` (CEST), recorded immediately before writing.
- **Measurement dates:** unknown. The timestamps above date this documentation snapshot, not the retained measurement runs.
- **Main workspace HEAD supplied for this snapshot:** `28b85f716a22596f67cad2b356250407c400bb33`.
- **Isolated evidence HEAD:** `10f4f477b3b3feb229dd42794588d3a021ea868a` (also recorded in both reports).
- **Evidence root:** `/var/folders/62/sj1vngrd76v9j3xk7v896j8w0000gn/T/opencode/astra-perf`.

## Scope and measurement integrity

This is a complete hierarchical account of the retained it11b **A500** measurements for frames **751 / 2817 / 4879 / 6927**, with an arithmetic mean over those four frames only. It is not a new measurement of the main workspace HEAD, a campaign-wide average, or a claim that performance acceptance passes.

Hardware and rendering stack: A500, 7 MHz 68000, OCS, PAL 50 Hz, 512 KiB chip + 512 KiB slow RAM; two 320×256×4bpp interleaved framebuffers; ACE BOB manager and blitter for BOBs; custom sprite DMA streams; Copper decor; Paula music/SFX. The budget is **20 ms per gameplay tick**, with the existing acceptance gate of zero drops and at most 90% peak load.

**Pass B does not contain the detailed outer-frame boundaries needed for a single-pass full hierarchy.** Its JSON and reparsed raw serial data agree: `FRAME_BREAKDOWN=OFF`, `HUD_BOB_TIMING=ON`, `HUD_BOB_DETAIL=ON`. Executed marks are 3, 4, 5, 7, 8 and 33–48 for each selected frame. Other zero-valued marks are invalid, not zero-duration stages. The available outer partition is only before HUD / HUD / BOBs / after BOBs.

- **A:** `game/build/it11b-frame-breakdown/report.json`, `split/campaign/a500`. Complete disjoint frame partition, including nested logic and the three sprite stages.
- **B†:** `game/build/it11b-hud-bob-breakdown/report.json`, `detail/campaign/a500`. Separate-probe HUD/BOB detail. **B† rows are non-additive with A and do not numerically decompose the A parent displayed above them.** Only children from the same pass sum to their own parent.
- Conversion follows `clockLines()` in `game/src/galaxy_trace.c`: **313 lines = 20 ms**; `ms = lines × 20 / 313`; `% of budget = lines × 100 / 313`. This is the trace clock's normalization.
- Instrumentation, fixture injection, checks and telemetry remain included. No estimated overhead has been subtracted. Stage timings are elapsed intervals, not exclusive CPU-cycle counts.

## Complete hierarchy

All line counts are four-frame means. Milliseconds and percentages are rounded only for display. Operation counts apply to pass B unless stated otherwise. The sprite parent is a grouping of three existing disjoint A segments, not an additional interval.

| Stage hierarchy | Pass | Mean lines | ms | % of 20 ms | Operations / technique |
|---|:---:|---:|---:|---:|---|
| **Instrumented frame — primary total** | **A** | **401.50** | **25.655** | **128.27%** | Complete partition; excludes AGK edges below |
| ├─ Start-of-frame bookkeeping | A | 10.50 | 0.671 | 3.35% | Initial controls and bookkeeping |
| ├─ BOB background restoration | A | 5.75 | 0.367 | 1.84% | Back-bitmap history |
| ├─ World animation | A | 25.00 | 1.597 | 7.99% | Background work after restoration |
| ├─ Music control | A | 3.00 | 0.192 | 0.96% | `campaignAudioUpdate`; not all Paula activity isolated |
| ├─ Input and simulation preparation | A | 5.00 | 0.319 | 1.60% | Read controls and preceding state |
| ├─ Test-fixture injection | A | 22.00 | 1.406 | 7.03% | `campaignProbeBeforeUpdate` |
| ├─ **Game logic** | **A** | **79.50** | **5.080** | **25.40%** | Exact sum of eight A children |
| │ ↳ Setup and hero | A | 6.25 | 0.399 | 2.00% | `logic_setup_hero` |
| │ ↳ Enemy spawn, movement and firing admission | A | 11.00 | 0.703 | 3.51% | `enemy_spawn_move_fire_admission` |
| │ ↳ Projectile movement | A | 9.00 | 0.575 | 2.88% | `projectile_movement` |
| │ ↳ Pickups | A | 2.00 | 0.128 | 0.64% | `pickups` |
| │ ↳ Collisions | A | 31.00 | 1.981 | 9.90% | `collisions` |
| │ ↳ Visibility scheduling | A | 16.50 | 1.054 | 5.27% | `visibility_schedule` |
| │ ↳ Boss-entry gate | A | 1.75 | 0.112 | 0.56% | `boss_gate` |
| │ ↳ Logic return | A | 2.00 | 0.128 | 0.64% | `logic_return` |
| ├─ Sound events | A | 14.50 | 0.927 | 4.63% | Audio event handling |
| ├─ Render setup | A | 4.50 | 0.288 | 1.44% | `renderFrame` entry to HUD |
| ├─ **HUD — primary-pass measurement** | **A** | **40.50** | **2.588** | **12.94%** | Included in total A |
| │ ↳ **HUD — separate-probe detail†** | **B†** | **59.00** | **3.770** | **18.85%** | Parent of the B† children below, not a child duration of A |
| │　↳ Damage / power indicator | B† | 2.75 | 0.176 | 0.88% | 0 graphical updates on each frame |
| │　↳ Speed indicator | B† | 2.00 | 0.128 | 0.64% | 0 graphical updates/frame |
| │　↳ Shield indicator | B† | 2.00 | 0.128 | 0.64% | 0 graphical updates/frame |
| │　↳ Fire-level F indicator | B† | 2.00 | 0.128 | 0.64% | 0 graphical updates/frame |
| │　↳ **Score** | **B†** | **38.50** | **2.460** | **12.30%** | 1 call/frame; changed glyphs only |
| │　　↳ Score setup | B† | 2.00 | 0.128 | 0.64% | Entry boundary to formatter |
| │　　↳ Score formatting | B† | 4.00 | 0.256 | 1.28% | 1 formatting call/frame |
| │　　↳ Dirty score drawing | B† | 32.50 | 2.077 | 10.38% | Changed glyphs, drawn glyphs and clears: **1 / 2 / 2 / 2** each; mean 1.75 each/frame |
| │　↳ Lives | B† | 2.00 | 0.128 | 0.64% | 0 graphical updates/frame |
| │　↳ Charge labels | B† | 2.00 | 0.128 | 0.64% | 0 label pairs drawn/frame |
| │　↳ Charge bar | B† | 2.25 | 0.144 | 0.72% | 0 clears, 0 fills/frame |
| │　↳ Boss label and bar | B† | 2.25 | 0.144 | 0.72% | Label clear/draw and bar clear/fill counters all 0 |
| │　↳ HUD history and return | B† | 3.25 | 0.208 | 1.04% | End of HUD processing |
| ├─ **BOBs — primary-pass measurement** | **A** | **100.50** | **6.422** | **32.11%** | Included in total A |
| │ ↳ **BOBs — separate-probe detail†** | **B†** | **114.50** | **7.316** | **36.58%** | Parent of the B† children below, not a child duration of A |
| │　↳ Call setup | B† | 2.50 | 0.160 | 0.80% | Entry to `renderBobsDraw` |
| │　↳ Boss submission | B† | 2.75 | 0.176 | 0.88% | **0 boss BOBs submitted**/frame |
| │　↳ Explosion submission | B† | 47.75 | 3.051 | 15.26% | **6 small 16×16 explosions**/frame, all unaligned; 0 hero explosions, 0 boss explosions |
| │　↳ Pickup submission | B† | 10.00 | 0.639 | 3.19% | **1 unaligned 16×16 pickup**/frame |
| │　↳ Player-shot submission | B† | 6.25 | 0.399 | 2.00% | **0 normal shots, 0 lances submitted**/frame |
| │　↳ Shared BOB queue flush | B† | 41.25 | 2.636 | 13.18% | `bobEnd()`; shared cost, not attributable per category |
| │　↳ Terminal blitter wait | B† | 2.00 | 0.128 | 0.64% | `blitWait()` |
| │　↳ Close and return | B† | 2.00 | 0.128 | 0.64% | Close the BOB frame |
| ├─ Display gate | A | 2.00 | 0.128 | 0.64% | `display_gate` |
| ├─ Copper decor | A | 3.25 | 0.208 | 1.04% | Decor update |
| ├─ Render pause handling | A | 2.50 | 0.160 | 0.80% | `pause` |
| ├─ **Hardware sprites — grouped stages** | **A** | **30.25** | **1.933** | **9.66%** | Sum of the next three stages |
| │ ↳ Hero | A | 11.25 | 0.719 | 3.59% | Attached sprites, channels 0–3 |
| │ ↳ Enemies | A | 7.25 | 0.463 | 2.32% | Attached sprites, channels 4–5 in PLAY |
| │ ↳ Hostile projectiles | A | 11.75 | 0.751 | 3.75% | Independent DMA streams, channels 6–7 in PLAY |
| ├─ Render return | A | 1.50 | 0.096 | 0.48% | `render_return` |
| ├─ Post-render processing | A | 2.00 | 0.128 | 0.64% | `post_render` |
| ├─ Fixture checks | A | 5.75 | 0.367 | 1.84% | `campaignProbeAfterFrame` |
| ├─ State report | A | 29.50 | 1.885 | 9.42% | `reportState` telemetry |
| ├─ Final blitter wait | A | 2.00 | 0.128 | 0.64% | `blitWait()` before publication |
| ├─ Publication | A | 10.00 | 0.639 | 3.19% | `publishFrame()` |
| └─ Trace tail | A | 2.00 | 0.128 | 0.64% | `trace_tail` |
| **AGK edges — outside primary total A** | **A** | **7.50** | **0.479** | **2.40%** | Prefix + suffix |
| ├─ AGK prefix | A | 2.50 | 0.160 | 0.80% | Before partition start |
| └─ AGK suffix | A | 5.00 | 0.319 | 1.60% | After partition end |
| **Complete AGK envelope A** | **A** | **409.00** | **26.134** | **130.67%** | 401.50 + 2.50 + 5.00 |
| **Independent cross-check: instrumented frame B†** | **B†** | **392.00** | **25.048** | **125.24%** | Separate pass; not additive with A |
| ├─ Before HUD, aggregate only | B† | 147.50 | 9.425 | 47.12% | Logic and preceding stages cannot be separated in B |
| ├─ HUD, repeated subtotal from above | B† | 59.00 | 3.770 | 18.85% | Same B measurement, not additional time |
| ├─ BOBs, repeated subtotal from above | B† | 114.50 | 7.316 | 36.58% | Same B measurement, not additional time |
| └─ After BOBs, aggregate only | B† | 71.00 | 4.537 | 22.68% | Sprites and following stages cannot be separated in B |
| **AGK edges — outside total B†** | **B†** | **12.00** | **0.767** | **3.83%** | Prefix + suffix |
| ├─ AGK prefix | B† | 2.50 | 0.160 | 0.80% | Measured in B |
| └─ AGK suffix | B† | 9.50 | 0.607 | 3.04% | Measured in B |
| **Complete AGK envelope B†** | **B†** | **404.00** | **25.815** | **129.07%** | 392.00 + 2.50 + 9.50 |

## Exact arithmetic checks

Python 3.12 calculations use the retained integer line counts before any display rounding. Vectors below follow frame order 751 / 2817 / 4879 / 6927.

- **A, 24 disjoint segments:** sums `[382, 411, 406, 407]` equal the recorded `lines` on every frame; mean **401.50**. The table groups three of these segments under sprites without adding a new interval.
- **A logic:** eight children sum to `[78, 80, 79, 81]`; mean **79.50**. Sprite children sum to `[29, 36, 28, 28]`; mean **30.25**.
- **A AGK:** prefixes `[2, 3, 3, 2]` + frame lines + suffixes `[5, 5, 5, 5]` equal `whole` `[389, 419, 414, 414]`; mean **409.00**.
- **B outer partition:** before HUD `[147, 147, 147, 149]` + HUD `[45, 60, 60, 71]` + BOBs `[110, 119, 122, 107]` + after BOBs `[69, 77, 69, 69]` equals `lines` `[371, 403, 398, 396]` on every frame. Means: **147.50 + 59.00 + 114.50 + 71.00 = 392.00**.
- **B HUD:** all ten immediate children sum to its recorded parent on each frame; mean **59.00**. Score children satisfy **2.00 + 4.00 + 32.50 = 38.50**.
- **B BOBs:** all eight immediate children sum to its recorded parent on each frame; mean **114.50**.
- **B AGK:** prefixes `[3, 2, 2, 3]` + frame lines + suffixes `[10, 10, 9, 9]` equal `whole` `[384, 415, 409, 408]`; mean **404.00**.

These identities are exact in lines. Rounded ms/% columns may show small apparent summation differences. There is no cross-pass identity between A's HUD/BOB totals and B's detailed children.

## Operation counts and interpretation

Each selected B frame has seven successful BOB submissions: six small explosions and one pickup, all with X unaligned to a 16-pixel word. Boss, hero-explosion, boss-explosion, normal-shot and lance submissions are all zero. Queue-stage time is **not exclusive drawing time for that object category**: ACE processing and the shared flush prevent that attribution.

`tools/hud_bob_breakdown.py` derives work areas from actual object geometry, four planes and successful-push/unaligned counts. Each frame has **896 word-plane units of save area and 896 of masked-draw area**: 768 for the six explosions, 128 for the pickup. These are calculated geometric work areas, **not durations or measured memory-transaction counts**. ACE saves an extra word even when aligned; masked width depends on X alignment.

Zero HUD graphical-operation counters do not imply zero time: dirty checks, control flow and instrumentation still run. Only the score performs counted graphical updates in these four B samples. Format calls are `[1, 1, 1, 1]`; changed glyphs, drawn glyphs and clears are each `[1, 2, 2, 2]`.

The music-control row measures its bounded main-loop interval, not an exclusive accounting of interrupt/DMA audio cost. Final blitter waits are included as shown; the vblank pacing wait after `agkPerfEnd()` is outside the reported AGK envelope.

## Performance status and related work

The retained HUD/BOB report's **OFF campaign A500 control** records **5 dropped frames, 115% maximum load, 9,172 measured frames, `pass=false`**. This is a separate whole-run control result, not the mean or maximum of the four instrumented rows above. It remains outside the acceptance gate. The documentation-only snapshot makes no performance improvement claim.

The previously quoted **13.8 ms residual** is historical context, not an updated it11b measurement. It is not inserted into this hierarchy, recalculated by mixing passes, or presented as a newly measured remainder.

For candidate changes and their trade-offs, see [HUD/BOB improvement options](hud-bob-improvement-options.md). That research document is maintained separately; the main-workspace copy is coordinated by the parent task. Options are not measured gains or implemented improvements in this snapshot.

## Retained evidence and reproducibility

Paths below are relative to the isolated evidence root recorded above; build artifacts need not exist in the main workspace:

- `game/build/it11b-frame-breakdown/report.json` — A: `split/campaign/a500.frames`.
- `game/build/it11b-hud-bob-breakdown/report.json` — B: `detail/campaign/a500.frames`; control: `off/campaign/a500.performance`.
- `game/build/it11b-hud-bob-breakdown/detail/campaign/a500/serial.txt` — reparsed with `hud_bob_breakdown.parse`; selected-frame stamps match the B report.
- `tools/frame_breakdown.py` — disjoint `CHAIN`, nested `LOGIC`, partition and AGK identities.
- `tools/hud_bob_breakdown.py` — valid-mark enforcement, HUD/BOB partitions, score subdivision, operation counters and geometric work areas.
- `game/src/galaxy_trace.c`, `game/src/main.c`, `game/src/render_bobs.c`, `game/src/render_world.c`, `game/AGENTS.md` — trace clock, execution boundaries, queue/flush order, HUD counters and hardware constraints.

This task stores the same English document in the main and isolated `docs/` directories. Verification compares their bytes, checks table conversions and source-derived arithmetic, and checks evidence references. No new measurement, runtime change, emulator session, build or commit is part of this documentation snapshot.
