# Rendering, publication and memory

Current localized primary/performance integration:
[merge evidence and production artifact](performance-integration-2026-10-11.md).
It retains160×96 stories, the current320×192 peach ending, English/French UI and
F9 alongside galaxies/36 movers and A2 score cells. Both-profile focused checks
pass; global50fps remains blocked. The older summaries below are historical.

## Accepted it9j fixed galaxies — global performance gate remains open

The `perf/combat-loop` Step D implementation preserves four selected RD masters,
painting their derivatives at y56–215. Then 36 retained moving stars XOR plane 2
over low inks 0–3.
Sparse nonzero spans have no framebuffer references, allocation or full CHIP staging.
Full/patch calls are bounded at 320 writes, 64 row/span operations and eight rows; a physical
bitmap owns each cursor. Opening close restores BOB history before clearing a
patch once, painting it and XORing that bitmap's historical stars. A per-bitmap
clear flag is an explicit painting precondition. The last patch and the first
heavy foreground/BOB draw are separate work steps before publication. Steady PLAY
does **zero galaxy decoding**. TITLE/WIN, HUD geometry and decor remain unchanged.

The source/palette contract is in [galaxy provenance](../game/art/galaxy/README.md).
Both-profile pixel/lifecycle checks pass. Campaign it7→it9j is **8/116%→7/116%**
A500 and **7/112%→6/110%** AROS (drops/peak load). Ordinary BOB reaches **0/95%**
A500 and **0/90%** AROS. Global 0-drop/90% acceptance remains open.
Measured first-target preparation is **3.00–3.02 seconds** by sector; both-target
preparation is **6.00–6.04 seconds**, including the existing story image composition.
S1 grows from 5.24 to 6.00 seconds for both targets. This excludes disk loading and
deliberate scene dwell. S1 closure is 0.72 seconds both targets versus it7's 0.68.
A500 free CHIP/total is **41,104/51,416 bytes**, versus it7's
51,616/64,072. No new CHIP allocation does **not** mean zero CHIP residency cost:
the **10,508-byte** ordinary-data bank spills into CHIP. A diagnostic A500 boot
reports code as PUBLIC|FAST (the baseline slow bank) and galaxy data as PUBLIC|CHIP.
Full details, rejected trials and unchanged hardware gates:
[combat performance, it9](combat-performance.md#it9--fixed-galaxy-step-d-accepted-at-it9j).

Latest story implementation: [selected RD 140×84 images and 320×192 WIN](selected-rd-story-images.md).
Five shared compressed images decode directly into the back bitmap; WIN clears
both targets and omits world/HUD/decor/sprites. Functional checks pass on both
profiles, including all 13 source-exact scenes and held-fire/restart/ESC. The
loader error-103/bank-placement failure is fixed by compression and a separate
ordinary-data hunk. Production is 487,888 bytes; A500 startup free CHIP/total RAM
is 51,616/63,432 bytes. Probe/timing flags are OFF. Performance work awaits the
parent commit. Older layout and validation sections below are historical.

This is the current double-framebuffer design, grounded in `game/src/main.c`,
`render.c/.h`, `render_bobs.c`, `render_world.c` and `render_scenes.c`.
Hardware constraints and change gates are authoritative in
[`game/AGENTS.md`](../game/AGENTS.md). Campaign functionality is delivered;
strict PAL 50fps acceptance remains blocked.

## Ownership

### P pause and larger panels — campaign validation blocked

The latest source adds manual P pause, first-target hero visibility, continuous
opening closure, stationary narrative ships and offline **112×64** panels within
the same window. Production pause/continuity checks pass on both profiles;
the injected A500 campaign has a new display/render startup allocation failure.
See [current behavior, memory, failure and unfinished validation](pause-ship-continuity.md).
The 96×56 descriptions below document the preceding accepted revision.

### Precomputed presentation — scoped validation passed

The current static-row implementation and fresh measurements are recorded in
[precomputed presentation](precomputed-presentation.md). Generated rows use at most
320 output bytes / 64 decode operations per call. Opening preparation falls from
6.68 s to **4.92 s**, with **zero title-latency drops** on both profiles. The
20,234-byte payload fits the original profiles: production A500 startup has
46,696 CHIP / 51,504 total bytes free. Fresh campaigns pass functionally; broader
performance remains blocked at 19/12 drops and 125% peak. Both diagnostic flags
are restored OFF. Earlier failed candidates and evidence are retained separately.

The latest UI keeps five **96×56** manga panels, scene-only **4×6** text, no entry
headings for scenes 0/3/6/9 and no continuation instruction. The opaque window is
(152,56)–(312,192); the image starts at (184,72). GAMEOVER is centered vertically.
Older layout/payload descriptions below are historical. All 13 complete native
windows pass independent source-pixel checks on both profiles, and 100 complete
captures per profile match exactly across profiles. Original two-buffer atomic
publication, dynamic HUD/stars, five shared manga sources, BOB and copper ownership
remain unchanged.

### Current playtest correction (focused functional validation passed)

See [playtest stabilization](playtest-stabilization.md) for fresh both-profile
source-pixel, live-opening, transition, GAMEOVER, BOB and scoped golden evidence.
Full campaign image review and performance acceptance remain separate gates.

TITLE now centers the intact 128×96 plate at (96,26), with a centered title,
prompts and sector caption below it. GAMEOVER keeps its existing layout. The
source validator checks all 12,288 plate pixels rather than the old partly
occluded 8,928 pixels.

Story windows occupy (152,56)–(312,192). Five 80×48 panels are exact offline
2:1 nearest-neighbor derivatives of the preserved 160×96 masters, with unchanged
palette indices and word-wrapped 1× text for all 13 beats. The manga strip payload
falls from 38,400 to 9,600 CHIP bytes; fresh native free-memory evidence is pending.

Acknowledged sector openings permit hero motion and release fire while stage,
enemy and combat clocks remain frozen and no waves spawn. The hero and shot BOBs
are occluded when their bounds intersect the opaque window. Other stories remain
blocking. Live BOBs restore the actual back bitmap before each draw. Closing an
opening restores each bitmap's BOB history, then repairs only the window at eight
rows per step using its frozen star history, preserving the atomic publication
and second-target acknowledgement gate. This is a bounded window-close pause,
not a second full-world reconstruction. No new framebuffer or runtime allocation
was added. Existing historical evidence below does not validate these changes.

| Owner | Owned state / responsibility |
|---|---|
| `main.c` / ACE simplebuffer | View, viewport, two 320×256×4bpp interleaved bitmaps; input, logic/audio sequencing, publication and vblank wait |
| `render.c` | Shared blank sprite word, palette/copper coordination, phase routing and back-target binding |
| `render_world.c` | Decor/title/font assets; per-bitmap HUD cache, star pixel history and composition cursors; copper cache per physical list |
| `render_scenes.c` | Five manga panels; bounded static-window composition per bitmap and two-buffer readiness |
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
2. Acknowledge only a preceding actual publication after vblank. Both-target
   readiness clears `presentationBusy` and acknowledges the scene epoch via
   `logicScenePresented()`. A ready hidden composition alone is not a display
   acknowledgement; epoch zero is valid. Ready telemetry is emitted here.
3. `renderAnimate()` runs only for a matching, ready world outside narrative
   scenes. `renderBobsBegin()` selects the queue with
   `bobSetCurrentBuffer(back)`, restores that bitmap's **N−2** background and waits
   for the blitter. Then `renderWorldAnimate()` updates/catches up its star pixels.
4. Process keyboard/joystick. Campaign music follows the acknowledged visible
   phase/sector before logic, including mute toggles. The first theme is selected
   on the first complete title's acknowledged display tick, while second-buffer
   repair remains pending. Intro exit retains its last complete frame and palette;
   it neither clears the screen nor writes the active palette. There is no fixed
   handoff timer. Micrix retains its fade-in and 100-tick stage but no longer fades
   to black before title preparation; the outgoing logo stays legible until the
   clean cut. Original PCM allocation and intro skip latches are retained.
5. `renderFrame()` follows one of two composition paths:
   - Narrative scene: close an open BOB frame, discard histories/invalidate the
     world when entering a new scene/epoch, then rebuild the frozen world before
     composing the static window. Incoming sector scenes use incoming scenery.
     A tick advances either world or window, never both bounded steps.
   - World: on mismatch close/discard BOB history before beginning incremental
     composition; set `presentationBusy` until publication acknowledgement, draw
     HUD on complete non-TITLE targets, then submit BOBs. Queue order is **boss → effects → pickups →
     shots/lances**, followed by `bobEnd()` and a blitter wait when a frame is open.
6. Publish back-list decor settings, then **hero → enemies → hostile bullets**.
   Incomplete targets and narrative windows use empty sprite streams through the
   display-only phase gate. The preceding visible list and streams remain untouched.
7. Wait for blits. If the target is incomplete, skip **both**
   `viewProcessManagers()` and `copProcessBlocks()`. Otherwise synchronize all 32
   back-list palette entries, mark pointers dirty and call both publication paths.
   Then `agkPerfEnd()`. The actual pinned simplebuffer swaps even with no dirty
   pointers, and raw copper processing unconditionally swaps lists: gating only
   dirty flags would corrupt bitmap/DMA identities.
8. Wait for `timerGet()` to advance: the new copper list must be acknowledged at
   vblank before the next iteration reuses buffers.

HUD caches, stars, BOB queues and composition cursors follow **bitmap identity**,
not odd/even logic ticks. Scene changes may bypass BOB drawing for many frames.
This is why the old same-front/back queue-flip cancellation rule is obsolete.
Incremental world/scene composition advances only the bound back target, in
bounded steps of up to eight rows or two text glyphs. First-target completion
permits a clean cut; that image is held while the old visible bitmap is repaired
offscreen. Both bitmaps must be ready and acknowledged before simulation resumes.
There is no per-tick full-screen copy. Logical pauses freeze simulation, not
display/effect/audio progress; missed video frames still stretch wall-clock time.

### Static story windows and TITLE

TITLE omits both initial and dirty HUD drawing (score, lives, charge and upgrades).
The original illustration/prompts remain, with a sector-name caption at y232.
Gameplay keeps its HUD. All 13 narrative beats retain their text and five panels
inside an opaque `(24,56)`–`(296,216)` window. The 160×96 image begins at `(80,78)`.
Scanner/glint animation is removed. Sector palette, stars, HUD and copper bands
remain frozen; hardware entities are blanked while the window is visible. Exit
rebuilds the same frozen scenery with the same bounded, hidden publication path,
discarding stale BOB histories before composition. No third framebuffer, screen
copy, runtime allocation or black interstitial is introduced.

Focused publication/pixel checks pass on both profiles, as do all 13 static-scene
pairs in the fresh 53-capture-per-profile injected fixture. Strict performance
remains blocked (A500 16 drops / 123% peak; AROS 11 drops / 120% peak).
`cut_hold`, `cut_target_ready`,
`cut_submit`, `cut_visible`, `cut_work` and `music_visible` expose physical bitmap/
copper identities and vblank clocks. `tools/verify-clean-transitions.py` checks
repair/publication order, music-controller invocation alignment, complete-frame
holds, TITLE HUD absence and static scene/restored exterior pixels. Controller
timestamps alone do not prove exact Paula sample onset or 50fps performance.

The ordinary [BOB replay correction](bob-replay-validation.md) now verifies real
six-kill bonus creation/collection, all 256 pickup artwork/mask pixels and the
full 768-pixel aligned background restore region on both profiles. It also checks
the 150-tick scene and 40-tick death lifecycle against complete wrapped telemetry.
The replay models the ready acknowledgement's neutral update rather than adding
an arbitrary wait or pixel offset. Runtime rendering and balance are unchanged.

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

**Veil Nebula (displayed sector 2, level 1)** retains its crystal artwork in both
bitmap composition and runtime copper band switches. After the existing 64×24
crops, seam normalization and two-row corridor clearance, the importer traverses
only corridor-connected inks 0/1 with four-neighbor horizontal wrapping. It maps
**544 ink-1 pixels to ink 0** (293 top / 251 bottom), retaining **158 disconnected
ink-1 shadow pixels** (53 / 105) and every other crystal ink. The original PNG is
unchanged. Ink 0 is `#102`; HUD and play/collision bounds are unchanged.

TITLE uses the four original 128×96 PNG illustrations selected by sector.
`tools/make-title-plates.py` emits four read-only 3,072-word arrays, with frame zero
matching the old generated Graveyard words. One 6,144-byte CHIP staging bitmap
serves all four: each composition step copies eight aligned rows (512 bytes),
then blits to **(184,56)**. Both framebuffer histories must finish recomposition.
The existing panel covers the illustration where x<296 and y>=122; the remaining
**8,928 pixels per title** are checked exactly against the source PNG and palette.
The checker uses its own quantization, not the generated title header.
Palette 0 is `#001/#102/#101/#001` by sector. TITLE preserves original palette 4
(`#568`); PLAY retains live palette 4 (`#BDF`) for stars and matching decor inks.

The bonus strip now has five 16×16 masked BOB frames in enum order D/S/R/L/F,
while the pickup pool remains four slots and drops cycle D/F/S/R/L. Normal
shots use the twelve-slot BOB pool: F1/F2/F3 selects 0, −6/+6, or −8/0/+8
vertical muzzle offsets, all vx6/vy0, admitted as a whole volley. Holding fire
only charges; normal release is capped at one volley per eight ticks. The
centered 16×10 charged lance remains one six-damage projectile. HUD DAMAGE at
(8,249) labels the unchanged `weaponLevel` value 0–2 at x44; FIRE reflects
independent shot count 1–3. The D badge replaces only the legacy P letter;
`BONUS_POWER`, numeric levels, capture names and rendering lifecycle are unchanged.

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
| One shared title staging bitmap | 6,144 bytes |
| Title CHIP bitmap payload saved versus four resident plates | −18,432 bytes |
| Four read-only title arrays (ordinary data, not CHIP-attributed) | 24,576 bytes |
| Second framebuffer less title-plate saving | +22,528 bytes, excluding descriptors and other changes |
| New four-sector music PCM | 13,624 bytes |
| All generated SFX + five songs | 75,948 sample bytes |
| Preserved original ACE intro PCM | 13,152 sample bytes |

Title staging is shared, but the four title illustrations, decor sets, sector
labels and five manga panels remain distinct. Read-only data still consumes
resident memory and may spill into CHIP on the baseline machine: the bitmap
payload saving does not imply unchanged free CHIP telemetry.
The generated art source size is not its live allocation size: masks and BOB
save areas also consume memory. Audio MOD files include patterns/headers/PCM;
adding MOD bytes to PCM bytes would double-count samples.

`game/art/art.toml` now includes only runtime assets. Unused compiled sections
`player`, `fleet`, `shot`, `scene`, `actors16`, `graveyard`, `nebula`, `foundry`, `citadel`
and `campaign_flash` were removed; every source file remains. In particular,
`actors16.txt` remains the authoring input, and active boss flashes still render.

The title PNGs now supply `title-plates.h`; removing the remaining `graveyard`
manifest entry avoids a second compiled copy of that source.

Clean-presentation **production** initial executable: **477,368 bytes**. A500 boot
telemetry: **23,752 free chip bytes / 27,712 total free bytes**. Earlier four-title
build: 474,992 bytes, 24,056 free chip / 30,112 total free. Previous common-title build:
456,792 bytes, 40,440 free chip / 48,312 total free. These are actual startup
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

The fresh [native fixture](campaign-native-fixture.md) passes functional checks on
both profiles (53 captures each) but the strict command exited FAIL:
**A500 16 drops / 123% peak**, **AROS 11 drops / 120% peak**. Changed fixture
captures and preparation prevent like-for-like comparison with older measurements.
Zero drops and <=90% peak remain the unchanged
gate; runtime remains **20 ms** and global 50fps is not achieved.
The project-local `tools/agk-launch.py` uses **6000 frames for cold-load timeout**
to accommodate the larger executable on AROS. It does not relax gameplay timing
or modify the global AGK installation.

The historical ordinary production suite passed **38/38** shared-golden
tests; all **42 complete captures were byte-identical across profiles**. This
predates the latest balance/presentation work; the fresh scoped suite passes
10/10 boot/skip/title-sector/music/ACE-audio cases. Keep that
result separate from injected coverage and strict performance. See the
[acceptance record](campaign-acceptance.md) for emitted ordinary-run timing,
commands and evidence paths. Inspect intended image changes before any scoped
golden update. The slower sector music is an artistic change with no proven
performance benefit; it has not closed the budget.

`tools/verify-sector-presentation.py` independently derives Nebula crops from
`rd_decor1.png` and uses fixed-point set expansion to validate the importer's
connectivity mask and exact derivative. It then checks all 15,360 native band
pixels, finding one unique 64-tile horizontal phase per band; their circular
phase distance must be at most one. There are no pixel exclusions in these bands.
`tools/verify-scrolling.py` reuses that assertion and retains the existing sector-1
four-pixel movement, four parallax rates, hero colors and title-without-decor checks.
`title_sectors.agk` waits up to 600 ticks for initial `title_ready`, then 400 ticks
after each selection for bounded two-buffer recomposition. Its six complete
captures cover the four titles and right/left wraps with shared goldens.
