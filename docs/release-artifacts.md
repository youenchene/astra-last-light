# Astra release artifacts

## Local command

From the repository root, after setting `AGK_KIT` to the pinned kit and running
`bash tools/bootstrap.sh`:

```sh
bash tools/agk package --help
bash tools/agk package --version 1.2.3
# Only reuse an independently content/cache/source-verified build receipt:
bash tools/agk package --version 1.2.3 --no-build --out .tmp/release-1.2.3-copy
python3.12 -m unittest discover -s game/tests/unit -p test_release_packaging.py -v
actionlint .github/workflows/release.yml
```

Requires Python 3.12, Docker and `bsdtar` (macOS system tool; Linux package
`libarchive-tools`). Network access downloads the reviewed official WHDLoad
20.0 SDK. Docker retrieves the digest-pinned linux/amd64 cross-toolchain,
which includes vasm 2.0f, NDK assembly includes, LHA and xdftool. Pins are in
`tools/release-lock.json`. SDK hashes are checked before extraction; links,
absolute paths, traversal and duplicate members are rejected. Nothing changes
the installed global kit. No proprietary runtime assets are downloaded.

The default command copies content-checked project and toolkit inputs into a
new `.tmp/release-build-*/project/` and `kit/` snapshot for each build. It never
inherits CMake caches or objects from `game/build`, and refuses object files in
the source inventory. Source mtimes therefore cannot suppress compilation.
Input hashes are checked before copying, after copying and after compilation.
It explicitly sets all seven Astra diagnostic/probe flags OFF, plus ACE
debug/ECS/AGA OFF, then checks the Release CMake cache.

Verified executable, ADF, cache and schema-2 receipt live in that run's
`verified/` directory. `.tmp/release-build-latest.json` selects the newest
receipt; existing `game/build` outputs and historical release directories are
not overwritten or deleted. `--no-build` rejects legacy incremental receipts,
changed inputs, changed outputs or a different source commit. Inputs include
packaging tools and final icon files as well as game sources/dependencies.
An arbitrary prebuilt Hunk is not accepted. Preserve the receipt only with its
build; a manually forged trusted receipt is outside the trust model. The
repository's build owner must serialize native builds and emulators.

## Outputs

Default output is a **new** `game/build/release-1.2.3/`; existing output is never
overwritten. A failed run leaves its isolated `.tmp/release-*` evidence in place.

| File | Contents |
|---|---|
| `Astra-1.2.3` | Raw Amiga executable |
| `Astra-1.2.3.adf` | Bootable 880 KiB OFS disk, startup, launcher icon, notices, intro sources |
| `Astra-1.2.3-HD.zip` | Only outer `Astra.info` and `Astra/` drawer |
| `Astra-1.2.3-HD.lha` | Same HD drawer and icon |
| `Astra-1.2.3-WHD.lha` | Only `AstraWHD.info` and `AstraWHD/`, real compiled slave and `data/Astra` |
| `Astra-1.2.3-SHA256SUMS` | Hashes for all five formats and accompanying source/notices/metadata |
| `release.json` | Source commit, dirty status, input fingerprint, binary/slave/icon hashes, flags, pins, validation status |
| `Sources.zip` | Exact covered intro and local patched ACE sources, license and safety patch |
| `ReadMe.txt`, `MPL-2.0.txt`, `IntroCredits.txt` | Requirements, licenses, attribution, modifications and restrictions |

Every executable is checked byte-for-byte after extracting ADF, ZIP and both
LHAs. Every packaged file and icon is checked against staged content. Formats
use short Amiga-compatible top-level filenames. No fake icons are generated;
the checked final `assets/workbench/Astra-{drawer,tool,whdload}.info` files are
required. Native double-click compatibility is separate from host format checks.

### Independent verification and trust boundary

```sh
python3.12 tools/verify-release.py .tmp/astra-release-verified-1.2.3 \
  --report .tmp/my-release-verification.json
# Optionally select a preserved schema-2 receipt explicitly:
python3.12 tools/verify-release.py .tmp/astra-release-verified-1.2.3 \
  --receipt .tmp/release-build-qh9kip0o/verified/release-build.json
```

This is a separate verification pass, not merely a check of self-supplied hashes.
It requires the checked-out source/tool dependencies and a verified isolated
build receipt as trust anchors. It reads every file from every archive and the
OFS disk, checks exact file inventories and allowed parent directories, rejects
links/special files/duplicate or case-colliding paths, and verifies executable
permissions (POSIX archive modes and Amiga read/execute protection bits).
ZIP `external_attr` types and setuid/setgid/sticky modes are checked before
content is read. The raw file must match the trusted fresh build; every embedded
executable must match that raw file. Rewriting a release's SHA256 manifest or
metadata cannot change those anchors.

The icon workstream's independent reader decodes normal/selected two-plane and
GlowIcon images, DrawerData and launch metadata. Extracted icons must equal
those structurally validated source icons. Source ZIP members and license/
attribution notices must equal the checked-out covered sources. The verifier
recompiles the slave independently from the hash-verified official SDK and
current loader source, compares all slave bytes, and validates its guards
against the **actual extracted `AstraWHD/data/Astra`**, not a metadata claim.
The ADF must have a checksummed boot block, OFS, correct startup and no extra
files. Verification reports belong outside the release directory so its exact
inventory remains stable.

The full covered-source ZIP does not fit alongside the executable on an 880 KiB
disk. The ADF includes `IntroSrc.zip`, license/attribution and `Sources.txt` with
the exact SHA256 of the accompanying `Sources.zip`. Retain the sidecars when
redistributing raw executable/ADF. Full sources are also inside both HD and WHD
drawers. **Mixed licensing: MPL-2.0 and Micrix CC BY-NC-SA 4.0**, not a blanket
permissive game license. Commercial rights must not be inferred.

## Native versus WHDLoad requirements

Native target remains 68000/OCS PAL, Kickstart 1.3, 512 KiB CHIP + 512 KiB slow.
Workbench and the icon's 64 KiB launcher stack can require more free memory.
No gameplay changes are required by packaging.

The genuine [Kick13 slave](../tools/whdload/README.md) uses DOS LoadSeg through
SDK KickEmu, full-file size/ANSI CRC16 guards and Astra's actual register-ABI
ACE keyboard handler. It reserves 512 KiB CHIP + 2 MiB expansion + 256 KiB
emulated ROM. WHDLoad's **host needs OS 2.0+** and additional RAM for the host,
WHDLoad and PRELOAD. A 4 MiB fast configuration is a candidate test target,
not a proven minimum. F10 is the slave quit key; Escape retains game shutdown.

User supplies WHDLoad, legal `kick34005.A500` and its matching RTB. ROMs, keys,
RTBs and the WHDLoad executable are never distributed. AGK ROM discovery found
only the legal local Kickstart 1.3 at implementation time, not an OS 2.0+ host
ROM. **Native WHD boot/quit remains unvalidated** until all runtime resources
are available. Compilation or archive verification does not imply a native pass.
Global zero-drop/<=90% PAL 50fps acceptance remains blocked as documented in
the [current performance integration](performance-integration-2026-10-11.md).

## GitHub workflow

`.github/workflows/release.yml` builds on `release: published` and manual dispatch.
Actions are pinned by complete SHA. The build job has read-only contents access;
the separate asset-attachment job alone has write access. Inputs pass through
environment variables, and tag **resolved commit** is checked, not a possibly
moving release `target_commitish` branch. Annotated tags are dereferenced again
before attachment, and artifact hashes/source identity are verified.
Before artifact upload, the build job runs both packaging boundary tests and
the icon regression suite, builds in a fresh snapshot, then invokes the
independent five-format verifier. The verification step must pass before upload.

Manual dispatch takes `version`, `ref` and `attach_assets` (default **false**).
Build-only runs upload Actions artifacts and do not create a release or tag.
Explicit attachment requires an existing matching draft; it never publishes
the draft, overwrites assets or moves a tag. Published-event attachment works
only for mutable releases. With immutable releases, run the manual workflow
against a matching tagged draft, check the downloaded assets, then publish
manually. The published event cannot append to that immutable release and will
report the restriction. No automatic live publication is implemented.

Local static validation is distinct from a remote Actions run. This task does
not trigger any remote workflow, release, push, commit or PR.

## Hardened local verification — 2026-10-11

All four review findings are addressed. New outputs, preserving the earlier
release, are in **`.tmp/astra-release-verified-1.2.3/`**:

| Artifact | Bytes | SHA256 |
|---|---:|---|
| `Astra-1.2.3` |543048|`fc2c8f8ec10ea0796008e550f12f38711471b69de25f67097220cc1768213011`|
| `Astra-1.2.3.adf` |901120|`5a1d4ae5cb691c2f1950e3b22e779104b77c5ff19987a4a883f3a334418e39dd`|
| `Astra-1.2.3-HD.zip` |683220|`0a3e2aaa509446e2d5e904fab3e3ed54b870d7eb058b247bf520ad6fc2486657`|
| `Astra-1.2.3-HD.lha` |693217|`b2916524d3a9b7f64efac16b99c9215923291839327e74577aa033cd532a18ee`|
| `Astra-1.2.3-WHD.lha` |728212|`3dda7e20a061e0a35c732ffdc2add152e8b0f7a201471399fc8427d871dd553b`|

The directory also contains the full SHA256 manifest, source bundle, notices and
release metadata. Executable and slave bytes remain identical to the previous
validated build. All seven diagnostic flags remain OFF. The new verified build
is `.tmp/release-build-qh9kip0o/verified/`; old `game/build` artifacts remain in place.

Executed:

```sh
bash tools/agk package --version 1.2.3 --out .tmp/astra-release-verified-1.2.3
python3.12 tools/verify-release.py .tmp/astra-release-verified-1.2.3 \
  --report .tmp/astra-release-hardened-verification.json
python3.12 game/tests/unit/test_release_packaging.py \
  --release-mutations .tmp/astra-release-verified-1.2.3
python3.12 tools/check-release-native.py .tmp/astra-release-verified-1.2.3
python3.12 -m unittest discover -s game/tests/unit -p 'test_*.py'
actionlint .github/workflows/release.yml
```

- **20/20 release boundary tests**, including negative types/modes, corrupt rich
  icon data, case collisions, changed executable/CRC, legacy/stale receipts and
  a real host compilation after editing source while moving its mtime backwards.
  That regression proves new binary identity and preservation of the old build.
- **3/3 icon tests**; **169/169 full Python tests**,205.309seconds.
- **C rules suite PASS** with ASAN/UBSAN, compiled to the new snapshot's
  `host-test-logic` instead of overwriting the existing `game/build/unit` output.
- Independent five-format extraction/content/mode/source/icon/slave verification
  **PASS**; report `.tmp/astra-release-hardened-verification.json`.
- Actual executable replacement attacks against raw, ADF, HD ZIP, HD LHA and
  WHD LHA: **5/5 rejected despite recomputed valid checksum manifests**. The raw
  attack also rewrote `release.json`'s claimed binary hash. Evidence and all
  mutated copies remain in `.tmp/release-mutation-lfpc3dpt/`.
- New packaged ADF cold-boot/title/Escape checks **PASS** on A500 and AROS;
  extracted HD drawer cold-boot/title/Escape **PASS** on A500/Kick1.3 plus2 MiB
  fast RAM. Evidence: `.tmp/release-native-_uoqqhq_/results.json`; title and
  AmigaDOS return captures inspected. This is still CLI startup, not Workbench
  double-click/64 KiB icon-stack validation. AROS shell return remains unproven.
- Actionlint, shell syntax, CLI help and final source/cache receipt **PASS**.

**WHDLoad runtime boot/quit remains unvalidated** without a legal OS2+ host ROM.
Only WHD compilation, exact independent recompilation, structure and archive
content are validated. No remote workflow, release, commit, push, GUI launch or
cleanup was performed. Earlier failed-run evidence remains available.

## Earlier local verification — 2026-10-11 (pre-hardening)

Generated all five formats with:

```sh
bash tools/agk package --version 1.2.3 --out .tmp/astra-release-1.2.3
python3.12 tools/verify-release.py .tmp/astra-release-1.2.3 \
  --report .tmp/astra-release-verification.json
python3.12 tools/check-release-native.py .tmp/astra-release-1.2.3
```

`1.2.3` is a local validation version, not a published Git tag/release. The
recorded source HEAD is `8ade8cab3f0dda369451e84a6fa9f3cb32d6cbf7` and metadata
honestly records a dirty working tree. No commit or remote publication occurred.

| Artifact | Bytes | SHA256 |
|---|---:|---|
| `Astra-1.2.3` |543048|`fc2c8f8ec10ea0796008e550f12f38711471b69de25f67097220cc1768213011`|
| `Astra-1.2.3.adf` |901120|`ecf8820ac5c54b422f6a76702c593e6efef59d9baeaf9056fd65c4b5b3b3d357`|
| `Astra-1.2.3-HD.zip` |683219|`e297df907561201eedee9f46d0cf09384807bf0d684c32cc9587cae6f42eb1a2`|
| `Astra-1.2.3-HD.lha` |693217|`697ed460b851ee9b525cd0df9cb863d2b2e3e10fa38879ff8910d08ff6eedaf6`|
| `Astra-1.2.3-WHD.lha` |728212|`03cf6fe634e25d8ab7c36fef60a5800f27512fa3e86e5bd7343b75acdf2ccf4a`|

The authoritative full checksum manifest is
`.tmp/astra-release-1.2.3/Astra-1.2.3-SHA256SUMS`. It also covers the full
460,972-byte `Sources.zip`, notices and `release.json`. Full content comparisons
passed after extraction from ADF, ZIP and both LHAs, including exact original
icons and the identical game in all five formats. No proprietary runtime files
are included. The 4,520-byte slave SHA256 is
`f0dea919499d19dc1ad00f1e93aa9d56714720b9581905fecf7886b01bba3935`.
Independent verification checks its real Hunk/header, loader entry, version19,
NoError/EmulPriv/Examine-only flags, memory layout, Kick13 CRC, F10 metadata,
two full-game size comparisons, ANSI CRC16 `$7765`, and the game's unique
register-ABI keyboard signature. **These are compile/structure checks, not a
WHDLoad runtime pass.**

Executed checks:

- `bash tools/agk unit`: **1/1 PASS**.
- Python discovery: **162/162 PASS**, 196.959 seconds. This includes13 release
  boundary tests and the icon tests. An initial120-second harness timeout was
  reported; the suite then passed with an adequate timeout and unchanged tests.
- `actionlint .github/workflows/release.yml`, `bash -n tools/agk` and CLI help:
  **PASS**. Remote GitHub execution remains untested.
- Production build and content-based receipt passed; final cache confirms all
  seven Astra flags OFF, ACE_DEBUG OFF and Release.
- Exact packaged ADF cold-boot/title/Escape-marker checks: **PASS** on native
  baseline A500/OCS512+512 KiB/Kick1.3 and the separate AROS profile.
- Extracted HD ZIP drawer copied to a formatted16 MiB OFS hard disk:
  **PASS** for cold boot/title/Escape on A500/OCS/Kick1.3 **plus2 MiB fast RAM**.
  This is a CLI-startup test, not Workbench double-click or baseline-HD RAM proof.
- Title and post-exit captures inspected: the Kick1.3 ADF and HD show an
  AmigaDOS prompt after Escape. AROS emits the Escape marker and restores a
  grey screen; a visible AROS shell return is not established.

Successful native evidence is `.tmp/release-native-29yrwt1g/results.json` and
its `a500/`, `a500-aros/`, `hd-a500/` subdirectories. `release.json` inside the
archives is deliberately frozen at packaging time and conservatively says
native validation had not yet run. The later evidence above is bound to the
exact ADF/image hashes; archives were not rewritten after validation.

Previously reported failures remain visible: SDK legacy History.txt UTF-8
decoding (fixed with a byte-marker regression), indented Motorola symbols
(fixed in source), unsupported `amiga run` in the new HD harness (removed after
confirming power-on already runs), and a verifier expecting CMPI rather than
vasm's valid CMP-immediate-EA encoding (corrected after actual disassembly).
Failed temporary build/native directories were retained.

**Remaining limitations:** no configured legal Workbench boot disk was supplied
for icon.library rendering/double-click tests, and the native icon's64 KiB
stack request remains untested. No OS2+ host ROM was found through AGK discovery;
WHD boot/F10/Escape and WHD memory requirements are **not runtime validated**.
AROS is not being substituted as proof of WHD compatibility. All five formats
exist and pass archive/structure checks; full runtime release acceptance is
not claimed.
