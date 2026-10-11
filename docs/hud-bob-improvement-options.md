# Score HUD and BOB improvement options

**Document timestamp:** 2026-10-11 09:16:10 CEST (UTC+02:00). This is the
research/report time, **not** the time of the earlier native measurements.
**Checkout:** isolated `astra-perf`, HEAD
`10f4f477b3b3feb229dd42794588d3a021ea868a`, with the existing diagnostic and other
uncommitted work retained. **Status:** research and bounded host prototypes only;
no candidate is integrated or accepted as a native optimization.

## Recommendation and hardware contract

Try the **opaque CPU score-cell writer first**. It removes the clear/CPU-glyph
handoff for each changed digit while reusing the existing masks and physical
bitmap history. Compare adjacent-clear batching as a smaller alternative.
For effects, first test skipping equal source-pointer assignments; investigate
fixed-size setup only after measuring whether CPU setup remains material.
All prospective time benefits below are **unquantified hypotheses**.

The target is an A500, 68000 at 7 MHz, OCS PAL 50 Hz, 512 KiB CHIP plus 512 KiB
slow RAM. A frame is 20 ms; acceptance remains zero missed vblanks and <=90%
peak load with audio. AROS is supplementary and cannot prove baseline RAM fit.
The display consists of two 320×256×4-plane interleaved CHIP bitmaps: 40 bytes
per plane row, 160 bytes per interleaved row, 40,960 bytes per bitmap. Word/long
accesses must be even-aligned; byte accesses in the prototype avoid that hazard.
See [hardware constraints](../game/AGENTS.md), lines 3–20, 82–117, and
[rendering ownership/order](rendering.md#actual-frame-order).

## 1. Findings from current implementation

### 1.1 Score: clear plus cached transparent glyph, not uncached text

[`render_world.c`](../game/src/render_world.c), lines 51, 59–67, 110–129,
207–269, 314–340, 651–654 and 693:

1. `hudDraw` compares the score against the **bound physical bitmap's** history.
2. `scoreDraw` formats the new value once, using `numberText`; the old digits
   already reside in `HISTORY.scoreText`. Eight displayed digits wrap modulo
   100,000,000, including full uint32 values.
3. For a normal changed cell, `blitRect(x,6,6,7,1)` clears to ink 1;
   `textDraw` waits, then overlays the cached 5×7 glyph in ink 6 across all four
   planes. The sixth column remains background. Unchanged cells are untouched.
4. `dirty=1` has a different baseline: one 48×7 clear and one eight-glyph draw,
   not eight clears. Composition initializes both score histories with the frozen
   command stream (`renderWorldBegin`, lines 794–817); it is already bounded.

`fontMasksCreate` already builds `[3][36][7]` masks once: **3,024 bytes**, using
the actual font. The score uses size zero; no new digit image bank, CHIP font
atlas, or duplicated mask cache is needed. Narrow formatting already uses word
arithmetic; full-width formatting avoids a division helper. Formatting is not
the main measured score interval.

### 1.2 BOB pipeline: submission can save earlier queued objects

Primary sources:
[`render_bobs.c`](../game/src/render_bobs.c), lines 83–93 and 142–175;
[`render_effects.c`](../game/src/render_effects.c), lines 19–86;
[`render_boss.c`](../game/src/render_boss.c), lines 12–65;
pinned ACE [`bob.c`](../game/vendor/ACE/src/ace/managers/bob.c), lines 221–274,
315–446, 452–595, and [`bob.h`](../game/vendor/ACE/include/ace/managers/bob.h),
lines 18–48 and 205–244.

- At frame start, select by actual bitmap identity and restore its **N−2** saved
  backgrounds with `bobBegin`, then wait. World/star changes happen afterward.
- HUD finishes before the first push. Submission order remains **boss → effects
  → pickups → shots/lances**; effects retain slot order. Nothing may change a
  submitted BOB's metadata before ACE finishes using it.
- `bobPush` appends a pointer and, when the blitter is idle, calls
  `bobProcessNext`. Before pushing is done, that function only processes pending
  saves, including a save belonging to an earlier category. The first save
  initializes shared blitter registers; later saves rely on their continuity.
- `bobEnd` marks pushing done, drains remaining saves, then draws every BOB in
  order. Masked drawing uses A=mask, B=image, C=destination and D=result. The
  application terminal wait completes the last launched blit.
- Saves capture the current background **before any queued foreground draw**.
  Keep the saved-area stream, queue order, per-bitmap destination pointers and
  old-position history consistent through overlap, disappearance and scene reset.

Thus a smaller effects-queue interval can simply mean saves moved to the common
flush. Measure the sum plus terminal wait and the separate restoration phase.
The installed kit's
`/Users/youen/Code/amiga/amiga-game-kit/techniques/bobs/TECHNIQUE.md`, lines 23–69,
was read. Its simplified warning against blits between Begin/End is refined by
the pinned header: other blits are permitted **before the first push**, exactly
as this game's HUD/star sequencing requires. Do not move them between pushes.
The technique's separate 32×16/3-plane example timings are not an Astra estimate.

### 1.3 What is already preinitialized

`renderEffectsCreate` calls `bobInit` once per slot. ACE already retains width,
height, interleaved height, save modulo and save blit size. `loadStrip` already
caches **all eight data/mask addresses for all three sizes**. The boss similarly
caches sector pointers and one current-sector white flash image; normal shot
sources are fixed. “Cache frame addresses” or “preinitialize BOB dimensions”
would repeat existing work, not remove the observed hot path.

Remaining effect preparation is eligibility, slot-size selection, bounds/clamp,
`effectFrame`, indexed source loads, `bobSetFrame`, position stores and push.
`bobSetFrame` itself is only two pointer assignments. The current CMake cache
already has `ACE_BOB_WRAP_Y=OFF` and `ACE_BOB_PRISTINE_BUFFER=OFF`.

## 2. Existing native evidence, not new candidate gains

The [nested measurement record](combat-performance.md#it11b--nested-hud-and-bob-measurements),
lines 822–976, reports these **A500 detailed-trace means over four selected
campaign bursts** (751/2817/4879/6927). These are elapsed raster measurements,
including diagnostic work, waits, interrupts and CHIP contention.

| Measured interval | Lines | ms (`lines × 20 / 313`) | Interpretation |
|---|---:|---:|---|
| Score inclusive | 38.5 | 2.460 | One conversion plus comparison, clear/glyph and history work |
| Nested conversion | 4 | 0.256 | Already contained in score |
| Nested compare/clear/glyph/return | 32.5 | 2.077 | No isolated CPU versus clear-time split |
| Effects queue | 47.75 | 3.051 | Six effects' eligibility/setup plus opportunistic saves |
| Common `bobEnd` | 41.25 | 2.636 | Remaining saves and all categories' masked draws |
| BOB parent | 114.5 | 7.316 | Includes the preceding rows, other categories and final wait |

Each burst actually submits **seven BOBs**: six shifted 16×16 explosions and
one shifted 16×16 bonus. There are no remaining player-shot pushes on those
frames. The six effects have 768 save word-positions and 768 masked-draw
word-positions; the bonus adds 128 of each. These are geometric operation areas,
not elapsed DMA measurements or total memory bus traffic. Earlier restoration
is outside the BOB parent. Neither “3.051 ms is pure CPU” nor “2.636 ms belongs
only to explosions” follows from this evidence.

The observed score changes are 1/2/2/2 digits. Digit adjacency was **not counted**,
so the two-digit samples do not establish a batching saving without the old/new
text or changed-bit mask. Detailed probes materially perturb native timing;
never subtract their inactive-block costs as a fixed overhead correction.
The existing complete OFF result remains A500 campaign **5 drops /115% peak**,
ordinary BOB **2/107%**, not a passing 50fps result
([accepted it11](combat-performance.md#it11--physical-score-cache-and-packed-boss-label)).

## 3. Ranked bounded options

Ranking is recommended experiment order, balancing scope, risk and directness.
Operations below are source-derived counts or explicitly labelled host counts;
none is a forecast of native milliseconds.

| Rank | Candidate and functions that would change | Operations removed / retained | Memory | Risk and acceptance test |
|---|---|---|---|---|
| **1** | **Opaque CPU 6×7 score cells**: add a score-only helper beside `scoreDraw`; replace its per-digit clear/`textDraw` pairs. Keep `hudDraw`, formatter and physical history contract. | For `d` normal changed digits: `d` clear calls → **zero**; `d` text-entry waits → one batch wait if `d>0`; one four-plane masked RMW pass per cell replaces clear plus transparent pass. Formatter/comparisons remain. For dirty full-score repaint remove its one clear, not eight. | No new persistent mask or CHIP allocation; small local masks/pointers, code growth unmeasured. Ordinary code/data placement can still affect free CHIP. | Byte-mask correctness, stale buffer history, outstanding blits and CHIP CPU contention. Host oracle passes below; require exact native captures, same-frame score and OFF whole-frame improvement. |
| **2** | **Clear adjacent changed runs** in `scoreDraw`, then one `textDraw` of each run using a bounded temporary substring. | `d` clears/text calls → `r` clears/text calls, where `r` is the number of contiguous changed runs; `d-r` handoffs removed. Same `d` glyphs. One isolated digit gives no handoff saving. Keep existing full-dirty path. | At most nine stack bytes for a terminated run; no persistent/CHIP payload. | Lower pixel-algorithm risk, smaller opportunity. Never clear across unchanged holes unless those digits are redrawn. Test carry runs, separated changes, identical displays after numeric wrap and both histories. Native A/B needed; this alternative was researched, not prototyped here. |
| **3** | **Skip equal effect source assignments** in `renderEffectsQueue`, calling `bobSetFrame` only when the existing frame/mask differs. Keep every position update and push. | Avoid the setter call and its two pointer stores for equal source pairs. Pointer-compare version still loads the indexed sources and adds comparisons. An optional one-byte frame key per slot can avoid indexed loads but adds invalidation bookkeeping. | Tested pointer-compare form: zero persistent bytes. Optional index cache: eight bytes plus any alignment; initialize at create and invalidate/reset on asset recreation. No CHIP image bank. | Low semantic risk when scoped to immutable strips and before push; branch cost may outweigh tiny setter. Host equal-output/count evidence below. Test spawn, slot reuse, omitted frames, scene transitions, recreation and all sizes before native timing. |
| **4** | **Fixed 16×16 preparation fast path**, then optionally manager-internal indexed setup: specialize `renderEffectsQueue`'s first six slots; a later separate ACE experiment would touch `bobProcessNext` only via a reproducible local patch. | Application path can remove repeated size selection/table loads and use constant x≤303/y≤200 clamps. Manager path could replace width/modulo calculations with alignment-indexed constants. **No save, restore or masked draw is removed.** | Application split needs no persistent payload but adds code. A compact 16-alignment table with five 16-bit fields would be 160 ordinary bytes; this is a proposed layout, not allocated or measured. | Medium/high complexity and instruction-cache-free 68000 code-size/placement tradeoff. Must retain generic hero/boss/other BOB cases, exact shift/mask semantics, all-save-before-draw and overlap order. Test all X residues and right edge, every size and mixed queue; only pursue after the first three experiments. |

### 3.1 Opaque-cell calculation and synchronization

Let `C` be the six-pixel cell mask and `G` the five-pixel glyph mask, both shifted
to the destination bit position. For each affected destination byte:

```text
plane0 = (old0 & ~C) | (C & ~G)   // background ink1; foreground clears bit0
plane1 = (old1 & ~C) | G          // foreground ink6
plane2 = (old2 & ~C) | G
plane3 =  old3 & ~C
```

`G` must be a subset of `C`. Exterior bits, including neighbouring HUD fields,
survive. Rows advance by 160; the plane bases are spaced by 40. A cell touches
one byte at X residues 0–2, two at 3–7. The actual score's X sequence is
162+6i, so residues are 2/0/6/4, repeated. This means 28 or 56 byte RMW stores
per cell, not a whole-frame CPU repaint. The sixth column must be explicitly
cleared even though the font has only five columns.

Wait once **before the first changed cell**, after any outstanding earlier HUD
blit and before any BOB push. Do not remove that synchronization because the
candidate has no blits of its own. Leave initial bounded composition unchanged.
The isolated implementation uses endian-independent byte stores; no potentially
odd `UWORD*` cast at `x>>3` is introduced.

### 3.2 Source-cache lifetime and meaningful equal-output counts

The cache is about a BOB's **current source**, not its N−2 background. Reading
the existing two pointers is enough to avoid a new cache. A byte frame key is
safe only while each slot's size and strip identity are fixed and the key is
kept consistent with `bobInit`/recreation. Never key only on effect age without
accounting for lifetime/frame mapping or slot reuse.

The extracted-queue host experiment initialized both implementations as creation
does (frame zero). For six visible effects over ages 0–15/lifetime 16:

| Host workload | Always assign | Compare existing source pair |
|---|---:|---:|
| Successful pushes | 96 | **96**, same ordered metadata |
| Setter calls | 96 | 42 |
| Pointer assignments inside setter | 192 | 84 |
| After reuse at age zero and one repeated-age redraw: cumulative setter calls | 108 | 48 |

This counts saved assignments, **not native time**. The first incarnation can
reuse creation's frame-zero pointers; an age-zero spawn after a previous frame
seven needs a real update. Therefore even a six-kill first-frame burst does not
universally save six setter calls. Six 16-tick lifetimes are a controlled host
workload, not inferred counts from the four native target records.

### 3.3 Why “prepare everything, then push” is not automatically better

All descriptor mutation must finish before that descriptor's push. Preparing
the entire effects batch before its first push could make the push loop shorter,
but delays the first save and removes opportunities to overlap later CPU setup
with prior save DMA. If the boss is already pushed, its pending save also affects
this schedule. Neither operation count nor total work necessarily decreases.
Keep the current ordered interleaving as the baseline. A future prepare/push
experiment must compare effects setup **plus flush plus wait**, not celebrate a
transfer of cost between timestamps. It must not draw any category before later
categories' backgrounds have been saved.

## 4. Executed host prototypes and audit

Everything is under [`.tmp/hud-bob-experiments/`](../.tmp/hud-bob-experiments/).
Run from this isolated checkout:

```sh
python3.12 .tmp/hud-bob-experiments/run.py
python3.12 .tmp/hud-bob-experiments/bob-run.py
```

Both compile with `cc -std=c11 -Wall -Wextra -Werror -O1
-fsanitize=address,undefined`; generated C, executables, commands and results are
retained locally. **No unexpected compile, sanitizer or assertion failure occurred.**

### Score oracle

`run.py` extracts the actual current `pixelRead`, `fontMasksCreate`, `textDraw`,
`numberText` and `scoreDraw` C functions. It reads all 36 glyphs from
[`game/art/font.txt`](../game/art/font.txt), constructs a padded one-plane source
bitmap, and runs production mask creation. The independent pixel oracle paints
ink 1 or 6 from source-font bits, rather than calling the candidate or trusting
the generated masks. Baseline `blitRect` is modelled synchronously by pixels.

- **252 unscaled glyph-mask rows** verified against source font.
- **2,880 cell cases:** ten digits × all 16 X residues × 18 backgrounds
  (all 16 uniform inks, checker pattern, deterministic random bytes).
- Each case compares the **entire 40,960-byte bitmap** for baseline and candidate
  against the oracle, including the sixth column, all planes and exterior bits.
- **5,019 score transitions**, including decimal carries, 65,535/65,536,
  99,999,999/100,000,000, UINT32_MAX→0 and 5,000 deterministic uint32 samples.
  Physical buffers are deliberately rebound in three-use runs rather than
  simple parity. Dirty full-score updates recur, and composition reseeds both
  images/histories periodically.
- **10,038 unchanged redraw checks** require no waits/clears and byte-identical
  output. Changed-only history matches the displayed eight characters.

This executes extracted score rendering, not `hudDraw`'s full lifecycle or actual
composition scheduling. Font bitmap construction uses the authored font rather
than booting the generated asset constructor. Hardware synchronization, beam
deadlines, interleaved blitter execution and native generated candidate code
remain untested. Host wall-clock time was not used as an Amiga estimate.

### BOB metadata oracle

`bob-run.py` includes the real `logic.h`, extracts `effectFrame` and
`renderEffectsQueue`, and creates a second copy with only a source-pair equality
guard around the setter. It compares every ordered push's frame, mask, X and Y.
**65,615 queue cases pass**, including every byte age/lifetime combination,
zero lifetime, out-of-bounds positions/clamping, phase/kind rejection,
inactive slots, small/hero/boss sizes, readiness, slot reuse and repeated age.

`bobPush` here captures metadata only. This experiment **does not execute ACE
save/restore or model DMA, moving stars or overlap pixels**. Those remain native
acceptance obligations. No effect is suppressed by the candidate guard.

### Existing generated 68000 audit

Read-only audit used the accepted build's
`game/build/perf-loop5-it11-final/68000.txt`, especially lines 22227–22527:
`renderEffectsQueue` traverses fixed-size effect/BOB records; size selection
still leads to width/height table reads; the bounded age threshold loop is
expanded into comparisons; indexed data/mask loads, stack argument pushes and
an actual `jsr _bobSetFrame` remain before position writes and `_bobPush`.
For example offsets 0x5b0–0x5d4 show that sequence. This supports a real setter
call-removal opportunity, not a claimed DMA reduction. It also cautions that a
source-level loop simplification may enlarge or duplicate machine code.

No candidate cross-compile or native build was run. Therefore candidate register
spills, exact instruction count, code residency and helper calls are still to be
audited. Do not derive 7 MHz timings by multiplying host operations by guessed
cycle costs under concurrent OCS DMA.

## 5. Rejected or deferred unsafe proposals

- **Skip drawing stationary/same-frame effects:** rejected. The actual back bitmap
  has N−2 pixels; restore and moving-star catch-up occur before this frame's BOBs.
  The same source/position still needs current-background save and masked redraw.
- **Skip restoration, use one global history, or infer buffer by tick parity:**
  rejected. Composition/held publication break parity; retained overlap and
  removed objects depend on the actual physical queue.
- **Save/draw each effect immediately, reorder by source/alignment, or flush each
  category:** rejected as an optimization shortcut. Earlier foreground may enter
  later saves, z-order can change and shared completion attribution changes.
- **Snap X, omit the bonus, reduce effect count/size/duration, delay first-frame
  explosions or score digits:** rejected; unauthorized pixel/timeline changes.
- **Spend hardware sprite channels on six effects:** not a drop-in option.
  Hero owns 0–3; normal PLAY enemies own attached 4/5 and hostile streams use
  6/7. Palette and scanline overlap constraints remain; no channel/palette proof
  supports this substitution ([rendering DMA ownership](rendering.md#dma-channels-and-decor)).
- **Enable pristine-buffer restore:** rejected for this bounded experiment;
  dynamic stars make a static pristine background stale, and another full bitmap
  costs 40,960 CHIP payload bytes before descriptors. Current save histories are
  intentional. **Disable Y-wrap** is already done, so it offers no new gain.
- **Recache fonts/frame addresses or replace decimal formatting first:** deferred
  as misdirected for these samples. The caches exist and formatting is the small
  nested interval; preserve the tested uint32/physical-buffer semantics.

## 6. Next native A/B plan

1. Serialize with the owner of native validation; do not build into a concurrently
   used tree. Freeze the baseline source hashes, flags, compiler and executable.
   Make separate single-change candidates for ranks 1, 2 and 3, then consider 4.
2. Cross-compile candidate objects in the designated isolated build. Audit 68000
   output for illegal alignment, helper calls, code growth and register spills.
   For rank 1 verify one synchronization before the batch and no per-cell blit;
   for rank 3 count equal source pairs versus setters **and retain equal pushes**.
3. Run light targeted traces with identical instrumentation on both sides: the
   four campaign burst IDs, ordinary 816/954/977/981 and BOSS 7704/7780. Retain
   raw endpoints and exact parent sums. Count changed-digit masks/run counts,
   queued effects by frame transition and all categories. No per-object clock
   reads or extra flushes in the acceptance path.
4. Native correctness must include both physical buffers, carries and score wrap,
   dirty redraw after reset/respawn, six overlapping effects with moving stars,
   simultaneous bonus/shots/boss, all X residues and edge clamps, repeated frame
   sources, slot reuse, pause/death, removal and scene discard/re-entry. Compare
   complete images and gameplay state without masks, timeline shifts or golden
   relaxation; run existing source-font and BOB restoration verifiers.
5. Use fully timing-OFF **complete original replays**, including the final partial
   window and last-frame drops, on A500 and AROS with sound. Report campaign and
   ordinary drops/peak, not just moved queue timestamps. Repeat matched runs if
   phase-sensitive differences are small. Record executable size, startup free
   CHIP/total and allocation changes without calling startup a worst-case bound.
6. Keep the zero-drop/90% gate unchanged. Restore all diagnostic flags OFF in the
   serialized owner's finalization, verify hashes, and distinguish incremental
   improvement from global acceptance. An opaque writer can still lose on native
   CHIP contention; host correctness alone is not permission to accept it.

## 7. Preservation and evidence boundary

The only authored files are this report and `.tmp/hud-bob-experiments/`.
Production sources, vendor, AGK, main loop, build artifacts, snapshot documents
and `docs/combat-performance.md` were not edited. No GUI, commit, cleanup or paid
generation was used. Existing work was read as the baseline, not reverted.

`preservation-before.json` / `results.json` retain SHA256 fingerprints of all
regular `game/src/*` files, CMake source/cache, font, pinned BOB source/header and
current production executable/ADF. The host score run verifies before/after
equality; `verify-preservation.py` provides the final read-only comparison.

| Current artifact | SHA256 |
|---|---|
| `game/build/astra` | `b105cfd770f07089252652179023771f8f93908066e705c1fb226d9e3e0b9c06` |
| `game/build/astra.adf` | `e0d625da2f00420e29572b7d424d6a852f7bf247f884430e89c5f154414cabd0` |
| `game/build/CMakeCache.txt` | `451a0f73b592dbb6f4ca623b16075863dd13db87aafb307acfc365c82f0cbd70` |

The current ADF hash is recorded as observed, rather than copied from an older
measurement's disk metadata. All seven ASTRA flags are OFF: CAMPAIGN_PROBE,
COMBAT_STRESS, COMBAT_TIMING, PRESENTATION_TIMING, FRAME_BREAKDOWN,
HUD_BOB_TIMING and HUD_BOB_DETAIL. No flag was changed by this task.

**Remaining unmeasured:** native candidate cost and peak/drop effect, asynchronous
save/restore correctness for any future BOB manager specialization, CHIP bus/IRQ
phase effects, generated candidate 68000 code and native memory residency.
No numeric performance gain is claimed for these prototypes.

## 8. Portable publication note

This report is published identically in the main workspace and the isolated
measured checkout. Its original **2026-10-11 09:16:10 CEST** report timestamp is
preserved. Source anchors, line numbers, build artifacts, hashes and experiment
paths throughout this report refer to the measured checkout at:

`/var/folders/62/sj1vngrd76v9j3xk7v896j8w0000gn/T/opencode/astra-perf`

That checkout's recorded HEAD is `10f4f477b3b3feb229dd42794588d3a021ea868a`,
including the uncommitted work described above. Code and documentation in the
main workspace (`/Users/youen/.baton/worktrees/Shooter/west-pear`) can differ;
relative source links opened there must not be treated as the measured revision.
Tests, prototypes and `.tmp/hud-bob-experiments/` outputs were **not copied into
the main/production workspace**, and publication does not integrate any candidate.

The accompanying [dated frame-time breakdown snapshot](frame-time-breakdown-2026-10-11-092005.md)
is available beside this report in both workspaces. Use that snapshot for the
portable measurement context; resolve source and experiment references against
the isolated absolute checkout above.
