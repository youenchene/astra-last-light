# Score candidate A: native refinement and acceptance

**Selected and applied: A2 — non-inlined opaque score-cell writer with hoisted plane pointers/masks and an explicit optional second byte.** Both-profile functional equivalence and repeated native deadline gains pass. Global PAL 50fps acceptance remains **FAIL**.

**Report timestamp:** 2026-10-11T11:01:33.361117+02:00.

> All code, hashes, measurements and evidence references describe only `/var/folders/62/sj1vngrd76v9j3xk7v896j8w0000gn/T/opencode/astra-perf` (macOS canonical prefix `/private/var`), branch `perf/combat-loop`, HEAD `10f4f477b3b3feb229dd42794588d3a021ea868a`, including its frozen dirty baseline and this uncommitted accepted A2 patch. This report does not measure or modify current main `west-pear`. Resolve relative code/evidence paths against the isolated checkout.

> **Publication scope:** Only this dated report is copied into main. The accepted A2 source and build remain in isolated `astra-perf`; A2 has not been ported to or applied to main runtime. References to “applied”, “ready” and an untouched `west-pear` describe the isolated refinement before this documentation-only publication. Both report copies are byte-identical; the original timestamp and measurements are preserved.

## Authorization and selection

The user explicitly selected **“go A”**, accepting original A's known mean-load tradeoff and prioritizing its actual deadline gains. This supersedes the [previous conservative A/B selection](hud-bob-native-comparison-2026-10-11-102053.md), which retained baseline. Original A is now the approved fallback; baseline was used only as a fresh control. No B/source-pair guard or combined experiment was applied. Existing [options/prototypes](hud-bob-improvement-options.md) and [rendering constraints](rendering.md) remain the design context.

| Variant | Change | Decision |
|---|---|---|
| Original A | Inlined opaque byte-RMW cells; previously measured twice | User-approved fallback; superseded by A2 |
| A1 | Only add `__attribute__((noinline))` to original A's cell helper | Fully validated; improves ordinary BOB deadlines and common HUD overhead; superseded by A2 |
| A2 | Retain noinline; hoist masks and four plane pointers; remove inner byte loop | **Applied**, repeat confirms best deadlines |

A1 uses the same GNU noinline spelling already used by `numberText`; native GCC and host Clang both accept it. A2 performs the same ink-1 background / ink-6 glyph byte RMW equations. The second byte is written only when the six-pixel cell crosses a byte boundary. The sixth background column and all exterior bits are preserved. No potentially odd destination WORD/LONG cast was introduced.

The formatter, gameplay, visibility, scene timing, audio, BOB submission and assets are unchanged. `scoreDraw` retains original A's real production timing/counter hooks, one wait before the first changed/dirty cell, zero waits for unchanged redraws, eight cells on full dirty redraw and histories keyed by the bound physical bitmap. Actual score clear count remains zero. Initial composition remains bounded and unchanged.

## Native complete-window OFF results

Cells are **drops / peak load %**. All five ordinary replays and the injected campaign run on both A500 and AROS. Original A columns are the explicitly retained earlier runs; fresh baseline, A1, A2 and A2 repeat were executed for this refinement. All six non-probe flags are OFF even during campaign; CAMPAIGN_PROBE alone is ON there. No measurements are inferred from the assembly, host speed or queue timing.

| Profile | Replay | Fresh base | Original A 1 | Original A 2 | A1 | A2 1 | A2 2 |
|---|---|---:|---:|---:|---:|---:|---:|
| a500 | pause_continuity | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 |
| a500 | clean_transitions | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 |
| a500 | gameover_title | 0 / 83 | 0 / 83 | 0 / 83 | 0 / 83 | 0 / 83 | 0 / 83 |
| a500 | large_manga | 0 / 78 | 0 / 78 | 0 / 78 | 0 / 78 | 0 / 78 | 0 / 78 |
| a500 | bob_restore | 2 / 107 | 1 / 106 | 1 / 106 | 1 / 105 | 1 / 104 | 1 / 104 |
| a500 | campaign | 5 / 115 | 5 / 112 | 5 / 112 | 5 / 111 | 5 / 109 | 5 / 109 |
| a500-aros | pause_continuity | 0 / 74 | 0 / 74 | 0 / 74 | 0 / 74 | 0 / 74 | 0 / 74 |
| a500-aros | clean_transitions | 0 / 74 | 0 / 74 | 0 / 74 | 0 / 74 | 0 / 74 | 0 / 74 |
| a500-aros | gameover_title | 0 / 81 | 0 / 81 | 0 / 81 | 0 / 81 | 0 / 81 | 0 / 81 |
| a500-aros | large_manga | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 | 0 / 76 |
| a500-aros | bob_restore | 1 / 100 | 1 / 100 | 1 / 100 | 0 / 99 | 0 / 97 | 0 / 97 |
| a500-aros | campaign | 3 / 107 | 3 / 103 | 3 / 103 | 3 / 103 | 3 / 100 | 3 / 100 |

### Weighted mean load %

Means include every actual window, weighted by its real frame count. Integer window loads are quantized; retain both repeated values rather than selecting the fastest. They are elapsed workload estimates, not isolated CPU or DMA measurements.

| Profile | Replay | Fresh base | Original A 1 | Original A 2 | A1 | A2 1 | A2 2 |
|---|---|---:|---:|---:|---:|---:|---:|
| a500 | pause_continuity | 23.460127 | 23.530699 | 23.636556 | 23.424841 | 23.318984 | 23.389555 |
| a500 | clean_transitions | 23.550000 | 23.450000 | 23.600000 | 23.550000 | 23.400000 | 23.450000 |
| a500 | gameover_title | 29.673215 | 29.689587 | 29.738703 | 29.673215 | 29.624100 | 29.640472 |
| a500 | large_manga | 22.855047 | 22.725626 | 22.855047 | 22.855047 | 22.725626 | 22.768766 |
| a500 | bob_restore | 32.585405 | 32.585405 | 32.705694 | 32.585405 | 32.465116 | 32.505213 |
| a500 | campaign | 34.557567 | 34.688399 | 34.688399 | 34.557567 | 34.541212 | 34.541212 |
| a500-aros | pause_continuity | 22.848271 | 22.895554 | 22.930840 | 22.883557 | 22.848271 | 22.848271 |
| a500-aros | clean_transitions | 22.800000 | 22.800000 | 22.800000 | 22.850000 | 22.800000 | 22.800000 |
| a500-aros | gameover_title | 28.820563 | 29.049771 | 29.049771 | 28.836935 | 28.820563 | 28.820563 |
| a500-aros | large_manga | 22.294219 | 22.294219 | 22.294219 | 22.337360 | 22.294219 | 22.294219 |
| a500-aros | bob_restore | 31.311949 | 31.392141 | 31.392141 | 31.314354 | 31.274258 | 31.274258 |
| a500-aros | campaign | 33.208679 | 33.404928 | 33.404928 | 33.214130 | 33.214130 | 33.214130 |

A2 preserves original A's A500 ordinary drop reduction and additionally removes the AROS ordinary BOB drop. Against original A, campaign peak falls **112 -> 109% A500** and **103 -> 100% AROS**; ordinary BOB peak falls **106 -> 104%** and **100 -> 97%**. No scenario's drops or peak worsens versus original A. Campaign drops remain five/three.

Original A's elevated campaign means (34.688399%/33.404928%) are reduced substantially. AROS A2 campaign mean is still **33.214130%**, versus fresh baseline **33.208679%** (+0.005451 percentage point). This tiny reported tradeoff is visible and accepted under the user's deadline-first selection; it is not a claim that every mean improves.

### Frame accounting and equivalence inventories

Every table column has the same complete replay counts on both profiles. Regular report overhead, final partial/full window and final-frame missed vblanks are counted. F8 completion/serial drain is outside the completed replay. No input padding, omitted tail, timing realignment or golden refresh.

| Replay | Measured frames | Final window | Completion logic frame | Images/profile | States/profile |
|---|---:|---:|---:|---:|---:|
| pause_continuity | 1417 | 17 | 1170 | 9 | 34 |
| clean_transitions | 1000 | 50 | 753 | 15 | 23 |
| gameover_title | 3054 | 4 | 2807 | 4 | 77 |
| large_manga | 1159 | 9 | 911 | 5 | 26 |
| bob_restore | 1247 | 47 | 1000 | 5 | 39 |
| campaign | 9172 | 22 | 8925 | 53 | 255 |

Each full trial contains **34098 measured iterations / 688 windows** across twelve replay/profile cases. A1, A2 and A2-repeat each match the fresh baseline at **182 full captures and 908 ordered gameplay states**. These are full-image identities, with no masked pixels or ignored state fields. Native source-pixel, BOB restoration, all thirteen scenes, four bosses/flashes, six-effect bursts, F fixtures, pause/death and visibility checks pass.

## Actual 68000 audit

OFF object `nm` and `objdump -dr` output is retained in each trial's `68000.txt`. The compiler is the same AmigaDev GCC 6.5.0b toolchain, Release `-m68000 -msoft-float -fomit-frame-pointer -mcrt=nix13`. The noinline attribute still permits a constant-propagated helper clone for fixed Y=6; it is a real subroutine call, not an inlined body.

| Build | HUD function span bytes | HUD locals + saved regs | Cell helper span bytes | Helper locals + saved regs |
|---|---:|---:|---:|---:|
| Baseline | 1984 | 12 + 40 = 52 | — | — |
| Original A | 2596 | 48 + 44 = 92 | Inlined | Included in HUD |
| A1 | 2042 | 12 + 40 = 52 | 308 | 20 + 44 = 64 |
| A2 | 2042 | 12 + 40 = 52 | 1036 | 4 + 44 = 48 |

- HUD saves `d2-d6/a2-a6` (40 bytes) for baseline/A1/A2, versus `d2-d7/a2-a6` (44 bytes) for original A. A1/A2 remove the extra **40 fixed entry bytes** from all HUD calls. They do not remove all score-path stack cost: changed cells also pay helper save area, eight argument bytes and four return-address bytes. Entry/helper reservations alone therefore total 128 bytes for A1 or112 for A2 while inside the helper, versus92 in original A's inlined writer. These scoped counts exclude the caller's own return address, interrupts and other call paths; they are not whole-game stack bounds.
- A1 HUD range `0x898a..0x9184`, helper `0xc432..0xc566`. It still spills glyph pointer/shift/masks and reconstructs plane addresses inside its byte loop. A2 retains the HUD range; helper ends at `0xc83e`. Plane bases are loaded once at `0xc466..0xc47e`; pointer increments then follow the interleaved row stride.
- A2 helper retains a four-byte spill slot for mask bytes (`sp@(46/47)` after register saves), not a claim of zero spills. GCC unrolls the single-byte seven-row path and partially unrolls the two-byte path. This explains the larger helper code, not a cycle estimate. The actual native measurements determine benefit.
- Framebuffer reads/writes remain BYTE operations, including odd-address second-byte accesses. A2's optimized WORD/LONG glyph loads address the existing aligned ULONG mask array at even offsets. No new WORD access to an unaligned framebuffer address. No imported 32-bit multiply/divide helper in the audited world/effects/BOB objects; formatter code is unchanged.

## Executable size and observed startup memory

No new persistent mask/cache/CHIP allocation. Code size and loader placement still affect free memory. Readings are startup observations, not formal worst-case bounds; AROS extra RAM cannot establish A500 feasibility.

| Build | Executable bytes | Delta from baseline | A500 CHIP / total free | AROS CHIP / total free |
|---|---:|---:|---:|---:|
| Fresh baseline | 501636 | +0 | 41104 / 50488 | 152248 / 1361224 |
| Original A run 1 | 502312 | +676 | 41104 / 49872 | 152248 / 1360608 |
| A1 | 502012 | +376 | 41104 / 50120 | 152248 / 1360856 |
| A2 run 1 | 502740 | +1104 | 41104 / 49392 | 152248 / 1360128 |

A2 costs **428 executable bytes and 480 observed startup free bytes** relative to original A, and728 executable/free bytes versus A1. CHIP free is unchanged. This is an explicit code/memory-for-deadline tradeoff; A2 is selected for the repeated additional native gains.

| Build | Executable SHA256 |
|---|---|
| Fresh baseline | `b105cfd770f07089252652179023771f8f93908066e705c1fb226d9e3e0b9c06` |
| Original A run 1 | `c78f6b5c1b0b313ed0f7ba432cd09610a57539223f9a6611c74b66cd1fec1898` |
| A1 | `2244607f4186bbd69379613953a383a9fce73cf1797ff639d71a26d96bc5539a` |
| A2 run 1 | `3288785797373564ef654946f610163a33d406e084363e39dc7d7c9fa900bf6d` |

## Host oracle, tests and preservation

- A1 and A2 independently execute extracted **actual production** helper and score functions against the frozen blitter/text baseline and an independent source-font pixel oracle under ASAN/UBSAN. Each passes **252 font-mask rows, 2880 cells** (all16 X residues, ten digits, all16 inks plus patterned/random backgrounds), **5019 transitions** (decimal carries, 65535/65536, eight-digit wrap, UINT32_MAX), and **10038 unchanged redraws**.
- Full40960-byte framebuffer comparisons include all planes, the sixth background column and exterior bits. Histories use both physical buffers with deliberately repeated/nonalternating binding and composition reseeding. Dirty full-score repaint, one synchronization per nonempty batch, no wait on unchanged redraw and zero actual score clears are asserted.
- Fresh baseline, A1, A2 and A2-repeat each pass **C1/1** and **Python3.12 116/116**, including current production counter/history tests. No source, pixel, build, sanitizer or functional failure occurred. Strict campaign performance exits1 remain expected and are evaluated separately from functional checks; no gate or assertion is relaxed.
- The new dirty-baseline freeze contains322 files, initial binary/ADF/cache, full diff and untracked inventory under `.tmp/score-refinement/`. The prior comparison artifacts and published report are preserved. Only score helper/scoreDraw hunks and the two existing score-test adaptations are applied to runtime/test sources; no HEAD restore or overwrite of existing diagnostics.
- Before this report/summary publication, final preservation checks find only `game/src/render_world.c`, `game/tests/unit/test_hud_numbers.py` and `game/tests/unit/test_hud_bob_operations.py` changed from the frozen322 files. `render_effects.c`, gameplay, main loop, assets and installed AGK perf source remain byte-identical. `git diff --check` passes.

## Final accepted OFF disk and remaining limits

The final explicit build sets all seven flags OFF and reproduces the tested A2 executable, **not** the old baseline hash. The exact resulting ADF is booted on A500 and AROS without a rebuild between or after boots; complete ordinary BOB replay, source-restoration, ten images and78 state records pass against the fresh baseline. Hashes remain identical before/after boot.

- Executable: **502740 bytes**, SHA256 `3288785797373564ef654946f610163a33d406e084363e39dc7d7c9fa900bf6d`.
- ADF: **901120 bytes**, SHA256 `62456751103ec296e267a042f710a1145ca5e54d5b3a40c6745f7d8ab41f6878`.
- OFF: `ASTRA_CAMPAIGN_PROBE`, `ASTRA_COMBAT_STRESS`, `ASTRA_COMBAT_TIMING`, `ASTRA_PRESENTATION_TIMING`, `ASTRA_FRAME_BREAKDOWN`, `ASTRA_HUD_BOB_TIMING`, `ASTRA_HUD_BOB_DETAIL`. Each trial explicitly builds/verifies all seven; campaign enables only the probe, then restores all OFF in `finally`.
- **Ready:** accepted A2 source and tested OFF build remain applied in the isolated checkout. No native comparison/final-boot check remains pending. No GUI, commit, cleanup, paid generation or `west-pear` modification.
- **Still blocked:** global zero-drop/<=90% PAL50fps. A500 campaign remains **5 drops/109%**, ordinary BOB **1/104%**; AROS campaign **3/100%**, BOB **0/97%**. The campaign fixture is injected, not an ordinary full-quota clear.
- **Unproven broader gates:** ordinary complete campaign, real Amiga hardware, formal worst-case free memory/stack, native OOM fault injection and final artistic acceptance. No new allocation required allocation-failure work.
- Optional light/detail timing was not run; no per-score raster-line, pure-CPU or category-specific BOB DMA claim is made. Whole replay counters include CPU, waits, contention and audio interrupts. Queue-only cost shifts are not used as acceptance evidence.

## Retained evidence and reproduction

New root: `.tmp/score-refinement/`. `base/`, `A1/`, `A2/`, `A2-repeat/` each retain candidate patch, measured source hashes/snapshots, OFF binaries/ADFs, probe artifacts, all serial/capture/window/memory records, `trial.json`, `prod/comparison.json`, command logs and `68000.txt`. `A1-oracle/` and `A2-oracle/` retain compiled C and sanitizer outputs. `final-boot/report.json` retains exact final disk identity and preservation.

Commands: `python3.12 .tmp/score-refinement.py freeze`; `... trial <new-label>`; `... oracle <new-label> score`; `... summary <labels>`; `... final A2`. The wrapper reuses the prior reviewed harness/oracles with only a separate output namespace. Existing output directories are not overwritten. Original A evidence remains in `.tmp/native-comparisons/{A,A-repeat}/` with its original timestamps.

### Native execution timestamps

| Run | Start | Finish |
|---|---|---|
| Fresh baseline | 2026-10-11T10:34:59.119542+02:00 | 2026-10-11T10:40:05.259597+02:00 |
| Original A run 1 | 2026-10-11T09:45:52.240886+02:00 | 2026-10-11T09:51:29.339565+02:00 |
| Original A run 2 | 2026-10-11T09:53:27.028419+02:00 | 2026-10-11T09:58:59.772259+02:00 |
| A1 | 2026-10-11T10:41:46.079667+02:00 | 2026-10-11T10:46:53.302388+02:00 |
| A2 run 1 | 2026-10-11T10:48:30.711912+02:00 | 2026-10-11T10:53:41.042006+02:00 |
| A2 run 2 | 2026-10-11T10:54:55.063881+02:00 | 2026-10-11T11:00:04.711451+02:00 |
