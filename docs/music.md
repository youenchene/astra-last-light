# Astra: Last Light — audio direction

## Scope and current state

Ten original procedural effects, the original looping title theme and four
sector scores live in `game/sound/`. Music starts after both intros and **M**
toggles music. The integrated controller in `src/campaign_audio.c` selects the
sector track and preserves mute state across campaign transitions.
The ACE logo separately uses the exact original SuperRugbyV sample; Micrix uses
the generated rise/spark effects. Music never replaces the ACE splash sound.
The title theme is “Astra Dusk Signal”; its source and sample bank are unchanged.
The four new sixteen-bar arrangements use small built-in synthesized instruments.

The format was checked directly against the local kit's
`harness/agk/sound.py`: TOML synthesis recipes, MML directives, note ranges,
channel assignment and generated identifiers. No third-party recordings,
commercial melodies were used for the original game theme/effects. The licensed
ACE branding audio is the explicitly attributed exception described below.

## Effects and shared generator interface

| Recipe | Generated identifier | Seconds | Volume / priority | Intent |
|---|---|---:|---:|---|
| shot | `SOUND_SFX_SHOT` | 0.07 | 34 / 1 | Short descending needle; unobtrusive under rapid fire |
| explosion | `SOUND_SFX_EXPLOSION` | 0.24 | 52 / 4 | Noise collapses from bright debris into rumble |
| hit | `SOUND_SFX_HIT` | 0.09 | 46 / 5 | Distinct, urgent damage crunch |
| charge | `SOUND_SFX_CHARGE` | 0.22 | 42 / 2 | Soft rising energy pulse |
| warp | `SOUND_SFX_WARP` | 0.28 | 44 / 6 | Falling sawtooth transition |
| intro_rise | `SOUND_SFX_INTRO_RISE` | 0.36 | 40 / 2 | Slowly opening title beacon |
| intro_spark | `SOUND_SFX_INTRO_SPARK` | 0.16 | 44 / 3 | Three-note spectral glint |
| lance | `SOUND_SFX_LANCE` | 0.28 | 58 / 5 | Charged-shot blast; audible over an ongoing enemy explosion |
| bonus_drop | `SOUND_SFX_BONUS_DROP` | 0.16 | 44 / 4 | Wave-clear reward chime |
| bonus_pickup | `SOUND_SFX_BONUS_PICKUP` | 0.18 | 54 / 7 | Clear confirmation of upgrade collection |

Use symbolic names, not numeric IDs: `soundPlay(SOUND_SFX_SHOT)` after a successful
`astraSoundCreate()` (the checked project constructor). Destroy via `soundDestroy()`.
The kit generates `sound.h`;
do not maintain a competing handwritten header. Expect `SOUND_SFX_COUNT` = 10,
`SOUND_MUSIC_COUNT` = 5, `SOUND_MUSIC_THEME`, and `SOUND_MUSIC_SECTOR1` through
`SOUND_MUSIC_SECTOR4` after successful generation.

All generated effects share **zero-based Paula channel 3**. Higher-priority cues can
interrupt lower-priority ones; this is intentionally not seven simultaneous
voices. Trigger charge once when fully charged, not every frame. Avoid a warp
over important damage feedback; schedule intro spark after intro rise if both
must be heard. Check equal-priority retrigger behavior in the actual player.

The generator reports **75,948 bytes** for generated SFX and all five songs,
excluding allocator overhead and player state. The pre-campaign total was 62,324.
The five original theme instruments account for **28,508 bytes** of PCM; the MOD file
is **33,688 bytes**, including pattern/header data rather than additional PCM.
The original ACE sample adds **13,152 bytes** retained until shared-player
shutdown. It plays on Paula channel 0 before music starts, at period 591,
volume 64, priority 100, matching SuperRugbyV. Its WAV and MPL notice are in
`game/art/intro/`; `python3 tools/check-ace-audio.py` verifies sample identity.

## Authored four-stage arc

All four arrangements are original note sequences, not transpositions or tempo
edits of the title theme. The beacon's rising fifth, falling third and unresolved
second develop through different harmonies, rhythmic groupings and registers.
Each is 256 rows / sixteen 4/4 bars / four pattern positions. Long tones use
looped mathematical waves; a single built-in kick sample is reused within each
song. No external recordings or new WAV instruments are needed.

| Stage | Tempo / tonal center | Arrangement and development |
|---|---|---|
| 1 — Orbital Graveyard: Graveyard Relay | 96 BPM, E minor | Em–C–G–B tension; broken eighth-note pulse12 glass, triangle beacon and offbeat bass. Late C-sharp Dorian glimmer; second-half melodic variation. |
| 2 — Veil Nebula: Parallax Veil | 88 BPM, C-sharp minor | C#m–A–E–B; D-natural Phrygian intrusion. Long sine gestures, triangle replies grouped 3+3+2 eighths, half-time kick and sustained bass. |
| 3 — Imperial Foundry: Alloy Oracle | 104 BPM, B minor | Bm–G–Em–F#; A-sharp dominant. Decaying saw stabs, pulse25 sixteenth machinery, displaced bass attacks and an eighth-bar break. |
| 4 — Stellar Citadel: Horizon Engine | 112 BPM, D minor | Dm–Bb–Gm–A, E-flat danger and C-sharp dominant. Rising pulse phrases, reversing saw eighths and gated pedal bass; two-bar sparse reset. |

There is no separate boss score or victory coda: the current sector score
continues through its boss, death animations and presentation scenes.

### Generated memory inventory

| Source / ID | PCM bytes | MOD bytes | Loop seconds |
|---|---:|---:|---:|
| `sector1.mml` / `SOUND_MUSIC_SECTOR1` | 3,438 | 8,618 | 40.00 |
| `sector2.mml` / `SOUND_MUSIC_SECTOR2` | 3,374 | 8,554 | 43.64 |
| `sector3.mml` / `SOUND_MUSIC_SECTOR3` | 3,438 | 8,618 | 36.92 |
| `sector4.mml` / `SOUND_MUSIC_SECTOR4` | 3,374 | 8,554 | 34.29 |
| **New total** | **13,624** | **34,344** | |

The new PCM is **19,144 bytes below the 32 KiB cap**. Each song has three
looped waves (64–256 samples plus a silent word) and one 2,984-byte kick.
AGK copies banks per module: the kick is counted four times, not claimed as
cross-module deduplicated. None copies the old 28,508-byte theme bank.
MOD sizes include headers/patterns and PCM; do not add both columns as DMA PCM.
Including original ACE PCM, total audio sample payload is **89,100 bytes**.
This is a sample inventory, not proof that the entire integrated game fits RAM.

### Practical four-channel orchestration

- **A / Paula 0:** pad root or fifth, then lead/brass answer. One pitched note
  at a time; an implied orchestral pad is not simultaneous chord polyphony.
- **B / Paula 1:** arpeggios and upper harmonic answers. MML `(ceg)` is a fast
  tracker arpeggio, not three oscillators. Keep spans within 15 semitones.
- **C / Paula 2:** bass and metallic drums time-share rows. Kick replaces a
  bass attack; hats occupy gaps. Do not claim pad + lead + arp + bass + drums
  all sustain independently with only three musical DMA channels.
- **D / Paula 3:** no music notes or samples, reserved for SFX. Use full-length
  rests. Global tracker speed/tempo effects may appear in its effect column;
  these are not audible notes. `sfx_channels = [3]` yields music mask `0x7`.

For a richer later score, synthesize short original string/brass/metallic
one-shots offline and budget them explicitly. The kit's WAV instrument path
plays one-shots; it does not expose custom sustained sample-loop points.
Use built-in looped waves for long holds, or budget finite pad samples. Do not
promise reverb, layered detuning, or real orchestral polyphony for free.
Keep a shared timbral vocabulary, but note that the current generator copies
each registered song's samples separately: four modules can duplicate banks.

## Demo, generation and verification

`theme.mml` has sixteen 4/4 bars at **96 BPM in E minor**: **256 rows**, four
pattern positions and **40 seconds** before looping, at playback volume 42.
`tools/make-synthwave-samples.py` synthesizes five original WAV instruments:
detuned open-fifth pad, sparse lead, rounded bass, soft kick and hushed snare.
Paula A carries the pad; B time-shares lead and snare; C time-shares bass and
kick; D rests for SFX. Echo-like phrases are sequential notes, not extra voices.
Detuning is baked into samples, not performed by extra runtime oscillators.

From the repository root, with AGK available:

```sh
python3 tools/make-synthwave-samples.py
bash tools/agk sound
python3 tools/check-music-channels.py
python3 tools/check-ace-audio.py
```

Inspect `game/build/sound/sound.h`, `theme.mod`, and every WAV/PNG in
`game/build/sound/preview/`. Expected sweep directions: shot/warp downward,
charge/intro_rise upward, explosion narrowing downward, intro_spark stepped
upward. Audition the theme loop, rapidly repeated shots and priority clashes.
The theme preview renderer is not a substitute for Paula/emulator testing.

### Campaign controller integration contract

Include `campaign_audio.h` (ACE types and `logic.h`). After player creation call
`campaignAudioReset()`; it only invalidates cached playback and preserves mute,
without touching intro audio. Do not call update while ACE/Micrix own audio.
Once both logos finish, call this each frame after state transitions:

```c
campaignAudioUpdate(state.level, state.phase, mutePressed);
```

`mutePressed` must be a press edge, not a held-key flag. Levels are zero-based.
TITLE selects the original theme; sector entry selects that level's score
immediately, before PLAY. Boss arrival/fight/death, hero death, CLEAR, GAMEOVER
and WIN keep the same level's score without restarting it. Entering
SECTOR_INTRO at level zero detects a new run (including a retry without TITLE)
and restarts sector 1 once. Repeated intro frames do not restart it.
Mute persists across all those transitions and reset. Unmute starts the current
score from its beginning; it does not resume a saved tracker position. Invalid
levels fall back to the title theme. The controller allocates no memory.
It must be the sole post-logo owner of music start/stop calls.

Channel D has no musical notes. Keep measuring frame load: the music timer
interrupt has a noticeable A500 cost.

**Historical title-theme validation:** generation and Amiga compilation passed. Firing audio
assertions passed on A500 and AROS; music-only playback, mute silence and resumed
playback are also asserted. Captured music and ACE-audio spectrograms were
inspected. The original ACE PCM was verified byte-for-byte against the reference.
The game theme has not been auditioned by a person and remains a short arrangement
sketch rather than a finished production score.

**Sector-audio validation (2026-10-05):** `bash tools/agk sound`,
`python3 tools/check-music-channels.py` and `python3 tools/check-ace-audio.py`
passed. The channel checker reads all five MODs, validates their PCM sizes,
forbids notes/samples on D while allowing global effects, checks generated IDs
and mask `0x7`, and enforces the combined sector PCM cap. All four generated
spectrograms were visually inspected for their distinct phrasing and silences.
A standalone host C harness compiled the real controller against mocked sound
calls with `cc -std=c99 -Wall -Wextra -Werror`: title, all four sectors, scene
continuity, same-sector retry, mute across levels/reset and invalid-level
fallback passed. Native builds/tests were deliberately left to integration;
the new arrangements have not been human-auditioned or validated on Paula.
Lance remains priority 5; ACE PCM identity remains 13,152 bytes with SHA-256
`9c1d1aeb6deccdc0a72f3e8cb755b2ce8a2a3572486a0148ce1e255cd45d78bd`.

## Originality and licensing

The recipes and note sequences were authored for this project; all sounds
derive from mathematical waveforms or deterministic synthesized noise.
No external sample clearance is required for these source assets. This is
provenance, not a claim of exclusive copyright or a new repository-wide
license. The project owner should select/confirm the distribution license for
these original assets before release. AGK/ACE/player licensing remains
separate and must retain its required notices. Future commissioned music must
include written commercial-use and redistribution rights for both samples
and compositions, plus source files and a sample-provenance inventory.
