# Native HUD / BOB A/B comparisons

> **Portable publication note:** All code, source hashes, build artifacts, test results and evidence paths in this report refer to the isolated checkout `/var/folders/62/sj1vngrd76v9j3xk7v896j8w0000gn/T/opencode/astra-perf`, branch `perf/combat-loop`, HEAD `10f4f477b3b3feb229dd42794588d3a021ea868a` (`10f4f47`), including its frozen uncommitted baseline. They do not describe or validate current main at `/Users/youen/.baton/worktrees/Shooter/west-pear`. Resolve code/evidence references against the isolated checkout; the sibling options and snapshot links are published context, while the it11b history link explicitly targets the isolated documentation because main's version differs. The original report timestamp and results are preserved. Statements that main was untouched describe the completed experiment before this documentation-only publication. Only this report is copied into main; no candidate, runtime artifact or raw evidence is integrated. Both report copies are byte-identical.

**Report timestamp:** 2026-10-11T10:20:53.098241+02:00. **Final selection: retain the frozen dirty it11b baseline.**

A and B were each integrated, cross-compiled and run natively twice on both profiles. Both pass functional equivalence. Neither is selected under the requested conservative no-regression requirement: A improves deadlines but consistently increases mean load; B does not change a drop/peak and its tiny mean differences do not establish a credible overall timing gain. No combined trial was justified. Global zero-drop / <=90% acceptance remains **FAIL**.

## Scope, frozen baseline and execution

- All authored files and retained evidence are in `/var/folders/62/sj1vngrd76v9j3xk7v896j8w0000gn/T/opencode/astra-perf` (macOS canonical path starts `/private/var`). Main `west-pear` was not modified.
- Branch `perf/combat-loop`, HEAD `10f4f477b3b3feb229dd42794588d3a021ea868a`. The baseline includes all pre-existing uncommitted diagnostics, tests and documentation. `baseline.json`, `baseline/`, `dirty-baseline.patch`, `status.txt` and `untracked.txt` under `.tmp/native-comparisons/` freeze 321 tracked/nonignored files and the initial binary/ADF/cache. Reversals removed only this task's candidate hunks; no HEAD restore/reset/clean was used.
- Initial and fresh OFF baseline executable: **501636 bytes**, SHA256 `b105cfd770f07089252652179023771f8f93908066e705c1fb226d9e3e0b9c06`.
- Native execution order: base, A, A-repeat, B, B-repeat, base-repeat, final OFF boot. Each complete trial runs all five ordinary cases and the injected campaign on A500 and AROS. Campaign is an injected fixture, not an ordinary campaign clear.
- Every build explicitly sets all seven flags: `CAMPAIGN_PROBE`, `COMBAT_STRESS`, `COMBAT_TIMING`, `PRESENTATION_TIMING`, `FRAME_BREAKDOWN`, `HUD_BOB_TIMING`, `HUD_BOB_DETAIL` (all prefixed `ASTRA_`). All OFF for ordinary/final; only CAMPAIGN_PROBE ON for campaign. Cache verification is independent of the existing runners' four-flag checks. Campaign `finally` explicitly rebuilds all seven OFF and the production hash must match.
- Compiler: `m68k-amigaos-gcc (AmigaDev) 6.5.0b 20260819091705`, Docker `amigadev/crosstools:m68k-amigaos`; Release, `-m68000 -msoft-float -fomit-frame-pointer -mcrt=nix13`. ACE BOB Y-wrap and pristine buffer are OFF. No hardware/profile, audio, pool or geometry change.

Related prior work: [options and host prototypes](hud-bob-improvement-options.md), [dated diagnostic snapshot](frame-time-breakdown-2026-10-11-092005.md), [it11b and earlier measurements](/var/folders/62/sj1vngrd76v9j3xk7v896j8w0000gn/T/opencode/astra-perf/docs/combat-performance.md#it11--physical-score-cache-and-packed-boss-label).

## Complete OFF timing: drops / peak load %

Every sample of every original replay, its final partial/full window and last-frame drops is included. F8 completion and the subsequent serial-drain hold are outside the completed replay; ordinary reporting overhead remains inside it. No padding, warm-up exclusion or time/pixel realignment was used. All six non-probe diagnostic flags are OFF even in injected campaigns.

| Profile | Replay | Base 1 | A 1 | A 2 | B 1 | B 2 | Base 2 |
|---|---|---:|---:|---:|---:|---:|---:|
| a500 | pause_continuity | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 |
| a500 | clean_transitions | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 |
| a500 | gameover_title | 0 / 83 | 0 / 83 | 0 / 83 | 0 / 83 | 0 / 83 | 0 / 83 |
| a500 | large_manga | 0 / 78 | 0 / 78 | 0 / 78 | 0 / 78 | 0 / 78 | 0 / 78 |
| a500 | bob_restore | 2 / 107 | 1 / 106 | 1 / 106 | 2 / 107 | 2 / 107 | 2 / 107 |
| a500 | campaign | 5 / 115 | 5 / 112 | 5 / 112 | 5 / 115 | 5 / 115 | 5 / 115 |
| a500-aros | pause_continuity | 0 / 74 | 0 / 74 | 0 / 74 | 0 / 74 | 0 / 74 | 0 / 74 |
| a500-aros | clean_transitions | 0 / 74 | 0 / 74 | 0 / 74 | 0 / 74 | 0 / 74 | 0 / 74 |
| a500-aros | gameover_title | 0 / 81 | 0 / 81 | 0 / 81 | 0 / 81 | 0 / 81 | 0 / 81 |
| a500-aros | large_manga | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 |
| a500-aros | bob_restore | 1 / 100 | 1 / 100 | 1 / 100 | 1 / 100 | 1 / 100 | 1 / 100 |
| a500-aros | campaign | 3 / 107 | 3 / 103 | 3 / 103 | 3 / 107 | 3 / 107 | 3 / 107 |

### Weighted mean load % — all windows, not just combat bursts

Mean = sum(window load% × actual window frames) / total frames. Window load is integer-quantized; these are not exact per-frame CPU times. Small ordinary A500 differences vary even with an identical executable. Repeats are retained rather than choosing the fastest one.

| Profile | Replay | Base 1 | A 1 | A 2 | B 1 | B 2 | Base 2 |
|---|---|---:|---:|---:|---:|---:|---:|
| a500 | pause_continuity | 23.460127 | 23.530699 | 23.636556 | 23.389555 | 23.318984 | 23.424841 |
| a500 | clean_transitions | 23.550000 | 23.450000 | 23.600000 | 23.500000 | 23.400000 | 23.550000 |
| a500 | gameover_title | 29.673215 | 29.689587 | 29.738703 | 29.640472 | 29.607728 | 29.673215 |
| a500 | large_manga | 22.855047 | 22.725626 | 22.855047 | 22.811907 | 22.725626 | 22.855047 |
| a500 | bob_restore | 32.585405 | 32.585405 | 32.705694 | 32.545309 | 32.465116 | 32.585405 |
| a500 | campaign | 34.568469 | 34.688399 | 34.688399 | 34.541212 | 34.557567 | 34.552115 |
| a500-aros | pause_continuity | 22.848271 | 22.895554 | 22.930840 | 22.883557 | 22.883557 | 22.848271 |
| a500-aros | clean_transitions | 22.800000 | 22.800000 | 22.800000 | 22.850000 | 22.850000 | 22.800000 |
| a500-aros | gameover_title | 28.820563 | 29.049771 | 29.049771 | 28.836935 | 28.836935 | 28.820563 |
| a500-aros | large_manga | 22.294219 | 22.294219 | 22.294219 | 22.337360 | 22.337360 | 22.294219 |
| a500-aros | bob_restore | 31.311949 | 31.392141 | 31.392141 | 31.352045 | 31.352045 | 31.311949 |
| a500-aros | campaign | 33.208679 | 33.404928 | 33.404928 | 33.203227 | 33.203227 | 33.208679 |

### Coverage and final boundaries

Counts below are identical for all six trials and both profiles. Each trial covers 34098 measured iterations and 688 windows across its twelve replay/profile runs.

| Replay | Measured frames | Final-window frames | Completion logic frame | Windows | Images/profile | States/profile |
|---|---:|---:|---:|---:|---:|---:|
| pause_continuity | 1417 | 17 | 1170 | 29 | 9 | 34 |
| clean_transitions | 1000 | 50 | 753 | 20 | 15 | 23 |
| gameover_title | 3054 | 4 | 2807 | 62 | 4 | 77 |
| large_manga | 1159 | 9 | 911 | 24 | 5 | 26 |
| bob_restore | 1247 | 47 | 1000 | 25 | 5 | 39 |
| campaign | 9172 | 22 | 8925 | 184 | 53 | 255 |

## Decisions and native-code findings

### A — opaque CPU score cells: rejected under no-regression selection

The actual production `render_world.c` candidate reused the existing font masks and formatter. Six-by-seven cells use byte RMW in all four planes, including the sixth background column. The first changed/dirty cell waits once for prior blits; unchanged redraws perform no wait or write. Full dirty redraw repaints all eight cells. Physical bitmap history, initial bounded composition, score timing hooks and successful glyph/changed counts are retained. Clear counters remain zero because no score clear blit runs.

Both repetitions reduce A500 ordinary BOB **2/107 -> 1/106** and campaign peak **115 -> 112%**; AROS campaign peak **107 -> 103%**. No drop/peak row increases. These are real whole-frame deadline improvements, not queue-only attribution. However, both campaign repeats increase weighted mean load to **34.688399% A500** and **33.404928% AROS**, and AROS GAMEOVER rises to **29.049771%**. Thus A is not a universal speedup or a no-regression replacement. It is retained as an explicit deadline-versus-throughput tradeoff, not silently promoted based only on its best metric.

Actual OFF disassembly in `A/68000.txt`: the cell is inlined into `renderWorldHud`. HUD function span grows **1984 -> 2596 bytes** (`0x898a..0x914a` versus `0x898a..0x93ae`). Local stack reservation grows **12 -> 48 bytes**; saved registers grow **40 -> 44 bytes**, giving **+40 bytes** of fixed entry stack usage. The row/byte loop spills glyph pointer, shift, masks, cell position and iteration state. Destination accesses at `0x8cc8..0x8d34` are byte MOVE/AND/OR operations; font LONG loads use aligned four-byte mask entries. No 32-bit multiply/divide helper is imported by the audited world/effects/BOB objects. Increased spills are observed; they are not claimed as an isolated causal timing measurement.

### B — equal effect source-pair guard: rejected as no credible overall timing gain

B was applied independently to the frozen baseline after byte-exact restoration of A. Only the existing `pFrameData` and `pMaskData` are compared before `bobSetFrame`. There is no added cache; each eligible object still receives its position stores and ordered `bobPush`, then its original `hudBobPushed` hook. Masks, old positions, save/restore histories, moving-star ordering and all fixed slots remain intact.

Both repetitions leave every drop and peak unchanged. Campaign mean differences are tiny; AROS ordinary means consistently increase slightly. The smaller binary and avoided setter calls alone do not establish a native frame-time benefit. No combined A+B run was performed because both components did not satisfy the credible-benefit/no-regression prerequisite.

Actual OFF disassembly in `B/68000.txt`: source LONG compares at `0x5b0` and `0x610` skip the setter only when both pointers match; both branches join the position stores at `0x5c4/0x5c8` and push at `0x5ce`. The effects queue span shrinks **816 -> 710 bytes**, and its baseline four-byte local spill slot disappears (same 44 bytes of saved registers). Aligned pointer fields and even position-word offsets are retained. No new arithmetic helper or persistent allocation.

## Size and observed startup free memory

Both repeats have identical executable hashes and memory readings for each candidate. Startup free memory is not a formal worst-case bound. AROS has additional fast RAM and cannot prove baseline A500 memory feasibility.

| Build | Executable bytes | Delta | A500 CHIP / total free bytes | AROS CHIP / total free bytes |
|---|---:|---:|---:|---:|
| base | 501636 | +0 | 41104 / 50488 | 152248 / 1361224 |
| A | 502312 | +676 | 41104 / 49872 | 152248 / 1360608 |
| B | 501512 | -124 | 41104 / 50592 | 152248 / 1361328 |

| Executable | SHA256 |
|---|---|
| base | `b105cfd770f07089252652179023771f8f93908066e705c1fb226d9e3e0b9c06` |
| A | `c78f6b5c1b0b313ed0f7ba432cd09610a57539223f9a6611c74b66cd1fec1898` |
| B | `b6f35eb09ac68c48e2287d8a1d8bc3d1698b62e30baf3928c05a4a6d28eb46fb` |

## Correctness, independent oracles and fail-closed checks

- Every candidate and repeat passes **182 full-image comparisons and 908 ordered gameplay-state comparisons** against the fresh baseline: per profile 38 ordinary images/199 states and 53 campaign images/255 states. No ignored state fields, masked pixels, golden updates or phase shifts. Native source artwork, restoration, scene/death lifecycle, F fixtures, boss flashes and zero-hidden-bullet checks pass.
- Complete-window parsing rejects missing/duplicate completion markers and inconsistent sample/drop totals. Capture inventories and ordinary replay text are checked fail-closed. The report generator additionally requires every exact frame/tail/boundary tuple in the coverage table. Fresh baseline self-validation establishes inventories only; candidate identity is measured against separate runs.
- Host C **1/1** and Python **116/116 under Python 3.12** pass for each of the six complete trials, including the actual current candidate source. A's two history/counter spies were adapted to opaque cells; actual raster semantics are covered separately by the independent oracle, not inferred from spies.
- A oracle compiles the actual integrated `scoreCellDraw` and `scoreDraw`, alongside the frozen production baseline, with ASAN/UBSAN. Independent source-font pixel painting verifies **252 mask rows, 2880 all-alignment/background cell cases, 5019 score transitions, 10038 unchanged redraws** across both nonalternating physical histories, carries, uint32/display wrap and dirty full updates. Whole 40960-byte buffers are compared, including exterior bits. One wait per nonempty batch and zero score clears are asserted.
- B oracle compiles the actual integrated queue against the frozen baseline. **65617 cases** cover all byte age/lifetime pairs, clamps, readiness, eligibility, all sizes, slot reuse, same-image/different-mask and converse pairs. Every ordered push's image/mask/X/Y matches and history sentinels remain unchanged. Controlled six-effect lifetime: **96/96 pushes, 96/42 setter calls, 192/84 pointer stores**. These are host operation counts, not native timing or a DMA simulation; real asynchronous restoration is validated by native runs.
- Oracle evidence: `.tmp/native-comparisons/{A,B}-oracle/` contains generated actual-source C, sanitizer executables, source hashes, commands and output. The older `.tmp/hud-bob-experiments/` prototype evidence is preserved unchanged.
- Every strict campaign command exits **1**, solely after separately passing functional and complete-accounting checks: the existing strict performance gate remains failed. No new functional, build, pixel, sanitizer or accounting failure occurred. No assertion or performance threshold was relaxed.
- Two invocation-only issues: the initial runner directory guard rejected `/private/var` versus `/var` before any build/test; it was reported then corrected to compare resolved paths. One summary was requested before B had written `trial.json`; it was rerun after completion. Neither was treated as a test pass or hidden native failure.

## Measurement limits

No new light/detail HUD/BOB trace was needed for the selection. There is no claimed per-score speedup in raster lines or category-specific BOB DMA saving. The complete OFF counters, not historical intrusive traces or host setter counts, control the decision. ACE may move opportunistic background saves from effect submission into the common flush; a shorter queue interval alone would not prove a gain. Native elapsed loads include CPU work, waits, DMA contention and audio interrupts; they do not isolate any one of those mechanisms.

## Final production, preservation and pending gates

**The final executable is the original it11b baseline; all seven flags are OFF.** The exact final ADF was then booted with the complete ordinary BOB replay on both profiles, without rebuilding between or after boots. Both pass independent BOB artwork/restoration checks, ten full-image comparisons and 78 state comparisons in total. Final-boot serial, performance, memory and artifact identity are in `.tmp/native-comparisons/final-boot/report.json`.

- Final executable: **501636 bytes**, SHA256 `b105cfd770f07089252652179023771f8f93908066e705c1fb226d9e3e0b9c06`.
- Final ADF: **901120 bytes**, SHA256 `0f327e0e130edecb5f6807afc54a75c372949210bda450bd2add82fe5d7e344d`.
- Before this report/publication note, all 321 frozen files match their initial dirty-baseline hashes exactly. The installed AGK perf source hash is unchanged. Candidate patches, source snapshots, builds, images, serial logs, memory, complete windows and actual 68000 dumps remain under each trial directory. No cleanup, GUI emulator, commit, paid generation or main-workspace edit occurred.
- **Completed:** authorized standalone A/B comparisons and repeats; both-profile ordinary/campaign functional checks; host suites and actual-source oracles; native audit; all-seven-OFF restoration and final both-profile ADF boots.
- **Not run by selection rule:** combined A+B. **Optional and not needed for this decision:** matched light/detail attribution. Neither is reported as a pass.
- **Still open:** global PAL 50fps (baseline campaign A500 5 drops/115%, AROS 3/107%; ordinary BOB A500 2/107%, AROS 1/100%), ordinary full-quota campaign clear, real-hardware verification, native allocation fault injection and formal worst-case free-memory bounds. Existing artistic acceptance is separate. No new allocation was added by either rejected candidate.

Reproduction scripts: `.tmp/native-comparisons.py`, `.tmp/native-oracles.py`, `.tmp/native-summary.py`, `.tmp/native-final.py`, `.tmp/write-native-report.py`. Use new trial labels for new runs; evidence directories refuse overwrites.
