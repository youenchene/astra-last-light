# Final campaign acceptance record

Latest observed results reported by the parent integration run for sector enemies,
release-only fire, F upgrades and clear Veil Nebula bands. Historical timing is
explicitly labeled below.
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

Commands below reproduce the relevant checks from the repository root; results
are the completed parent run, not new executions by this documentation pass.

| Check / command | Final observed result | Evidence |
|---|---|---|
| `bash tools/agk test` | **36/36 PASS** on the latest ordinary production build; all **36 complete captures byte-identical** between profiles | `game/build/agk/{a500,a500-aros}/<scenario>/`: `*.screen.png`, full `*.png`, `serial.txt`, `emulator.log`, audio; scenarios/goldens in `game/tests/` |
| `python3 tools/check-allocation-safety.py` (after build) | **PASS**: all 15 audio allocation failure positions/retries, BOB/bitmap faults, exact preservation of all 20 generated SFX/MOD arrays | Persisted checker; `game/build/sound/{sound.c,sound-safe.c}` and patched `game/vendor/ACE/`; host harnesses are temporary and cleaned |
| `python3 tools/check-campaign-native.py --strict-performance` | Command ran and **exited FAIL** on performance; **functional PASS** on both profiles, 40 captures each, all 13 scenes plus F badge/F2/F3 checks | `game/build/campaign-native/report.json`; per-profile `serial.txt`, screenshots, audio and emulator logs |
| Production OFF restoration | **Succeeded** | `production_restored` in fixture report; `ASTRA_CAMPAIGN_PROBE:BOOL=OFF` in `game/build/CMakeCache.txt` |
| Production A500 boot memory | **40,440 free chip / 48,312 total free bytes**; initial executable **456,792 bytes** | `game/build/agk/a500/boot/serial.txt`, `chip_free` / `ram_free` telemetry; parent build size verification |
| Sector 2 clear bands | **15,360 band pixels** match ink 0, `#102`; HUD/play bounds unchanged | Ordinary sector captures; bitmap and copper decor paths disabled in `render_world.c` |
| P pickup BOB verification | **164 opaque / 92 transparent / 512 restored pixels** checked | `tools/verify-bob-restoration.py`, ordinary `bob_restore` captures on both profiles |

Allocation checks use ASAN/UBSAN host stubs and an allocation ledger; on macOS,
LeakSanitizer is disabled. This is not native OOM fault injection. Generated data
preservation is exact; the checker does not certify Amiga interrupt behavior.

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

## Historical ordinary production timing

The following table is retained from the earlier allocation-hardened run; it is
**not current timing evidence for the release-only fire/sector-wave build**.
Fresh ordinary timing summaries were not supplied for this documentation pass.
These historical summaries cover **all emitted performance windows**, including intros,
preparation and transitions, rather than combat-only intervals. The final partial
window is not emitted and is not included. Ticks count game iterations, not
elapsed video frames. Low average load does not override a failed peak/drop gate.

| Scenario | Profile | Emitted ticks | Average load | Peak load | Drops |
|---|---|---:|---:|---:|---:|
| `campaign_waves` | A500 | 1,300 | 28.23% | 100% | 1 |
| `campaign_waves` | AROS | 1,300 | 27.46% | 98% | 0 |
| `bonus` | A500 | 1,350 | 32.26% | 108% | 10 |
| `bonus` | AROS | 1,350 | 31.00% | 106% | 3 |

Original log locations: `game/build/agk/{a500,a500-aros}/{campaign_waves,bonus}/serial.txt`;
these mutable build paths may now contain newer runs. Even the historical
zero-drop AROS wave run exceeded the <=90% peak acceptance limit.
The stable ACE-intro `perf.agk` test cannot establish whole-campaign performance.

## Memory, music and preview scope

The 144 KiB decor phase bank is removed. Atomic double-buffer publication and
copper-scrolled bands remain delivered. Latest production boot memory is an
observation, not a formal worst-case free-memory or allocation high-water bound.
The runtime art manifest no longer compiles unused `player`, `fleet`, `shot`,
`scene`, `actors16`, `nebula`, `foundry`, `citadel` or `campaign_flash` sections;
all source files remain. Runtime assets, original masters and licensed intros
are preserved. See the [memory ledger](rendering.md#memory-ledger).

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
