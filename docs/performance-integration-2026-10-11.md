# Performance integration into the localized primary

## Result and ancestry

The user-approved target is `west-pear` (primary source `61d3056`); there is no
local `main`. Performance work is checkpointed at `269bdb6`, descended from
`10f4f47`. The four byte-identical published reports were first preserved on
primary at `8aba2e6`. Integration uses an ancestry merge, not copied source files.

The merged production build passes the focused integration bundle below.
**Global zero-drop / <=90% PAL 50fps acceptance remains blocked.** The earlier
isolated A2 campaign5/109% and BOB1/104% A500 results are historical; they are not
measurements of this larger localized build. No fresh injected campaign was run.

## Merge semantics

- Retained primary English/French selection, CP1252 glyphs, both startup label
  banks, F9 preview, ordinary160×96 portraits,320×192 ending, white inset border,
  WIN-only peach ink11 and exit palette restoration, blue almond eyes, silver
  armor and approved bold cheek marks.
- Retained fixed galaxies/36 movers, physical star/score histories, bounded
  sparse repairs, repair/foreground separation, fixed-image hostile streams,
  scalar admission, A2 opaque6×7 score cells, packed BOSS label and complete
  replay-window accounting. Diagnostic hooks remain compile-time guarded.
- Packed BOSS uses the same four glyphs in both approved catalogs; the host
  test checks both catalog entries and full-framebuffer output. Localized font
  and label tests retain all extra glyphs and post-selection bank checks.
- Merged font/title/HUD extraction harnesses include both sets of dependencies;
  scene-close tests use the primary152px height and preserve the separate final
  foreground-ready step. Runtime scene geometry is unchanged from primary.
- Regenerated presentation data from primary masters/catalog. Result:72,684
  resident bytes,26 cards,16 HUD variants, five shared images. Generated headers,
  decoder, importer, generator, selected art and catalog remain byte-identical
  to `61d3056`; the regeneration did not import older140×84 images.
- Historical primary and isolated performance documentation is retained with
  explicit scope labels. The four published report files retain their exact bytes.

## Initial stale checks, diagnosis and correction

First full host run: C1/1 PASS; Python144/145 PASS. The sole failure was
`test_title_keycaps.py`, unchanged from primary: it expected literal English
`queueText` calls although primary already uses localized messages and a6px
French shift. Assertions now require that exact localized positioning; the
independent icon-pixel, mirroring, exterior and three-row bounds are retained.

First A500 production bundle passed the transition replay but its companion
checker reported `opening close changed frozen exterior`. The checker still
excluded the old `(152,56)-(312,192)` box. All1,034 reported changed pixels lie
inside the current `(136,56)-(312,208)` story box; zero lie outside the current
box and validated hero. Corrected only the obsolete box coordinates. Publication,
vblank, complete-frame holds, source pixels and exterior equality remain strict.
Original failed evidence remains in `game/build/merge-perf-production/`.

Final validation passes with these explicit harness corrections. No goldens,
performance thresholds, entity lifetimes or hardware profiles were changed.

## Executed checks

- `bash tools/agk unit`: **1/1 PASS**.
- Python3.12 discovery: **146/146 PASS**,207.697seconds on the final run.
- New actual-production A2 ASAN/UBSAN oracle: **2,880 cells** (ten digits,16 X
  residues,18 backgrounds), **5,019 transitions**, **10,038 unchanged redraws**,
  **252 source-font mask rows**; whole40,960-byte bitmap comparisons, sixth
  background column, decimal/uint32 wrap, nonalternating physical histories,
  composition reseeding and one-wait/zero-wait batch rules.
- Presentation/galaxy/title-plate generation/freshness PASS. Bold-marks and
  character generation/oracles PASS, including259 protected files,16 approved
  mark changes,2,571 immutable eye pixels and498+7 skin samples.
- Allocation-safety ASAN/UBSAN PASS:16 audio failure positions/retries,
 21 exact generated arrays, BOB/bitmap partial cleanup and reproducible vendor
  patch. Music channel and original ACE PCM checks PASS.
- Native production build PASS, all seven flags explicitly OFF.
- Actual68000 audit retained at `game/build/merge-perf-68000.txt`: world,
  BOB/boss/effects, galaxy and presentation objects; no imported32-bit
  multiply/divide helpers in these objects. No native timing inferred from host
  execution or instruction counts.

## Focused native bundle — both a500 and a500-aros

All paths below are under primary `game/build/`.

| Evidence | Checks |
|---|---|
| `merge-perf-ending-{a500,aros}/` | Production F9; ready/held/released WIN, restart, ignored F9 outside TITLE, ESC,299,264 source pixels/profile, peach/sky and entire title restoration |
| `merge-perf-production-validated/{a500,a500-aros}/` | Complete-window pause, transitions, GAMEOVER/title, manga and ordinary BOB;38 captures/profile |
| `merge-perf-galaxy/{a500,a500-aros}/` | Four source-derived galaxies and exact XOR-star histories;352,256 pixels/profile; paused-background equality |
| `merge-perf-french-{a500,aros}/` | Four titles, opening/HUD, ready/pause/release, F9 ending, ESC, GAMEOVER and retained French selection;13 captures/profile |
| `merge-perf-sectors/{a500,a500-aros}/` | Four original title plates, both wraps, source-font caption/navigation, Nebula connected-background and crystal bands |

`tools/verify-localized-ui.py` independently checks141,120 French UI/story pixels
per profile and12,800 initial English HUD pixels per profile. F9 English source
verification and French ending verification use the current selected art.
BOB checks prove164 opaque+92 transparent badge pixels,768 restored background
pixels, genuine six-kill bonus/pickup, exact150-tick scene dwell and40-tick hero
death freeze (native combat start744, death stage167). No x-adjust was used.

**81 complete320×256 capture pairs are byte-identical across profiles**:
7 ending+13 French+38 ordinary+16 galaxy+7 sector/title. Selected native ending,
French title/HUD/ending, ordinary bonus drop and scene/restored background captures
were visually inspected. Pixel assertions cover the specified full regions;
cross-profile comparisons cover the entire captured screens.

## Fresh merged production timing

Five ordinary replays include all measured original iterations and final
full/partial windows. The appended F8 completion/hold is outside measurement;
regular reporting followed by gameplay remains included. Localization selection
and larger art change frame counts, so these are not like-for-like isolated A2
comparisons. Entries are **dropped vblanks / peak load%**.

| Replay | Actual frames / final window | A500 | AROS |
|---|---:|---:|---:|
| Pause continuity |1744 /44|0 /89|0 /88|
| Clean transitions |1327 /27|0 /89|0 /88|
| GAMEOVER/title |3425 /25|0 /89|0 /88|
| Manga |1486 /36|0 /89|0 /88|
| Ordinary BOB |1574 /24|**1 /100**|**0 /93**|

F9 emitted-window observations (not complete-tail performance acceptance) are
0 drops,89%/88% peaks. Global50fps still fails; fresh campaign, full ordinary
campaign clear, real hardware, native OOM and formal worst-case RAM/stack bounds
remain unproven. Known stale broad shared goldens were not refreshed or rerun.

## Final primary artifacts and launch handoff

Produced by an explicit primary build with all seven OFF:
`ASTRA_CAMPAIGN_PROBE`, `ASTRA_COMBAT_STRESS`, `ASTRA_COMBAT_TIMING`,
`ASTRA_PRESENTATION_TIMING`, `ASTRA_FRAME_BREAKDOWN`, `ASTRA_HUD_BOB_TIMING`,
`ASTRA_HUD_BOB_DETAIL`. Cache lines97–115 independently confirm OFF.
The same disk was used throughout the final focused production runs.

| Artifact | Bytes | SHA256 |
|---|---:|---|
| `game/build/astra` |543048|`fc2c8f8ec10ea0796008e550f12f38711471b69de25f67097220cc1768213011`|
| `game/build/astra.adf` |901120|`318a4730bf233eda727efafcf16502f96fd792c49937dfb4a85ef6b9816b9890`|

Observed startup free memory: **A5005,296 CHIP /7,184 total bytes**;
**AROS150,904 CHIP /1,317,920 total bytes**. These are actual startup readings,
not worst-case bounds. AROS does not establish baseline A500 memory feasibility.

Machine-readable identities, flags,81 capture-pair checks and complete ordinary
performance records: `game/build/merge-performance-evidence.json`.
Source checkpoint is clean; no push, GUI launch, cleanup or worktree removal.
Parent owns GUI launch of the exact primary ADF after the integration commit.
