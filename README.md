# ASTRA: LAST LIGHT

A horizontal space-opera shooter for the **Amiga A500 / OCS**, combining
classic arcade combat, manga-style storytelling and a mysterious synthwave soundtrack.

Fly through four sectors of wreckage, crystal nebulae and imperial machinery.
Dodge enemy formations, collect upgrades and charge your weapon to take on
each sector's boss.

## How it started

I wanted to vibe-code a quick project to show off the sprite multiplexing
capabilities I had just submitted to ACE in
[pull request #292](https://github.com/AmigaPorts/ACE/pull/292).

Iteration after iteration, that little showcase turned into this weird
space-opera shoot ’em up. I think the result is quite acceptable!

It’s not that hard: I can finish it, and I’ve never managed to finish Team17’s
*Project-X*. My younger son, however, still can’t get past the first level.
Difficulty is relative.

## The game

- **Four-sector campaign** with distinct environments, enemy patterns and bosses.
- **Release-to-fire combat:** tap and release for normal shots, or hold until
  READY and release a powerful charged lance.
- **Wave-clear rewards:** destroy an entire formation to earn damage, fire-pattern,
  speed, shield or extra-life pickups. Upgrades carry between sectors.
- **Manga-style story scenes** at sector entry, boss encounters and victory.
- **Scrolling pixel-art scenery and layered parallax stars**, accompanied by
  an original title theme and four sector arrangements.

| Sector | Setting | Boss |
|---|---|---|
| Orbital Graveyard | Wrecked hulls and running lights | Salvage Claw |
| Veil Nebula | Crystals and a dark-violet starfield | Manta |
| Imperial Foundry | Girders, pipes and furnace vents | Furnace Carrier |
| Stellar Citadel | Silver armor and luminous reactors | Reactor Crown |

## ACE and sprite multiplexing

The Amiga has **eight hardware sprite channels**. Multiplexing reuses a channel
at different vertical positions on the screen, allowing more than eight objects
to appear in a frame. Objects sharing a channel still need vertical separation.

A normal sprite uses **4-color mode** (three visible colors plus transparency).
Attaching two channels together gives **16-color mode** (15 visible colors plus
transparency), trading channels for a richer palette.

| Object | Sprite mode | Hardware channels |
|---|---|---|
| Player ship | 16-color attached sprites; two adjacent columns form the 32-pixel-wide ship | 0–3 |
| Enemies and asteroids | 16-color attached sprites, multiplexed for up to six formation members | 4/5 |
| Enemy bullets | 4-color independent sprites, multiplexed vertically | 6/7 during waves; 4–7 during boss fights |

Large bosses, player shots, pickups and explosions use **BOBs**—images drawn
into the playfield with the blitter. Drawing bosses this way frees the enemy
sprite pair for more hostile bullets during boss fights.

The project grew out of the ACE multiplexing contribution and still uses that
ACE branch. As the game evolved, its sprite streams moved to a **game-specific,
double-buffered DMA writer**, rather than ACE’s generic multiplexer. The same
hardware channel-sharing principles remain at the heart of the showcase.

## Playing

The game targets a **PAL Amiga A500 with OCS, 512 KB chip RAM and 512 KB
expansion RAM**. Load the bootable `astra.adf` disk in an A500 emulator as DF0
using those settings. A licensed Kickstart 1.3 ROM or the kit's free AROS profile
is required; no ROM is included.

| Input | Action |
|---|---|
| Joystick port 2 / arrow keys | Move |
| Fire / Space | Start; hold to charge and release to shoot |
| Left / right on title | Select starting sector |
| P | Pause |
| M | Toggle music |
| Fresh fire press | Skip an intro or, after a short delay, a story scene |
| Fire after victory | Restart from sector 1 |
| Escape | Return to AmigaOS |

## Project status

**Work in progress.** The four-sector campaign is implemented, but the target of
locked PAL 50fps has not yet been achieved. I’ve completed the campaign in
playtesting; formal full-campaign validation and real-hardware validation remain open.

## Credits

Built with [Amiga Game Kit](https://github.com/codebase/amiga-game-kit) and
[ACE](https://github.com/youenchene/ACE/tree/feat/multiplexed-sprites).
Pixel art combines Retro Diffusion-generated sources with locally authored
artwork and offline refinements. Music includes the original title theme,
**Astra Dusk Signal**, and four sector tracks: **Graveyard Relay**, **Parallax
Veil**, **Alloy Oracle** and **Horizon Engine**.

The ACE and Micrix Production intros are adapted from
[SuperRugbyV](https://github.com/youenchene/SuperRugbyV).
**Licensing is mixed:** ACE intro material carries MPL-2.0 provenance; Micrix
material is CC BY-NC-SA 4.0. See the
[intro credits and licensing notices](game/art/intro/README.md) for attribution
and restrictions.

---

For setup, build commands, tests and implementation details, see the
[development guide](docs/development.md) and [agent instructions](AGENTS.md).
