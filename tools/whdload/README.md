# Astra Kick13 slave

The dedicated slave uses the official WHDLoad 20.0 SDK's public-domain
`kick13.s` and `kickfs.s`. `tools/release-lock.json` pins the freshly reviewed
official download and the Docker image containing vasm 2.0f and NDK includes.
`bash tools/agk package --version 1.2.3` builds it with `-m68000 -Fhunkexe`.
No global AGK files are changed. Included loader glue is MPL-2.0.

The game remains an intact 68000/OCS executable. HDINIT/BOOTDOS boot Kickstart
34.005; the loader opens `dos.library` using Exec OldOpenLibrary, loads
`data/Astra` with **DOS LoadSeg**, and calls its first segment at BPTR*4+4.
The CLI stack is 32 KiB. The slave reserves 512 KiB CHIP, 2 MiB expansion and
an additional 256 KiB for the emulated ROM. This is deliberately separate
from the native floppy's 512+512 KiB target. Host OS, WHDLoad and PRELOAD
require more memory; 4 MiB fast is a candidate, not a validated minimum.

WHDLoad itself requires host Kickstart/AmigaOS 2.0+ and at least 1 MiB RAM.
Supply WHDLoad and legal `Devs:Kickstarts/kick34005.A500` plus the matching
RTB yourself. ROMs, keys, RTBs and WHDLoad binaries are never release inputs.

Before LoadSeg, the slave checks the full executable size and ANSI CRC16
against generated `game-version.i`. Before patching, exactly one relocated
ACE keyboard signature must match. Unknown versions abort with WRONGVER.
The checked handler uses **a0/a1 register arguments**, unlike the Rugby
stack-argument ABI. Its first ten bytes push a2/d2 and load relocated
`g_pCia` into a2. The hook copies and replays those bytes for all non-F10
keys, preserving arguments and registers. F10 calls resload_Abort with
TDREASON_OK on the stack. Escape retains the original game's clean shutdown;
return from the executable also calls Abort/OK. No gameplay source changes.

The archive contains the loader source, generated version constants and
upstream Kick13/KickFS source with their public-domain notices. The SDK and
digest-pinned compiler remain build dependencies.

**Native WHDLoad boot and F10/Escape return are not yet validated.** A compiled
slave or successful archive round trip alone does not establish compatibility.
