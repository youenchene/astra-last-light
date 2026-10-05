# Rendering, publication and memory

This is the current double-framebuffer design, grounded in `game/src/main.c`,
`render.c/.h`, `render_bobs.c`, `render_world.c` and `render_scenes.c`.
Hardware constraints and change gates are authoritative in
[`game/AGENTS.md`](../game/AGENTS.md). Campaign functionality is delivered;
strict PAL 50fps acceptance remains blocked.

## Ownership

| Owner | Owned state / responsibility |
|---|---|
| `main.c` / ACE simplebuffer | View, viewport, two 320×256×4bpp interleaved bitmaps; input, logic/audio sequencing, publication and vblank wait |
| `render.c` | Shared blank sprite word, palette/copper coordination, phase routing and back-target binding |
| `render_world.c` | Decor/title/font assets; per-bitmap HUD cache, star pixel history and composition cursors; copper cache per physical list |
| `render_scenes.c` | Five manga panels; per-bitmap composition/animation history and two-buffer readiness |
| `render_bobs.c` | One BOB manager with separate background queues for the two bitmaps; shots/lances/pickups; boss/effect child lifecycle |
| `render_boss.c`, `render_effects.c` | Boss/flash and fixed-pool explosion assets/BOBs |
| Hero/enemy/bullet renderers | Their assets and double-buffered custom sprite DMA streams; phase-owned channel publication |
| `campaign_audio.c` | Post-intro music selection and mute continuity |

Child renderers borrow the view, screen and shared blank pointer; they free only
their own resources. Partial construction must be safe to destroy. The coordinator
uses a blank display-only state during composition without rewriting live gameplay
phase or collision state. Visibility feedback suppresses invisible collisions.

## Actual frame order

`genericProcess()` measures the whole iteration, including preparation:

1. `agkPerfBegin()`, then `renderBindBack(pBack)` binds world, scenes and BOBs to
   the unpublished bitmap.
2. After startup intros, acknowledge a ready scene epoch from the preceding
   published frame via `logicScenePresented()`. A ready composition alone is not
   a display acknowledgement; epoch zero is valid.
3. `renderAnimate()` runs only for a matching, ready world outside narrative
   scenes. `renderBobsBegin()` selects the queue with
   `bobSetCurrentBuffer(back)`, restores that bitmap's **N−2** background and waits
   for the blitter. Then `renderWorldAnimate()` updates/catches up its star pixels.
4. Process keyboard/joystick and intro state. Once intros are done, run
   `logicUpdate()`, campaign music selection and sound events. The intro-ending
   tick defers music setup to spread startup work over adjacent ticks.
5. `renderFrame()` follows one of two composition paths:
   - Narrative scene: close an open BOB frame, discard histories/invalidate the
     world when entering a new scene/epoch, begin if needed, then step the scene.
   - World: on mismatch close/discard BOB history before beginning incremental
     composition; update `presentationBusy` around `renderWorldStep()`, draw HUD
     when ready, then submit BOBs. Queue order is **boss → effects → pickups →
     shots/lances**, followed by `bobEnd()` and a blitter wait when a frame is open.
6. Publish back-list decor settings, then **hero → enemies → hostile bullets**.
   During preparation/scene display, publish empty sprite streams through the
   display-only phase gate.
7. Wait for blits, synchronize all 32 palette entries, mark simplebuffer pointers
   dirty, run `viewProcessManagers()` and `copProcessBlocks()`, then
   `agkPerfEnd()`.
8. Wait for `timerGet()` to advance: the new copper list must be acknowledged at
   vblank before the next iteration reuses buffers.

HUD caches, stars, BOB queues and composition cursors follow **bitmap identity**,
not odd/even logic ticks. Scene changes may bypass BOB drawing for many frames.
This is why the old same-front/back queue-flip cancellation rule is obsolete.
Incremental world/scene composition advances only the bound back target, in
bounded steps of up to eight rows or two text glyphs. Both bitmaps must be ready.
There is no per-tick full-screen copy. Logical pauses freeze simulation, not
display/effect/audio progress; missed video frames still stretch wall-clock time.

## DMA channels and decor

- Hero: attached channels **0–3**, 32×24 pixels.
- Enemy source: **24 16×16 frames**, indexed by `level * 6 + kind`; each sector
  includes an unused legacy-boss slot. Sector 1 retains original pixels; later
  variants are [offline derivatives](../game/art/SECTOR-ENEMIES.md).
- Normal combat: attached enemies/asteroids on **4/5**, independent hostiles on
  **6/7**. Boss combat: 64×48 BOB boss frees **4–7** for independent hostiles.
- `logicHostileChannelMask()` owns the phase handover. HERO_DYING retains its
  resume-phase mask while projectiles are cleared. Keep one publisher per channel.
- Hostile pool stays **32**, with 16 stream slots per channel and 32-bit membership
  masks. Admission reserves the full straight trajectory, preserving drawability.
- Independent 4/5 inks map to existing hero colors in **25–27**; 6/7 use **29–31**.
  The renderer does not overwrite attached hero palette RGBs to lend channels.

The custom **57-command copper reservation** performs four raster switches and
a PAL line-255 rollover guard. It fetches the sector-specific decor directly at
**y29–52 and y220–243**, restoring framebuffer pointers/modulo/fine-scroll state
after each band. Its 384×192×4bpp repeated source contains all four sectors and
guard pixels. Fine scrolling uses hardware fetch offsets and delay; the old
147,456-byte (144 KiB) sixteen-phase bank is gone. Startup/scene composition can still
blit bounded decor rows into a bitmap; ordinary scrolling does not rebuild phases.
PLAY advances decor/stars; bosses and both death phases retain positions.

**Veil Nebula (displayed sector 2, level 1) is the exception:** both bitmap
composition and runtime copper band switches are disabled. Ink 0 is `#102`;
all **15,360 tested band pixels** match it. HUD and play/collision bounds are
unchanged, and the original crystal PNG and four-sector decor strip are preserved.

The bonus strip now has five 16×16 masked BOB frames in enum order P/S/R/L/F,
while the pickup pool remains four slots and drops cycle P/F/S/R/L. Normal
shots use the twelve-slot BOB pool: F1/F2/F3 selects 0, −6/+6, or −8/0/+8
vertical muzzle offsets, all vx6/vy0, admitted as a whole volley. Holding fire
only charges; normal release is capped at one volley per eight ticks. The
centered 16×10 charged lance remains one projectile. HUD W still reflects damage;
F1–F3 reflects independent shot count, with the stage caption at x104.

## Memory ledger

These are payload calculations and **observed startup measurements**, not a formal
worst-case free-memory or allocation high-water proof. Allocator overhead,
descriptors, resident code/source data, queues and other assets matter too.

| Item | Chip payload / scope |
|---|---:|
| One 320×256×4bpp framebuffer | 40,960 bytes |
| Two framebuffers | 81,920 bytes |
| Removed old decor phase bank | −147,456 bytes |
| Current 384×192×4bpp decor source | 36,864 bytes |
| One common Graveyard title plate instead of four resident plates | −18,432 bytes |
| Second framebuffer less title-plate saving | +22,528 bytes, excluding descriptors and other changes |
| New four-sector music PCM | 13,624 bytes |
| All generated SFX + five songs | 75,948 sample bytes |
| Preserved original ACE intro PCM | 13,152 sample bytes |

Title sharing affects **only TITLE**. Original source plates are retained; all
four decor source sets, sector labels and five manga panels remain distinct;
Veil Nebula's gameplay bands are disabled.
The generated art source size is not its live allocation size: masks and BOB
save areas also consume memory. Audio MOD files include patterns/headers/PCM;
adding MOD bytes to PCM bytes would double-count samples.

`game/art/art.toml` now includes only runtime assets. Unused compiled sections
`player`, `fleet`, `shot`, `scene`, `actors16`, `nebula`, `foundry`, `citadel`
and `campaign_flash` were removed; every source file remains. In particular,
`actors16.txt` remains the authoring input, and active boss flashes still render.

Latest **production** initial executable: **456,792 bytes**. A500 boot telemetry:
**40,440 free chip bytes / 48,312 total free bytes**. These are actual startup
observations, not a formal worst-case bound or a calculation from source sizes.
AROS's extra fast RAM cannot prove baseline A500 fit.

## Allocation safety

`tools/bootstrap.sh` pins ACE at
`10ca68a321989738e9ac40f895bdd9f1d8e040fe`, applies the kit compatibility patch,
then reproducibly applies `tools/patches/ace-allocation-safety.patch`. The patch
preserves the pinned files' required line endings and supports repeat bootstrap.
Keep vendor changes reproducible here, rather than editing the global kit.

`game/CMakeLists.txt` guards generated constructors locally as `art-safe.c` and
`sound-safe.c`. The sound transform fails configuration if expected generator
anchors change. `astraSoundCreate()` reports failure, unwinds partial audio state
through `soundDestroy()`, and is checked before main marks sound initialized.
BOB creation checks `bobBuffersReady()` after allocation and supports cleanup.

The persisted `python3 tools/check-allocation-safety.py` passed under ASAN/UBSAN
for **15 audio allocation positions**, successful retries and BOB queue/bitmap
faults. It also verifies exact preservation of all **20 generated SFX/MOD data
arrays** between `sound.c` and `sound-safe.c`. Host stubs exercise allocation and
cleanup, not Amiga interrupt/hardware behavior. Native OOM has not been
fault-injected; a successful native startup does not prove every failure path.

## Validation boundary

The [native fixture](campaign-native-fixture.md) passes functional checks on both
profiles (40 captures each) but the latest strict command exited FAIL:
**A500 22 drops / 130% peak**, **AROS 17 drops / 123% peak**. Added F probes and
changed waves prevent like-for-like comparison with older measurements.
Zero drops and <=90% peak remain the unchanged
gate; runtime remains **20 ms** and global 50fps is not achieved.
The project-local `tools/agk-launch.py` uses **6000 frames for cold-load timeout**
to accommodate the larger executable on AROS. It does not relax gameplay timing
or modify the global AGK installation.

The latest ordinary production suite passed **36/36** shared-golden
tests; all **36 complete captures are byte-identical across profiles**. Keep that
result separate from injected coverage and strict performance. See the
[acceptance record](campaign-acceptance.md) for emitted ordinary-run timing,
commands and evidence paths. Inspect intended image changes before any scoped
golden update. The slower sector music is an artistic change with no proven
performance benefit; it has not closed the budget.
