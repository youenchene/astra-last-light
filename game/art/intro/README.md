# ACE and Micrix startup animations

Adapted from [SuperRugbyV](https://github.com/youenchene/SuperRugbyV), checkout
`4a659ed550aa74c55b386cbb4884b15055136111` (read-only source in
`.tmp/SuperRugbyV`). Source inputs are `src/ace_splash.c`, `src/intro.c`,
`assets/ace-splash/data.h` and the attribution documents in both asset folders.
The checkout commit identifies the source versions; individual file content
hashes may be recorded by the integrating build.

## ACE — MPL 2.0

`ace-logo.h` retains the original 160×59 two-plane indexed pixel data (2360
bytes). `ace.wav` preserves the original mono, 8-bit, 6 kHz WAV; `ace-sound.h`
contains its exact signed Paula PCM (13,152 bytes, 2.192 seconds).
The logo credits **Amiga C Engine**; this
is not original Astra artwork and implies no endorsement.

SuperRugbyV adapted the ACE sequence from **Last Minute Creations**'
[GermzSurvivor splash](https://github.com/Last-Minute-Creations/GermzSurvivor/tree/1bdd194114d921ea5a64e768a5c22274493be00e/res/splash),
commit `1bdd194114d921ea5a64e768a5c22274493be00e`.
GermzSurvivor commit `34d25e63b2a44571506f40b3785f156b0f70d4ee`
identifies the assets as imported from
[Germz](https://github.com/Last-Minute-Creations/germz/tree/f7325228e9e5f4b894a7192d21c6ae2fc80455c5),
commit `f7325228e9e5f4b894a7192d21c6ae2fc80455c5`.
The upstream PNG/WAV are documented as byte-identical there.

The ACE logo, original audio and adapted ACE animation portions in `src/intro.c` are subject
to the [Mozilla Public License 2.0](https://www.mozilla.org/MPL/2.0/).
Retain these notices and make the covered source available with distributions.
No Last Minute Creations splash or other game artwork is included.

Changes for Astra: retain logo silhouette, center `(80,98)`, separate white
A/C/E/POWERED flashes (local frames 0/9/29/49) and 15-frame fade. Quantize the
original raster rainbow to five horizontal bands, using independent palette
banks for the three letters and a separate grey-green POWERED entry. This
fits black plus fifteen colors in OCS 4bpp without adding raster copper
blocks. The hold is shortened to give a 150-frame ACE sequence. The original
PCM plays in full using the upstream settings: Paula channel 0, volume 64,
priority 100, period `3546895 / 6000` (591). It is not resampled or replaced by
a synthesized sweep. Channel 0 is stopped when skipping/finishing ACE, before
Micrix; game music starts only after both intros. The license is in `MPL-2.0.txt`.

`python3 tools/check-ace-audio.py` verifies compiled PCM against the preserved
WAV and, when the reference checkout is present, byte identity with SuperRugbyV.
Signed PCM SHA-256:
`9c1d1aeb6deccdc0a72f3e8cb755b2ce8a2a3572486a0148ce1e255cd45d78bd`.

## Micrix — CC BY-NC-SA 4.0

**Micrix Production, Youen CHENE (1996–2022)**. Adapted originally from the
`.Intro` sequence in `blower.bba`,
[Blower](https://github.com/youenchene/blower/tree/03a91c4201e093e5a31c7fc55cf1b7638ce5dce4),
commit `03a91c4201e093e5a31c7fc55cf1b7638ce5dce4`, via SuperRugbyV.

The Micrix artwork in `micrix.h` and adapted Micrix animation portions in
`src/intro.c` remain **Creative Commons Attribution-NonCommercial-ShareAlike
4.0 International**. This adaptation is offered under that same license,
not under a blanket permissive game license. See the
[license and full legal terms](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode).
Retain attribution and modification notices; redistribution/adaptation must
respect NonCommercial and ShareAlike. Licensed material is provided **as-is,
without warranties**, subject to the license's disclaimer and limitation of
liability. No endorsement is implied.

SuperRugbyV's earlier adaptation shortened the Blower sequence to 100 PAL
frames, retained the pixel-letter MICRIX/PRODUCTION design, added a moving
glint and sparkle, and synthesized rise/spark effects. Astra preserves those
glyphs, geometry, purple/white/lavender design, glint frames 10–44, sparkle
43–54, and final fade 86–99. AGA `0x7733bb/0xffffff/0xddbbff` becomes OCS
`0x73b/0xfff/0xdbf`. The original embedded audio arrays are not copied;
`soundPlay(SOUND_SFX_INTRO_RISE)` at frame 10 and
`soundPlay(SOUND_SFX_INTRO_SPARK)` at frame 43 use the game's existing player.
No Blower title artwork or music is included.

Transition optimization: rasterize the same Micrix pixels and glint mask once
at startup into a 320×64×4bpp interleaved chip cache (10,240 bytes), with screen
Y origin 96. Copy the aligned 208×64 region from `(64,0)` to `(64,96)` at entry.
Screen clears use hardware blits, completed before CPU drawing. Animation ticks,
palette, sounds and original ACE PCM are unchanged. Cache allocation failure is
reported and falls back to the original pixel-correct draw (with its old stall).

## Integration contract

- `introCreate(buffer, viewport)` borrows the existing interleaved 4bpp
  320×256 buffer, clears all four planes and draws ACE immediately. It calls
  the shared sound API, so initialize game audio before creating the intro.
- Call `introProcess(fire)` exactly once per PAL frame. Unskipped calls 1–149
  continue ACE; call 150 draws Micrix frame zero and returns 1; calls 151–249
  animate Micrix; call 250 clears the screen/palette and returns 0. Subsequent
  calls return 0 without drawing. Normal duration is five seconds at 50 Hz.
- Each stage starts unarmed. It must observe a released fire input, then a
  pressed input to skip. ACE skip switches directly to visible Micrix and
  returns 1; Micrix skip clears and returns 0. A held press never skips both.
- The renderer must call `renderSyncPalette()` after create and each intro
  tick, including the final tick if it presents that cleared frame. On
  completion restore the game palette and redraw the game before presenting.
- No view creation/load, system takeover, copper processing/swap, frame waits,
  file I/O or ptplayer lifecycle happens in this module. ACE PCM is allocated
  during create while the OS is available and kept alive until shutdown. The
  Micrix cache is also allocated during create; blitter waits complete all DMA
  before CPU drawing or cache release. Both
  supplied buffers are updated if front/back differ; no buffer swaps occur.
- `introDestroy()` is idempotent, frees owned Micrix cache and ACE PCM and forgets borrowed
  pointers. Call it **after `soundDestroy()`** so asynchronous DMA cannot access
  freed sample RAM. It does not free borrowed bitmaps, restore palette or alter the view.

The integrated build has been cross-compiled and both intros, including their
skip behavior, have been checked with shared screenshot baselines on A500 and
AROS. Dynamic glint masks are cached and updated before their scanlines to avoid
single-buffer tearing. The cache/DMA transition optimization still requires fresh
parent-run transition performance measurements and boot/audio/skip goldens.
