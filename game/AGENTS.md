# Astra: A500 implementation constraints

## Target and completion gate

- A500, 68000 at 7 MHz, OCS, **PAL 50 Hz**, **512 KiB chip + 512 KiB slow RAM**.
- One gameplay tick per video frame: **20 ms** maximum, with headroom for music
  interrupts and DMA. Aim for <=90% peak load in measured gameplay windows.
- A deliberate gameplay pause freezes simulation, not display, effects or audio.
- Validate on `a500` and `a500-aros`; AROS has extra fast RAM and cannot establish
  that a memory budget fits the baseline A500.
- All 11 functional campaign features are implemented; **performance acceptance is BLOCKED**.
  Latest ordinary production suite: 38/38 shared-golden tests PASS,
  all 42 complete captures byte-identical across profiles. Latest injected fixture:
  functional PASS on both, 40 captures each; strict command exited FAIL (A500
  22 drops/130% peak; AROS 17 drops/123%). Added F probes and changed waves mean
  this is not a like-for-like comparison with older runs. Keep zero drops and
  <=90% peak as the unchanged gate.
  `perf.agk` guards only the stable ACE intro, not full-game 50fps.
- A campaign feature is complete only after rule tests, inspected screenshots,
  memory checks and performance measurements cover its worst-case states.
  Keep the 50fps target; do not substitute25fps, faster hardware, removed audio,
  masked screenshot regions or profile-specific goldens to make a test pass.

## Current architecture

| Module | Responsibility |
|---|---|
| `src/logic.c/.h` | Portable, deterministic rules and fixed-size pools; no ACE, hardware, allocation or I/O |
| `src/main.c` | Lifecycle, input, sound events, telemetry and frame publication |
| `src/render.c/.h` | Rendering coordinator, shared blank word and palette/copper ownership |
| `src/render_stream.c/.h` | Double-buffered custom sprite DMA streams; cached pixels and inline control-word writer |
| `src/render_hero.c/.h` | 32×24 hero: attached hardware channels0–3 |
| `src/render_enemies.c/.h` | Attached enemies/asteroids on4/5; yields the pair during boss combat |
| `src/render_bullets.c/.h` | Independent hostile streams on6/7 in PLAY,4–7 in BOSS |
| `src/render_bobs.c/.h` | Shared ACE BOB manager, per-bitmap restore queues and submission order |
| `src/render_boss.c/.h`, `render_effects.c/.h` | 64×48 boss/flash and eight fixed explosion slots |
| `src/render_world.c/.h` | Two four-plane bitmaps' histories, copper decor, stars, fonts and HUD |
| `src/render_scenes.c/.h` | 13 scenes over five manga panels; bounded composition and animation |
| `src/campaign_audio.c/.h` | Sole post-intro music controller, sector selection and mute continuity |
| `src/intro.c/.h` | Original ACE/Micrix startup and exact ACE audio ownership |

Keep interfaces small and ownership explicit. Child renderers free only owned
assets, never borrowed screen/view/blank pointers. Constructors must permit
partial cleanup. Entity visibility feedback protects against invisible collisions.
Preserve current uncommitted work and explicit task file ownership. Coordinate
changes to shared interfaces with their owner before editing another workstream's files.

## Sprite and palette rules

- Use **one publisher per hardware channel per phase**. Current allocation:
  hero0–3; in PLAY enemy attached4/5 and hostile independent6/7; in BOSS hostiles
  own4–7 and the boss is a BOB. Use `logicHostileChannelMask()` for handover,
  including HERO_DYING's retained resume-phase ownership. Player fire is BOB-based.
- Current hostile pool32, capacity16 per bullet channel; do not increase the pool
  without changing the renderer's 32-bit membership masks and admission bounds.
- Hostiles are6×8. Before firing, admission reserves a channel for the entire
  straight trajectory. Every accepted on-screen hostile must remain drawable;
  `bullet_hidden` must be zero. Refuse an impossible ray before firing it.
- Attached enemies need their actual height plus blank scanlines between members.
  Six slots is capacity, not permission for vertical overlap or simultaneous waves.
- Six homogeneous members per formation, including six asteroids. Quotas are
  18/21/24/24, derived from the frozen historical fixture under `tests/fixtures/`.
  Boss entry waits for the final retirement, not `g_stageFrames` (historical only).
- Sector-specific five-wave cycles are in `../docs/campaign-expansion.md`.
  Enemy art has 24 frames (`level * 6 + kind`), including unused legacy boss slots.
- Holding fire only charges; release at 1–49 ticks requests a normal volley,
  at 50 a single six-damage lance. Normal releases retain the eight-tick cap;
  early releases are discarded. F (`BONUS_FIRE=4`) raises independent shotLevel
  0–2; P controls damage. Five kinds cycle P/F/S/R/L in four pickup slots.
  Normal offsets are 0, −6/+6, or −8/0/+8, all vx6/vy0; reserve the full volley
  atomically in the unchanged twelve-shot pool. HUD F1–F3 displays shot count.
- Sprite slots are sorted by Y. VSTOP fetches the next control pair; keep at least
  one blank line between hardware uses (logic reserves a larger safety margin).
- Write only the DMA buffer belonging to the **back copper list**, terminate with
  zero control words, publish, and wait for vblank acknowledgement before reuse.
- Hero/enemy attached colors share registers17–31. Independent4/5 use25–27;
  independent6/7 use29–31. The startup bullet conversion maps4/5 inks to existing
  hero palette colors. Preserve the attached hero's RGB values during handover.
- The pinned ACE branch remains a dependency, but current sprite rendering uses
  the game's custom DMA writer, not ACE's generic multiplexed-sprite manager.

## Blitter, BOBs and frame order

- Current display: **two 320×256×4bpp interleaved framebuffers**. For renderer,
  publication or memory work, read `../docs/rendering.md` and the actual
  `main.c`, `render.c/.h` interfaces before changing frame order.
- Bind the actual back bitmap after vblank. Before input/logic, acknowledge any
  published scene, restore this bitmap's N−2 BOB history, then animate the world.
  After logic/audio, compose scenes or update HUD/BOBs, then decor copper and
  hero/enemy/bullet streams; wait for blits, publish palette/copper, acknowledge vblank.
- `bobSetCurrentBuffer(back)` selects history by bitmap identity before
  `bobBegin(back)`. HUD/star histories and composition cursors are also per bitmap.
- Restore before touching stars/background; finish BOB submission before other
  blits. Scene transitions close open queues and discard undraw history before
  incremental clearing. Preallocate backgrounds; retain overlapping restore order.
- Composition advances only the bound back bitmap, at most 8 rows or 2 glyphs per
  step. Readiness requires both bitmaps; scene acknowledgement additionally requires
  publication. Keep preparation inside performance measurement; no per-tick full-screen copy.
- 16px BOBs use X<=303, 64px boss X<=255; ACE saves an extra aligned word.
  Recalculate width-specific bounds and save/restore storage for new geometry.
- Preserve restore order for overlapping objects and test removal/scene changes.
- Dirty HUD updates are important: score formatting avoids32-bit division and
  redraws changed glyphs only, preventing BOB work from missing its scanlines.
- Veil Nebula (level 1 / displayed sector 2) retains crystals in both bitmap
  composition and copper switches. Clear only corridor-connected inks 0/1 after
  crop/seam processing; retain enclosed ink-1 shadows and every other crystal ink.
  Keep ink 0 at #102, PLAY ink 4 at #BDF and existing HUD/play bounds.

## CPU, memory and audio

- DMA data (bitmaps, sprite streams, copper, audio) belongs in chip RAM. Other
  state may use slow RAM. No floating point, frame-loop allocations or OS calls
  while `systemUnuse()` owns the machine.
- Word/long accesses must be even-aligned. Audit generated68000 code for hidden
  `___mulsi3`/division calls after hot-path changes; C integer promotion matters.
- Measure, then optimize. Cache stable images/masks, use fixed-point motion and
  bounded loops. Keep gameplay code portable; isolate hardware-specific fast paths.
- Record memory before adding assets. The 147,456-byte phase bank is removed;
  decor now uses 57 copper commands and hardware fine scrolling. Four read-only
  title arrays (24,576 bytes) share one 6,144-byte CHIP staging bitmap, with bounded
  eight-row copies and original TITLE ink 4 (#568). The bitmap payload saving
  versus four CHIP plates is 18,432 bytes; ordinary data can still spill into CHIP.
  See `../docs/rendering.md` for the scoped memory ledger.
- Latest actual production A500 boot: 24,056 free chip / 30,112 total free bytes;
  initial executable 474,992 bytes. The art manifest retains runtime assets only;
  removed compiled legacy sections still have preserved source files.
  Obtain fresh telemetry for new allocations; startup readings are not a formal
  worst-case bound. Final evidence is in `../docs/campaign-acceptance.md`.
- Keep pinned ACE allocation safety reproducible through `tools/bootstrap.sh`.
  CMake guards generated art/audio locally (`art-safe.c`, `sound-safe.c`);
  main checks `astraSoundCreate()`. Preserve partial-failure cleanup and the
  global AGK installation. Host ASAN OOM coverage is not native fault injection.
- `tools/check-allocation-safety.py` passes all 15 audio allocation positions,
  BOB/bitmap faults and exact generated-array preservation under ASAN/UBSAN.
  Native OOM remains uninjected. Run this persisted check after allocation changes.
- Music uses PaulaA–C; reserve D/channel3 for prioritized SFX. Sprite channel IDs
  are unrelated to Paula IDs. Sector changes must preserve the user's mute state.
- MML sample paths resolve against `game/sound/`. Check every generated music
  module for accidental channel-D notes/samples; global tempo effects are allowed.

## Assets and references

- Preserve Retro Diffusion masters, prompts, seeds and hashes. See `art/RD-RICH.md`.
  Sector variants are offline derivatives; read `art/SECTOR-ENEMIES.md` for their
  24-frame layout and the authored fifth bonus frame, rather than attributing them to RD.
  Keep original ACE/Micrix intros and exact ACE PCM; licensing is documented in
  `art/intro/README.md` (including Micrix noncommercial/share-alike restrictions).
- Before paid image generation, verify current pricing and obtain a spending
  ceiling. Recover existing task IDs rather than resubmitting paid requests.
  Label placeholders honestly; they do not satisfy final manga/boss-art acceptance.
- For BOB changes, read pinned `vendor/ACE/include/ace/managers/bob.h`, its matching
  implementation and the installed kit's `techniques/bobs/TECHNIQUE.md` first.
- For DMA/palette changes, inspect `render_stream.h`, `render.c` and the art
  converter rather than assuming a generic ACE API owns the current channels.
- For campaign changes, read `../docs/campaign-expansion.md`. Large BOB bosses,
  explosions, 13 presentations and four-sector music are implemented. New art is
  original offline-generator work (`art/CAMPAIGN-ART.md`), not RD output; final
  artistic approval is separate from pixel checks and implementation.

## Build, tests and reporting

From the repository root:

```sh
bash tools/agk unit
bash tools/agk build
bash tools/agk test
bash tools/agk run -f game/tests/barrage.agk
python3 tools/verify-rich-art.py
python3.12 tools/verify-scrolling.py
python3.12 tools/verify-sector-presentation.py
python3.12 tools/make-title-plates.py --check
python3 tools/check-music-channels.py
python3 tools/check-ace-audio.py
python3 tools/check-allocation-safety.py
```

The wrapper uses `$AGK_KIT` or `$HOME/Code/amiga/amiga-game-kit`. Native builds
need Docker; kit imports require Python3.12. Host tests need no Amiga headers.
Project-local `tools/agk-launch.py` grants 6000 frames only for cold loading the
larger executable on AROS. Runtime 20 ms and strict performance budgets stay fixed.

After visible changes, inspect320×256 `*.screen.png` captures. Review each intended
change before scoped golden updates, then rerun both profiles without updates.
Never regenerate goldens blindly or treat an injected fixture as ordinary play.
Use pixel assertions and `tools/verify-bob-restoration.py` as well as goldens.
For title/decor changes, run `verify-sector-presentation.py` on both profiles:
it independently checks original title PNGs, right/left wrap, Nebula connectivity
and every band pixel. Keep `title_sectors.agk`'s 400-tick selection waits: bounded
recomposition must finish for both buffers before capture.
Replan joystick replays when rules change; retain genuine kills/collection checks.

`sync="ticks"` counts game iterations, not elapsed video frames. Keep
`agkPerfBegin()` first and `agkPerfEnd()` before the frame wait. Report `load`,
`maxload`, missed vblanks and which phase/window was measured. New performance
gates must cover crowded waves, all bosses, simultaneous effects, death pauses,
presentations and transitions with sound enabled. Paused gameplay must still draw
at50Hz; an intentional pause is not permission for a long synchronous stall.

For injected campaign coverage, read `../docs/campaign-native-fixture.md`.
`ASTRA_CAMPAIGN_PROBE` defaults OFF; keep hooks compile-time guarded and native
scenarios outside ordinary autodiscovery. The runner must rebuild OFF in `finally`
and report restoration failures. Verify OFF before distributing the ADF. Report
functional and strict-performance results separately; full ordinary campaign clear,
native OOM injection and formal worst-case free memory remain unproven.

On a new validation failure: report the exact failure and proposed correction
before changing code. Keep failures visible; do not silently relax assertions.
Do not commit or launch/terminate GUI emulators unless explicitly requested.
