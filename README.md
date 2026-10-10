# ASTRA: LAST LIGHT

An original horizontal space-opera shooter for the **Amiga A500 / OCS**, inspired
by the deliberate dodging and charged fire of R-Type. The expanded four-sector
campaign has **all 11 functional features implemented**. **Performance acceptance is BLOCKED:**
locked PAL 50fps is not yet achieved. This is not a finished commercial game.

Built with [Amiga Game Kit](https://github.com/codebase/amiga-game-kit) and
[ACE's `feat/multiplexed-sprites` branch](https://github.com/youenchene/ACE/tree/feat/multiplexed-sprites).
The boot sequence includes adapted **ACE** and **Micrix Production** intros from
[SuperRugbyV](https://github.com/youenchene/SuperRugbyV).

## Play this build

The built bootable disk is **`game/build/astra.adf`**. Load it as DF0 in an A500
emulator: PAL, OCS, 512 KB chip + 512 KB expansion RAM. A licensed Kickstart 1.3
or AGK's free AROS profile is required. No ROM is included.

The **campaign preview with audio** is available at
`game/build/astra-demo.mp4`. Reproduce it with:

```sh
bash tools/agk record game/demo/campaign-preview.agk game -o game/build/astra-demo.mp4
```

This ordinary-input preview shows the original intros, title, first manga scene
and combat. `game/demo/showcase.agk` remains the verified no-cheat six-wave/pickup
flight; neither recording is a full-campaign or all-level demonstration.

With the installed kit:

```sh
bash tools/agk play
```

| Input | Action |
|---|---|
| Joystick port 2 / arrow keys | Move |
| Fire / Space | Start; in combat hold to charge, release after 1–49 ticks for a normal volley |
| Hold until READY (50 combat ticks), then release | One charged lance, six damage |
| M | Toggle game music |
| Left / right on title | Select starting sector (campaign defaults to 1) |
| Fresh fire press during an intro | Skip that intro only |
| Release, then press fire in a campaign scene | Skip after 25 acknowledged display ticks |
| Game over | Automatically return to title after 150 ready ticks; release/fresh fire can dismiss after 25 |
| Fire after victory | Restart from sector 1 |
| Escape | Return to AmigaOS |

### Four sectors

| Sector | Setting | Waves before boss | Boss behavior |
|---|---|---:|---|
| Orbital Graveyard | Scrolling wrecked hull plating and running lights | 18 | Salvage Claw: aimed fans, slow vertical patrol |
| Veil Nebula | Scrolling crystal borders against a dark-violet starfield | 21 | Manta: five-ray chevrons |
| Imperial Foundry | Scrolling girders, pipes and furnace vents | 24 | Furnace Carrier: dense aimed fans and slow lunges |
| Stellar Citadel | Silver armor and luminous reactor borders | 27 | Reactor Crown: aimed fans and lane barrages |

Three lives, brief respawn immunity, score, charge gauge, boss health bar,
sector-clear transitions, final victory, and restart are implemented. Each sector
has a distinct **64×48 masked BOB boss**, with a **six-tick white damage flash**.
Their health is **108 / 168 / 216 / 240**:
**18 / 28 / 36 / 40 landed charged shots** at six damage each. The latest HP
increase affects only sector 2 and 3 bosses; ordinary enemy HP is unchanged.

Eight explosion slots provide six small enemy/asteroid effects plus reserved
hero and boss effects. Hero death pauses simulation for **40 ticks**, boss death
for **75 ticks**, while display, effects and audio continue. Thirteen narrative
scenes cover sector entry, boss arrival, boss defeat and victory, using five
distinct locally authored manga-style panels with scanner/glint animation.
Scenes dwell for **150 ticks after display acknowledgement**; victory remains
until a fresh fire press. Composition time is separate from that dwell.
After the last 40-tick hero explosion, GAME OVER waits for composition, then
returns to the default title after 150 ready ticks. Score, lives and upgrades
reset; held fire/direction cannot carry through into a new game. Release fire
after the returned title is ready, then press again to start. Mute is preserved.

Waves contain **six members of one enemy type**, including **six asteroids** on
asteroid waves, beginning half a second into
the stage, with minimum intervals of **3.0 / 2.8 / 2.6 / 2.4 seconds** by sector. A
due formation waits until every previous enemy has retired. Charged
shots have a bright animated **16×10** silhouette, travel more slowly than normal
shots, and have their own launch sound. The HUD flashes **READY / RELEASE FIRE**.
Timings are nominal at **50 game ticks/second**; missed frames stretch real-time durations.
The boss starts after the exact sector quota and final retirement. Quotas are
18/21/24/27: the first three triple the measured no-fire reference (6/7/8/8),
and the fourth adds three waves for increasing difficulty. See
[campaign expansion status and reference](docs/campaign-expansion.md) for delivered
behavior and the remaining acceptance gates.

Scouts, weavers, gunners, darts and asteroids follow a distinct five-wave cycle
per sector, with six passive asteroids every fifth wave; see the
[cycle table](docs/campaign-expansion.md#sector-cycles-and-player-fire). Only one homogeneous
formation is active, with movement confined to vertically separated lanes. Enemy movement and
boss paths use **16/17/18/20 movement steps per 20 combat ticks** by sector
(80%/85%/90%/100% of the half-speed base). Independent firing countdowns advance
every combat tick, including skipped movement ticks:

| Sector | Ordinary rays (other/gunner) | Ordinary period | Boss fan rays | Boss period | Boss HP |
|---|---:|---:|---:|---:|---:|
| 1 | 3/5 | 96 | 5 | 64 | 108 |
| 2 | 5/5 | 76 | 7 | 52 | 168 |
| 3 | 5/7 | 64 | 7 | 44 | 216 |
| 4 | 7/7 | 52 | 9 | 36 | 240 |

Periods are combat ticks. Initial delays are 50 + 10 × formation member for
ordinary ships and 50 for bosses. Sector 4 retains its alternate boss lane barrage.
Hero, projectile, pickup and world speeds retain their previous rates. Initial
stagger is independent of motion; trajectory admission means these
cadences do not promise exact accepted bullet totals. Each hostile is **6×8 pixels**,
twice the previous width and height. Origins are 22px apart vertically and outer
rays trail by 6px per step, leaving at least 14px gaps within a fan. The hero's
damage core remains 8×8. Bosses use five/seven/nine-ray chevrons or 32px lanes.
Out-of-corridor rays are skipped instead of stacked at the edge. Asteroids remain passive.
Holding fire only charges: no shot fires on press or while held. Normal releases
are capped at one volley per eight combat ticks; an early release is discarded.
F upgrades select a centered single shot, double offsets −6/+6, or triple
offsets −8/0/+8, all at vx=6, vy=0. The twelve-shot pool admits a whole volley
atomically or emits neither projectiles nor a firing sound. Charged fire stays
one centered 16×10 lance at vx=4, damage six, regardless of F or P upgrades.

The **32×24 vessel** is twice as wide as the earlier model and uses the same
Retro Diffusion master at higher resolution. It moves at **1.5 pixels/tick**
before upgrades, with half-pixel accumulation for precise controls. Its central
**8×8 hurtbox** makes dense bullet patterns fairer; pickups use the full body.

**There is no static galaxy picture during gameplay or boss fights.** Top and
bottom 24-pixel decor bands in all four sectors share **the same 0.25-pixel/tick leftward speed**,
using copper-controlled hardware fine scrolling. Decor and stars freeze during
boss fights and death pauses. Neither band is drawn or animated on the title.
Left/right title selection displays the corresponding original Graveyard, Nebula,
Foundry or Citadel illustration. Four read-only sources share one 6,144-byte CHIP
staging bitmap, copied in bounded eight-row steps during composition.
Sector 2 (Veil Nebula) retains both crystal bands. Only corridor-connected dark
background is cleared to ink 0 (`#102`), preserving enclosed shadows and all other
crystal inks; HUD and play/collision bounds stay unchanged.

**96 parallax stars** move in four layers at **1/8, 1/4, 1/2 and 1 pixel/tick**,
with phase-staggered updates and randomized deterministic placement. They use
direct **bitplane pixels, never sprite channels**. A bright playfield palette
slot keeps the dense field legible without touching the sprite palette.
The hero, six enemy/asteroid masters and four corridor masters were
generated with **Retro Diffusion**, then fitted to the Amiga format. Original
PNGs, prompts, seeds and conversion provenance are preserved in
[the rich-art record](game/art/RD-RICH.md).
Enemies now use a **24-frame 16×16 sector strip**: six slots per sector, including
one unused legacy-boss slot. The first sector retains original pixels; later
sectors are [offline-authored derivatives](game/art/SECTOR-ENEMIES.md).

### Wave-clear bonuses

Shoot down **every member of a fully spawned formation** to release one
collectible at the last enemy's position. An escaped member, truncated spawn,
or cancelled wave disqualifies that formation. Eligibility is tracked per wave;
lingering bullets or previous pickups do not block a reward.

| Badge | Boost | Cap |
|---|---|---|
| **D** | Damage: normal shots deal 1 → 2 → 3 damage | Two upgrade levels |
| **F** | Fire pattern: single → double → triple normal volley | Two upgrade levels |
| **S** | Speed: movement increases 1.5 → 2 → 2.5 pixels/tick | Two upgrade levels |
| **R** | Resistance: shield absorbs a hit instead of losing a life | Two charges |
| **L** | Extra life | Five lives |

Drops cycle D → F → S → R → L. Fly into the badge to collect it. The footer's
**DAMAGE / SPEED / SHIELD** counters show upgrade levels (DAMAGE stays 0–2); **FIRE** shows
the independent normal-shot count. Upgrades persist
between sectors; losing a life reduces damage, fire-pattern and speed by one level. A shield
hit consumes one charge and grants brief immunity. New games reset upgrades.
Uncollected bonuses drift left and expire after 400 ticks or leaving the screen;
boss/sector transitions and game over clear uncollected pickups. If all four
pickup slots are full, the oldest is replaced.

## Sprite implementation

- **Attached channels 0–3:** one logical, animated **32×24 hero**, made of two
  adjacent 16-pixel attached columns.
- **Attached pair 4/5 in normal combat:** enemies and asteroids, capacity six.
- **Independent hostile channels:** 6/7 in normal combat, **4–7 during BOB boss
  fights**, capacity 16 per channel within the unchanged 32-hostile pool.
  Channels 4/5 map bullet inks to existing registers **25–27**; 6/7 use **29–31**.
  Hero palette RGB values are preserved.
- Hero and enemies use **4bpp/16-color sprite mode: 15 visible palette colors plus transparency**.
  Each frame uses the subset its artwork needs; the hero currently displays twelve
  opaque shades, verified from emulator pixels. All attached sprites share 17–31.
- Pools: 18 enemy slots, 12 player shots, **32 individual hostile bullets**, four
  pickups. Each hostile entity has one 6×8 image and one collision rectangle.
  Telemetry reports accepted `hostile_bullets` directly, without multiplying it.
  `bullet4` through `bullet7` and `enemies` report accepted objects; wave changes trigger
  state reports. One enemy and two bullet intervals can overlap vertically.
  `bullet_hidden` must remain zero for on-screen hostiles; `shot_bobs` counts
  visible player projectiles.
- Hostile admission checks the full straight trajectory before firing and binds
  the bullet to an allowed phase-owned channel for its lifetime. It reserves 11px vertical
  separation on each channel, including a rounding margin. A ray that cannot
  stay displayable is not fired: bullets do not alternate between visible and
  hidden frames when channels fill up. Hardware overlap limits still apply.
- Player shots and charged lances are masked BOBs, independent of sprite
  admission. Their artwork retains the playfield palette's full colors.
- Raw copper shares sprite pointers and all 32 palette entries. Backgrounds,
  text and stars use **two 320×256 interleaved four-plane framebuffers**, with
  separate HUD, star and BOB-restore history per bitmap. Bonuses are masked
  **16×16 BOBs**. Their X limit is 303; the 64px boss limit is 255 because ACE
  saves an extra aligned background word. Bounds depend on object width.
- Copper publication is acknowledged at vblank before the next logic tick.
- A custom **57-command copper reservation** fetches decor at y29–52 and
  y220–243, then restores framebuffer fetch settings. The old **147,456-byte
  phase bank is removed**. See [rendering and memory](docs/rendering.md).

Sprite streams now use the game's small, double-buffered DMA writer rather than
ACE's generic multiplexer. Slots cache pixel data and update control words in
ascending Y order. The ACE branch remains pinned to `10ca68a321989738e9ac40f895bdd9f1d8e040fe`, with the
AGK compatibility patch and the reproducible project allocation-safety patch
applied by `tools/bootstrap.sh`. The global AGK installation is untouched.
See `dependencies.lock` and [allocation ownership](docs/rendering.md#allocation-safety).

### Hardware sprites versus bitplanes / BOBs

| Drawing method | Contents |
|---|---|
| Hardware sprites, channels 0–3 | One logical 32×24 hero, using two attached columns |
| Multiplexed attached pair 4/5 | Enemies and asteroids during normal combat |
| Independent multiplexed channels 6/7, or 4–7 in boss combat | Individual 6×8 hostile bullets |
| Copper bitplane fetch switches | Hardware-scrolled top/bottom decor bands |
| Bitplanes, blitter copies | Title/manga artwork, bounded scene composition and HUD labels |
| Bitplanes, CPU pixel updates | 96 parallax stars, font/HUD pixels and ACE/Micrix logo artwork |
| BOB manager | Player shots, charged lances, four pickups, large bosses, flashes and eight effects |

The full-color hero consumes four hardware channels, leaving one attached enemy
pair and two independent bullet channels in normal combat, or four independent
bullet channels during boss combat. Multiplexing reuses these vertically;
it does not remove same-scanline overlap limits. Sprite-palette indices 7/13 and
11/14 are swapped during conversion, preserving original hero/enemy RGB colors
while exposing bullet colors in registers 29–31.

The BOB manager selects restore history by the actual back bitmap's identity.
It restores that bitmap's N−2 background before world animation, then draws the
updated state. Scene changes discard saved backgrounds before incremental
composition. Buffers are preallocated; there are no per-frame full-screen copies.

## Build and test

Requirements: a working AGK installation, Python 3.12, Docker and the kit's
toolchain/emulator setup. Tested kit revision:
`4d825a05a8d8dfcf8d824d70f0cb53b2f350fc7a`.

```sh
export AGK_KIT=/path/to/amiga-game-kit
bash tools/bootstrap.sh  # fetch pinned ACE, apply compatibility + allocation-safety patches
bash tools/agk build     # generates art + SFX and game/build/astra.adf
bash tools/agk unit      # portable C behavior tests
bash tools/agk test      # A500 + AROS, shared image baselines
python3.12 tools/verify-scrolling.py  # real leftward movement + hero color checks
python3.12 tools/verify-sector-presentation.py  # original titles + exact Nebula crystal/background pixels
python3.12 tools/make-title-plates.py --check
python3 tools/verify-rich-art.py     # remapped 4bpp/2bpp pixels and BOB masks
python3 tools/check-music-channels.py
python3 tools/check-ace-audio.py
python3.12 tools/verify-bob-restoration.py \
  --drop game/build/agk/a500/bob_restore/bonus_drop.screen.png \
  --restored game/build/agk/a500/bob_restore/bob_restored.screen.png
```

The wrapper defaults to `$HOME/Code/amiga/amiga-game-kit` if `AGK_KIT` is unset.
Bootstrap never downloads Kickstart, and refuses to overwrite a different ACE
revision. The `vendor/` checkout and build artifacts are intentionally ignored.

The project-local `tools/agk-launch.py` raises the **cold-load allowance to 6000
frames** so AROS can load the larger executable. This is boot compatibility only:
the runtime **20 ms** frame budget and strict performance thresholds are unchanged.
CMake builds guarded generated `art-safe.c` and `sound-safe.c`; startup checks
`astraSoundCreate()` and cleans up partial allocations on failure.

Repeat the BOB checker with `a500-aros` paths for the second profile. Its replay
evidence lives in `game/tests/bonus-flight.json`, not the ignored build directory.
To regenerate the deterministic no-cheat replays and evidence:

```sh
cc -std=c99 -Wall -Wextra -Werror -Igame/src tools/plan-bonus-flight.c \
  game/src/logic.c -o game/build/plan-bonus-flight
game/build/plan-bonus-flight --write
```

## Music and sound

Ten original synthesized effects are integrated: shots, explosions, damage,
charge-ready, charged-shot launch, warp, Micrix rise/sparkle, bonus appearance
and bonus collection. The ACE
logo uses the **original SuperRugbyV ACE splash sample**, not a generic sweep:
the PCM is preserved exactly and plays at its original 6 kHz rate.
Audio assertions verify
audible firing in the emulator, not just calls to a sound API.

**“Astra Dusk Signal” remains the title theme.** Mysterious synthwave: detuned open-fifth
pads, sparse echo-like lead phrases, rounded bass, soft kick and hushed snare.
An original **96 BPM E-minor, sixteen-bar / forty-second loop** is included as
`game/sound/theme.mml`. Generate/listen with:

```sh
bash tools/agk sound
# Open game/build/sound/preview/theme.wav in your audio player.
```

Music starts after both intros and can be muted with **M**. Four original sector
arrangements are integrated: **Graveyard Relay, Parallax Veil, Alloy Oracle and
Horizon Engine**. Each continues through its sector's boss, death and narrative
scenes; mute state survives transitions. Music uses Paula A–C, leaving D for SFX.
The four scores add **13,624 PCM bytes** without duplicating the old theme bank.
Generated SFX and all five songs total **75,948 sample bytes**, plus **13,152**
for the preserved ACE intro PCM. This is a sample inventory, not total RAM use.
Sector tempos are **96 / 88 / 104 / 112 BPM**, with sixteen-bar loops of
**40.00 / 43.64 / 36.92 / 34.29 seconds**, supporting the slower, mysterious tone.
No performance benefit from the tempo change has been established; it has not
closed the frame budget. See [music sources and arrangements](docs/music.md) and
the [campaign status](docs/campaign-expansion.md).

## Validation and remaining work

The evidence below predates the new GAMEOVER lifecycle and per-sector motion,
independent firing and boss-HP balance. Revalidate native replays and screenshots against this source;
historical passes do not establish acceptance of the balance changes.

- **Latest ordinary production suite: 38/38 shared-golden tests PASS**
  across A500 and AROS, including intros/audio, combat, scrolling and a genuine
  joystick wave-clear/pickup replay. All **42 complete captures are byte-identical
  between profiles**.
- **Injected native campaign fixture: functional PASS on both profiles**, with
  all **40 captures per profile**, 13 acknowledged scenes, F badge/F2/F3, all bosses/flashes,
  six simultaneous small effects, eight hero deaths and four boss deaths.
  This non-shipping fixture injects state and is **not an ordinary campaign clear**.
  See [coverage and reproduction](docs/campaign-native-fixture.md).
- **Strict performance FAIL:** the latest fixture recorded **22 drops / 130%
  peak load on A500**, **17 drops / 123% on AROS**. Added F probes and different
  waves prevent a like-for-like comparison with the earlier fixture. The strict command ran and
  exited with failure. Acceptance requires zero
  drops and at most 90% peak load. Runtime remains 20 ms; `perf.agk` covers only
  the stable ACE intro and cannot certify the campaign.
- `python3 tools/check-allocation-safety.py` **PASS** under ASAN/UBSAN: all **15
  audio allocation positions**, BOB/bitmap faults and exact preservation of all
  20 generated SFX/MOD data arrays. Native OOM has **not** been fault-injected.
- Source-derived presentation checks pass on both profiles: **8,928 unobscured
  pixels per title**, four distinct originals, both selection wraps, and all
  **15,360 Nebula band pixels**. Only six new title goldens and the corrected
  sector-2 golden were accepted after inspection.
- Latest production A500 boot: **24,056 free chip bytes / 30,112 total free bytes**;
  initial executable **474,992 bytes** with four read-only title sources.
  This is actual startup telemetry, not a formal worst-case free-memory/high-water
  proof. See [memory accounting](docs/rendering.md#memory-ledger).
- Full ordinary native campaign completion, real-hardware validation and final
  artistic approval remain unclaimed. Functional delivery does not complete all
  acceptance tasks or establish locked 50fps.

The [final acceptance record](docs/campaign-acceptance.md) lists commands, evidence
paths and ordinary-run timing, including intros, preparation and transitions.

## Code organization

| Module | Responsibility |
|---|---|
| `game/src/main.c` | Lifecycle, input, audio events, intro sequencing and frame publication |
| `game/src/logic.c/.h` | Portable game rules, movement, collisions, waves, bonuses and scheduling |
| `game/src/render.c/.h` | Rendering coordinator; owns blank buffer, copper and palette publication |
| `game/src/render_stream.c/.h` | Double-buffered sprite DMA storage, cached pixels, inline control-word writer |
| `game/src/render_hero.c/.h` | Player-ship assets, animation, blink, position and owned sprite resources |
| `game/src/render_enemies.c/.h` | Attached enemy stream on 4/5 and visibility feedback |
| `game/src/render_bullets.c/.h` | Phase-owned independent 2bpp streams on 6/7 or 4–7 and visibility feedback |
| `game/src/render_bobs.c/.h` | Shared BOB manager and per-bitmap saved-background queues |
| `game/src/render_boss.c/.h`, `render_effects.c/.h` | Large boss/flash and bounded explosion BOBs |
| `game/src/render_world.c/.h` | Backgrounds, scrolling decor, parallax stars, fonts, panels and HUD |
| `game/src/render_scenes.c/.h` | Incremental double-buffered narrative composition and panel animation |
| `game/src/campaign_audio.c/.h` | Post-intro title/sector music selection and mute continuity |
| `game/src/render_internal.h` | Private strip-layout validation shared by the rendering modules |
| `game/src/intro.c/.h` | Nonblocking ACE/Micrix startup sequence and original ACE sample ownership |

`main.c` binds the back bitmap, acknowledges published scenes, restores its BOB
history and animates the world before input/logic. After logic/audio, rendering
composes scenes or updates HUD/BOBs, then publishes decor and hero/enemy/bullet
streams. Blits finish before palette/copper publication and vblank acknowledgement.
The exact ownership and conditional frame order are in [rendering](docs/rendering.md).

Enemy, bullet and bonus renderers can clear rejected entities' visibility to
prevent invisible collisions. Child modules free their own resources but never
the borrowed view, screen or shared blank buffer.

## Assets and credits

- `game/art/`: editable pixel art and imported logo provenance.
- `game/sound/`: original procedural audio and MML demo.
- `game/tests/`: host rules tests and emulator scenarios/goldens.

The new bosses, flashes, effects and five manga panels are **original locally
authored offline-generator pixel art**, not Retro Diffusion output. See
[campaign-art provenance](game/art/CAMPAIGN-ART.md). Original Retro Diffusion
masters, source plates, licensed intros and exact ACE PCM are preserved.

**Licensing is mixed.** ACE/Micrix are credited adaptations, not original Astra
branding. The ACE intro carries MPL-2.0 provenance; the Micrix material is
**CC BY-NC-SA 4.0**, including its noncommercial/share-alike restrictions.
See [intro attribution and modification notices](game/art/intro/README.md).
Do not treat the entire game as permissively licensed or assume commercial
distribution rights from this repository. No R-Type artwork, music or code is used.
