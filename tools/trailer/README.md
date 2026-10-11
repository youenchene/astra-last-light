# Astra — The Signal

A **90-second, 1920×1080, 25fps** mysterious transmission film: a message from
tomorrow, breathing wrecks, mirrored machines, a pilot recognized by the dark,
and an impossible reply. Includes **20 seconds of actual normal-speed A500
gameplay across all four sectors** (five seconds each), English captions and the
same continuous stereo score throughout. Gameplay contributes visuals only:
no native music, SFX, ducking or soundtrack changes at gameplay edits.
The closing text reads “A side-scrolling shooter for
Amiga OCS/ECS”. The 25fps export samples every second PAL frame; it does not
speed up gameplay or assert the game's performance acceptance.

## Rebuild

Install FFmpeg (`ffmpeg` and `ffprobe` on PATH). Capturing needs Python 3.12,
the project's Amiga Game Kit (default `$HOME/Code/amiga/amiga-game-kit`, override
with `AGK_KIT`), its headless vAmiga and a locally available A500 Kickstart ROM.
From the repository root, first capture a built production ADF:

```sh
python3.12 tools/trailer/capture.py --adf game/build/astra.adf
```

The capture script uses ordinary joystick inputs, not injected state. It creates
its own cold-boot snapshot and copies the ADF into its output directory. It does
not rebuild the game, alter the original disk, use a GUI emulator, or touch user
snapshots. Use a production build with diagnostic/stress flags OFF. The four
16-second captures include charge/release fire and vertical dodges. The saved
`sources.json` identifies the disk hash, hardware, source clips and capture script.

Then render:

```sh
python3 -m venv .tmp/trailer-venv
.tmp/trailer-venv/bin/pip install -r tools/trailer/requirements.txt
.tmp/trailer-venv/bin/python tools/trailer/render.py
```

Output: `.tmp/astra-trailer-90s/Astra-The-Signal-90s.mp4`.

For a newer game build, recapture its ADF into a fresh directory and use its art:

```sh
python3.12 tools/trailer/capture.py \
  --adf /path/to/new/astra-checkout/game/build/astra.adf \
  --out .tmp/astra-gameplay-new --label "New production build"
.tmp/trailer-venv/bin/python tools/trailer/render.py \
  --source-root /path/to/new/astra-checkout \
  --footage .tmp/astra-gameplay-new/sources.json \
  --out .tmp/astra-trailer-new
```

`edit.json` is the editable timeline and asset mapping. If the game changes its
selected-art layer or filenames, update those explicit paths to the new approved
sources. Changed source bytes are always read afresh; there is no stale shot cache.
Rendering already-recorded footage requires no emulator, `.tmp/SuperRugbyV`,
private service or API key. Gameplay source hashes and clip lengths are validated;
missing or short footage is never silently replaced by stills.

`score.json` locks the original two-minute composition independently of the
visual edit. Changing shot durations or zooms does not change any score sample.
The 90-second cut uses its first 90 seconds without retiming, with a one-second
fade at the new ending. The full original score WAV is retained as the source.
The Nebula and Foundry gameplay excerpts have gentle editorial zoom-ins configured
by `zoom` (start/end factors) and `focus` (normalized crop position); the other
two preserve the complete screen. All gameplay remains at 1x speed.

Use `--preview` to generate only the 17-shot storyboard. Use `--edit FILE` to load
a revised timeline; its sum must match its explicit `duration` (90 seconds). All shot lengths
are checked against whole-frame boundaries. The script fails if a source is absent.

## Deliverables and verification

- `Astra-The-Signal-90s.mp4`: H.264, yuv420p, AAC stereo, fast-start for sharing.
- `storyboard.jpg`: frame from every shot with edit timecode.
- `signal-score.wav`: original seeded score, 48kHz stereo.
- `picture.mp4`: silent picture master.
- `edit-manifest.json`: complete edit, source commit and dirty status, SHA-256 of
  each artwork/font/edit/renderer/export, FFmpeg version, audio and ffprobe results.

After rendering, ffprobe decodes/counts the video and checks **2250 frames**, exact
duration, output geometry and stereo audio. For a full independent decode check:

```sh
ffmpeg -v error -i .tmp/astra-trailer-90s/Astra-The-Signal-90s.mp4 -f null -
```

The source art and seeded synthesis make the edit reproducible. Binary-identical
MP4 output additionally requires identical Python/Pillow/NumPy/FFmpeg versions.
The score synthesizer mixes reversed inharmonic bells, detuned drones, uneven
pulses and radio dust, then targets −18 LUFS / −2dBTP via
FFmpeg loudness normalization. It does not change system audio settings.

## Provenance

The pipeline follows the frame-exact FFmpeg/Pillow and source-manifest approach in
[`SuperRugbyV/tools/teaser`](https://github.com/youenchene/SuperRugbyV/tree/main/tools/teaser).
The Astra renderer, edit and score are newly authored for this film.

The four story panels use the game's approved `story-character/bold-marks` layer;
four galaxy plates come from `game/art/galaxy`. Original Retro Diffusion provenance
and offline-derivative history stay in those asset directories. The trailer applies
editorial crops, movement, darkening and reflection without modifying the sources.
Its cryptic copy is promotional fiction, not additional implemented game mechanics.
The Graveyard and Citadel excerpts retain the complete screen and HUD at integer
pixel scaling; Nebula and Foundry use intentional nearest-neighbor zoom crops. Capture
uses 512K chip + 512K slow A500 emulation and ordinary sector selection. The
source disk can predate unbuilt checkout edits; its hash and label are preserved
separately from artwork checkout metadata. No licensed ACE/Micrix intro imagery
or audio is included. The original three-minute export remains in
`.tmp/astra-trailer/` as edit history.

Bundled Space Mono Regular/Bold are from Google Fonts, under the SIL Open Font
License in `fonts/OFL.txt`. Pinning these files removes dependence on macOS fonts.
