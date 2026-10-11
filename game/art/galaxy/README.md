# Selected fixed galaxy backgrounds — accepted it9j

These are the four **unmodified Retro Diffusion masters** selected by the user:
Graveyard C, Nebula B, Foundry B and Citadel A. `manifest.json` preserves each
original prompt, seed, task ID, request/image hash, quote and actual charge.
The original twelve-image batch cost USD 2.16 (four selected images cost USD 0.72
within that batch). Integration made **no paid requests: USD 0.00 additional**.
The manifest's `image` is the original generation-directory-relative location;
the durable master here is `<job.id>.png`. No additional planet or world art exists.

`*.rgb.hex` is a lossless RGB extraction, hashed in each manifest job. It makes the
Docker generator stdlib-only, following the existing selected-story pipeline.
The independent tests decode the PNG itself, not this extraction or generated C.

## Offline derivative

`python3.12 game/tools/make-galaxy.py --check` validates provenance and generated
`game/src/galaxy_data.c`. Normal generation omits `--check`.

- The source is **256×128**, expanded to **320×160** with explicit floor-coordinate
  nearest neighbour: source `(x*4//5,y*4//5)`. Runtime destination is y56–215.
- RGB channels are multiplied by 3/4 with integer truncation; Nebula uses 1/2.
  Quantization minimizes squared RGB distance to **effective inks 0,1,2,3**,
  breaking ties toward the lower index. There is no dithering or global recoloring.
- Effective ink 0 is sector-specific `#001/#102/#101/#001`; ink 4 is live `#BDF`.
  Allowed background inks and plane-2 XOR partners are `0→4`, `1→5 (#89A)`,
  `2→6 (#CEF)`, `3→7 (#FFF)`. Thus every moving star remains bright, and its next
  XOR erases back to the exact underlying galaxy. Warm master details quantize
  into the existing cool low-ink palette; this is an intentional offline derivative.
- Each row contains independently indexed **nonzero spans** on planes 0/1;
  palette indices never use planes 2/3. Equal encoded rows share immutable source
  data, **never framebuffer pixels**. A row starts with span count and write-byte
  count. Each span has `(plane<<6)|byteColumn`, then length 1–40 with bit 7 set
  for repeated data (one byte), otherwise literal data (length bytes). Zero runs
  are omitted; no span crosses a plane boundary.
- Payload: 9,228 span bytes and 1,280 row-index bytes: **10,508 ordinary-data
  bytes**, not a CHIP bitmap. This saves 6,174 bytes versus rejected it9g.
  Ordinary data does consume RAM and spills into CHIP on A500; see measured ledger.

Both framebuffers have their rectangle cleared on all four planes before painting.
The caller records `galaxyBaseCleared` per physical bitmap and passes it explicitly;
without it the writer refuses work. `blitWait()` precedes painting. Each call admits
complete rows within **320 written bytes / 64 row-or-span operations / eight rows**.
Row metadata reads, including refused admission, consume one operation; every span
consumes one operation even if outside a patch. Skips perform no framebuffer write.
Masked edge writes preserve all outside bits. Caller-owned cursors are per bitmap.
Opening closure restores old BOBs, clears each patch once, paints it incrementally,
then XORs that bitmap's retained star history. The final patch and the first heavy
foreground/BOB publication are separate work steps; no incomplete frame is shown.

TITLE/WIN bypass the galaxy. Active gameplay never calls the decoder. The original
48-seed/48-row sequence still advances fully, dropping original indices `i%4==0`;
the remaining 36 stars retain exact Y, X, widths, periods 8/4/2 and stagger.

## Acceptance

All four native source images, star motion and pauses pass on both profiles.
**it9j is accepted for the requested visual change and scoped performance gain**:
campaign it7→it9j is 8/116%→7/116% A500 and 7/112%→6/110% AROS (drops/peak load).
Ordinary BOB is 3/114%→0/95% A500 and 2/107%→0/90% AROS. The global 0-drop/90%
gate still fails on A500. See `docs/combat-performance.md`, it9, for measured
trials, remaining gaps, latency and the observed RAM cost of ordinary-data spill.
