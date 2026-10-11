# Final campaign acceptance record

Latest ordinary production validation includes restored sector-specific titles
and Veil Nebula crystal bands. Injected campaign results below are the earlier
parent integration run for sector enemies, release-only fire and F upgrades;
that strict fixture was not rerun in this presentation regression pass.
**All 11 functional features are implemented; performance acceptance is BLOCKED.**
Global 50fps is not achieved. This record does not mark all 25 plan tasks complete.
Feature details are in [campaign status](campaign-expansion.md); render ownership
and payload accounting are in [rendering](rendering.md).

## Target and production flags

- Baseline: A500, 7 MHz 68000, OCS, PAL 50 Hz, 512 KiB chip + 512 KiB slow RAM.
  Both `a500` and `a500-aros` were exercised; AROS's extra fast RAM is not baseline
  memory proof.
- Runtime budget: **20 ms**, strict gate **zero dropped frames and <=90% peak**.
  The project-local 6000-frame cold-load timeout only accommodates the larger
  executable on AROS; no runtime threshold was relaxed.
- Final production cache: `ASTRA_CAMPAIGN_PROBE=OFF`, `ACE_DEBUG=OFF`,
  `ACE_DEBUG_SERIAL=OFF`, `ACE_DEBUG_UAE=OFF`, `ACE_USE_ECS_FEATURES=OFF`,
  `ACE_USE_AGA_FEATURES=OFF`, `ACE_BOB_WRAP_Y=OFF`.
  Injected QA hooks compile only with the probe ON; the runner rebuilds OFF in
  `finally`. Production restoration succeeded.

## Command and evidence matrix

### Latest per-sector balance: scoped validation

The 16/17/18/20 motion steps per 20 combat ticks, independent firing periods
and boss-only sector-2/3 HP changes passed the C host suite (1/1), nine Python
telemetry-validator tests and the production build (**476,364-byte executable**).
Combat ordinary-input runs passed on both profiles. Both complete `firing.png`
and 320×256 `firing.screen.png` captures were byte-identical across profiles and
visually inspected before updating **only** `game/tests/golden/combat/firing.png`.
The shared combat reference then passed on both profiles without updates.

```sh
bash tools/agk unit
python3 -B -m unittest discover -s game/tests/unit -p test_gameover_title_validator.py -v
bash tools/agk build
# Executed individually, stopping on a new failure:
bash tools/agk run --profile a500 --no-build -f game/tests/combat.agk -o game/build/agk/a500/combat
bash tools/agk run --profile a500-aros --no-build -f game/tests/combat.agk -o game/build/agk/a500-aros/combat
cmp game/build/agk/a500/combat/firing.png game/build/agk/a500-aros/combat/firing.png
cmp game/build/agk/a500/combat/firing.screen.png game/build/agk/a500-aros/combat/firing.screen.png
# Only after inspecting both complete captures:
bash tools/agk test --profile a500 --only combat --update --no-build
bash tools/agk test --profile a500 --only combat --no-build
bash tools/agk test --profile a500-aros --only combat --no-build
bash tools/agk run --profile a500 --no-build -f game/tests/native/gameover_title.agk -o game/build/agk/a500/gameover_title
python3 -B tools/verify-gameover-title.py game/build/agk/a500/gameover_title/serial.txt
bash tools/agk run --profile a500-aros --no-build -f game/tests/native/gameover_title.agk -o game/build/agk/a500-aros/gameover_title
python3 -B tools/verify-gameover-title.py game/build/agk/a500-aros/gameover_title/serial.txt
```

Both fresh GAMEOVER scenarios and validators passed; all eight captures were
inspected. The 150-ready-tick return, reset and held-input protection are covered.
The `fresh_intro` screenshot still represents early bounded recomposition, not
completed manga artwork. These are scoped functional passes, not full campaign
or strict-performance acceptance. The combat A500 log includes a 93% peak window;
the unchanged <=90% target is not established by these functional scenarios.
Other ordinary references, revised injected boss coverage and worst-case 50fps
remain to be revalidated. Historical evidence below is not a pass for this balance.

### New balance: scoped GAMEOVER validation

This subsection is historical evidence for the uniform 4/5-clock revision,
before the latest per-sector motion, independent combat-tick firing and
sector-2/3 boss-HP increases. Revalidation of that newer balance is pending.

After the GAMEOVER lifecycle and 4/5 enemy-clock changes, production
`gameover_title` and its wrapped-state serial validator pass on **both profiles**.
All four screenshots per profile were inspected. Nine Python validator regression
tests, the C unit suite (1/1) and production build also pass; executable size is
**475,180 bytes**. Commands, evidence paths and the early-transition screenshot
limitation are recorded in [the GAMEOVER validation record](campaign-native-fixture.md#gameover-validation-after-the-45-clock-changes).
The full ordinary suite and revised injected boss probes have not yet been
revalidated for this balance. No new global 50fps acceptance is claimed.

### Historical presentation and campaign evidence

Commands below reproduce the relevant checks from the repository root. Ordinary,
source/pixel, allocation and audio checks were rerun in this presentation pass;
the injected fixture row is retained prior evidence.

| Check / command | Final observed result | Evidence |
|---|---|---|
| `bash tools/agk unit` / `bash tools/agk build` | **PASS** host rule suite / production ADF build | `game/tests/test_logic.c`, `game/build/astra.adf` |
| `bash tools/agk test --no-build` | **38/38 PASS** (19 scenarios × two profiles), after scoped updates; all **42 complete captures byte-identical** between profiles | `game/build/agk/{a500,a500-aros}/<scenario>/`: `*.screen.png`, full `*.png`, `serial.txt`, `emulator.log`, audio; scenarios/goldens in `game/tests/` |
| `python3 tools/check-allocation-safety.py` (after build) | **PASS**: all 15 audio allocation failure positions/retries, BOB/bitmap faults, exact preservation of all 20 generated SFX/MOD arrays | Persisted checker; `game/build/sound/{sound.c,sound-safe.c}` and patched `game/vendor/ACE/`; host harnesses are temporary and cleaned |
| `python3 tools/check-campaign-native.py --strict-performance` | Command ran and **exited FAIL** on performance; **functional PASS** on both profiles, 40 captures each, all 13 scenes plus F badge/F2/F3 checks | `game/build/campaign-native/report.json`; per-profile `serial.txt`, screenshots, audio and emulator logs |
| Production OFF restoration | **Succeeded** | `production_restored` in fixture report; `ASTRA_CAMPAIGN_PROBE:BOOL=OFF` in `game/build/CMakeCache.txt` |
| Production A500 boot memory | **24,056 free chip / 30,112 total free bytes**; initial executable **474,992 bytes** | `game/build/agk/a500/boot/serial.txt`, `chip_free` / `ram_free` telemetry; build output |
| `python3.12 tools/verify-sector-presentation.py` | **PASS** both profiles: 8,928 exact unobscured pixels per original title, four distinct plates, both full-screen selection wraps; all **15,360 Nebula band pixels** match source-derived crystals/background | `title_sectors/*.screen.png`, `sector2/nebula.screen.png`; unique top/bottom phases both 29 |
| Independent Nebula source check (same command) | **PASS** fixed-point connectivity: only 544 connected ink-1 pixels cleared (293/251); 158 disconnected shadow pixels retained (53/105); all other crystal inks unchanged | Original `rd_decor1.png` + palette + existing crop/seam rules compared exactly with `decor.txt` |
| `python3.12 tools/verify-scrolling.py --compare-profiles --performance-summary` | **PASS** exact Nebula bands, sector-1 4px motion, all four parallax rates, 12 hero colors, clean title; 42 byte-identical complete captures | Ordinary per-profile captures and emitted timing windows |
| `python3.12 tools/make-title-plates.py --check` / `python3 tools/verify-rich-art.py` | **PASS** deterministic four-title header; exact generated/remapped art pixels and masks | Read-only header, generated art and text sources |
| `python3 tools/check-music-channels.py` / `python3 tools/check-ace-audio.py` | **PASS** Paula D reserved, 13,624 sector PCM bytes; exact original 13,152-byte ACE sample | Generated modules and preserved ACE PCM |
| P pickup BOB verification | **164 opaque / 92 transparent / 512 restored pixels** checked | `tools/verify-bob-restoration.py`, ordinary `bob_restore` captures on both profiles |

Allocation checks use ASAN/UBSAN host stubs and an allocation ledger; on macOS,
LeakSanitizer is disabled. This is not native OOM fault injection. Generated data
preservation is exact; the checker does not certify Amiga interrupt behavior.

### Presentation regression sequence

Focused native runs preceded golden acceptance on both profiles:

```sh
for profile in a500 a500-aros; do
  bash tools/agk run -f game/tests/title_sectors.agk -p "$profile" \
    -o "game/build/agk/$profile/title_sectors" --no-build
  bash tools/agk run -f game/tests/sector2.agk -p "$profile" \
    -o "game/build/agk/$profile/sector2" --no-build
done
python3.12 tools/verify-sector-presentation.py
# After inspecting the title and crystal captures and comparing profiles:
bash tools/agk test --only title_sectors --only sector2 --update --no-build
bash tools/agk test --no-build
python3.12 tools/verify-sector-presentation.py
python3.12 tools/verify-scrolling.py --compare-profiles --performance-summary
```

All four focused runs passed. Inspection confirmed distinct original illustrations
and visible crystal borders with matching dark-violet space. Only six new title
goldens (`title1`–`title4`, `wrap_right`, `wrap_left`) and the corrected
`sector2/nebula.png` were accepted; all other existing goldens matched unchanged.
The subsequent whole-suite run passed without updates. The title checker uses
original PNGs/palette, excluding only the known existing panel overlap at
x<296, y>=122 within the illustration at (184,56). Full-screen goldens and wrap
equality still cover that panel. Band checks have no exclusions or position
adjustments: all pixels must match one unique source tile phase, with circular
top/bottom phase distance <=1. TITLE ink 4 remains #568; PLAY ink 4 remains #BDF.

BOB checks were also rerun for each profile:

```sh
for profile in a500 a500-aros; do
  python3.12 tools/verify-bob-restoration.py \
    --drop "game/build/agk/$profile/bob_restore/bonus_drop.screen.png" \
    --restored "game/build/agk/$profile/bob_restore/bob_restored.screen.png"
done
```

## Strict injected fixture

| Profile | Functional | Captures | Dropped frames | Peak load | Strict result |
|---|---|---:|---:|---:|---|
| A500 | PASS | 40 | 22 | 130% | FAIL |
| AROS | PASS | 40 | 17 | 123% | FAIL |

Coverage includes all 13 acknowledged scenes, four bosses and white flashes,
six simultaneous small effects per sector, eight hero deaths, four boss deaths,
exact death pauses and hostile channel/visibility invariants. Added F-badge,
double- and triple-volley captures check pattern/HUD pixels and confirm normal
damage remains one despite F upgrades. The
[fixture](campaign-native-fixture.md) injects quotas, collisions and health;
it is **not an ordinary campaign clear**. Scene presence/dimensions and opaque
effect pixels do not constitute final artistic approval.

The fixture now includes additional F probes and different sector waves. These
measurements are **not a like-for-like performance comparison** with the earlier
37-capture run; neither performance improvement nor regression is established
by comparing the totals alone. No 50fps certification is claimed.

## Ordinary replay evidence

`game/tests/bonus-flight.json` records combat-relative **logic video ticks since
`combat_ready`**, not elapsed PAL vblanks: final first-wave kill/drop **275**,
P collection **294**, and six-asteroid capture **1172**. Stage-frame fields in
the same record use a different clock. This is genuine ordinary-input replay
coverage, separate from the injected F fixtures and not a full-campaign clear.

## Current ordinary production timing

These freshly rerun summaries cover **all emitted performance windows**, including intros,
preparation and transitions, rather than combat-only intervals. The final partial
window is not emitted and is not included. Ticks count game iterations, not
elapsed video frames. Low average load does not override a failed peak/drop gate.

| Scenario | Profile | Emitted ticks | Average load | Peak load | Drops |
|---|---|---:|---:|---:|---:|
| `campaign_waves` | A500 | 1,300 | 27.77% | 107% | 1 |
| `campaign_waves` | AROS | 1,300 | 27.19% | 105% | 1 |
| `bonus` | A500 | 1,400 | 31.29% | 117% | 6 |
| `bonus` | AROS | 1,400 | 30.21% | 115% | 2 |

Log locations: `game/build/agk/{a500,a500-aros}/{campaign_waves,bonus}/serial.txt`.
All four summaries exceed the <=90% peak limit and contain dropped frames.
The stable ACE-intro `perf.agk` test cannot establish whole-campaign performance.

## Memory, music and preview scope

The 144 KiB decor phase bank is removed. Atomic double-buffer publication and
copper-scrolled bands remain delivered. Latest production boot memory is an
observation, not a formal worst-case free-memory or allocation high-water bound.
The runtime art manifest no longer compiles unused `player`, `fleet`, `shot`,
`scene`, `actors16`, `graveyard`, `nebula`, `foundry`, `citadel` or `campaign_flash` sections;
all source files remain. Runtime assets, original masters and licensed intros
are preserved. See the [memory ledger](rendering.md#memory-ledger).

Four original title plates occupy **24,576 read-only bytes** and share one
**6,144-byte CHIP staging bitmap**, retaining bounded eight-row composition.
Removing the `graveyard` manifest registration avoids duplicate source payload.
Two framebuffers remain **81,920 CHIP bytes**, the repeated decor source **36,864
CHIP bytes**, and the copper reservation **57 commands**. These payload figures
exclude allocation overhead and other assets; ordinary executable data can use
CHIP when slow memory fills. Compared with the previous common-title build,
the executable grew 18,200 bytes and observed A500 free CHIP fell 16,384 bytes;
total free fell 18,200 bytes. AROS boot reports **115,840 free CHIP / 1,340,848
total free bytes**, which does not establish baseline A500 fit. Original art
masters remain unchanged; frame zero's 3,072-word legacy equality was established
by the preceding implementation pass, while this pass reran native source-pixel
and unchanged boot-golden checks.

Four sector MML tempos are **96/88/104/112 BPM**, with sixteen-bar loops of
**40.00/43.64/36.92/34.29 seconds**. The slower mysterious tone is an artistic
choice; no performance benefit has been proven and it did not close the budget.
See [music](music.md) for the updated arrangements and unchanged PCM inventory.

The parent is recording the ordinary-input preview with:

```sh
bash tools/agk record game/demo/campaign-preview.agk game -o game/build/astra-demo.mp4
```

It covers original intros, title, first manga scene and combat; completion of the
recording is not asserted here. `game/demo/showcase.agk` remains the verified
no-cheat six-wave/pickup flight, not an all-level showcase.

Full ordinary human/native campaign completion, native OOM fault injection,
real-hardware validation, final artistic approval and strict performance
acceptance remain unclaimed or open.
