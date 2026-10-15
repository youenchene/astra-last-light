#ifndef ASTRA_RENDER_H
#define ASTRA_RENDER_H

#include <ace/managers/viewport/simplebuffer.h>
#include "logic.h"

/* DOUBLE-FRAMEBUFFER CONTRACT (intentional revision of the historical
 * single-buffer frame-order rules in game/AGENTS.md):
 * - main binds pBack after each acknowledged publication; no gameplay writes
 *   target the displayed bitmap. Pixels and sprite streams use one back copper.
 * - restore the back bitmap's N-2 BOB history, animate world, update logic,
 *   draw current HUD/BOBs/sprites, wait for blitter, publish, acknowledge vblank.
 * - independent per-bitmap composition cursors consume <=8 rows / <=2 glyphs
 *   TOTAL per tick. Only complete targets are published; the first is held
 *   while the second is repaired. Simulation readiness/scene acknowledgement
 *   require both complete plus vblank acknowledgement. No full-screen copies.
 * - +40960 chip pixels offset by -18432 title-only plates = +22528 bytes,
 *   excluding descriptors. Four original title sources share one CHIP staging
 *   plate; sector labels, gameplay decor and manga stay sector-specific.
 *   Runtime free-chip telemetry on baseline A500 remains the acceptance gate.
 */

/* Shared 32-slot sprite reservation: some ACE versions initialize 32 slots
 * even though the pointer table itself consumes only sixteen MOVEs. */
#define ASTRA_COP_SPRITES 0
#define ASTRA_COP_PALETTE 32
#define ASTRA_COP_BUFFER 65
/* Four raster switches (WAIT + five controls + eight pointer MOVEs),
 * plus the PAL line-255 rollover guard, after simpleBuffer's reservation. */
#define ASTRA_COP_DECOR (ASTRA_COP_BUFFER + simpleBufferGetRawCopperlistInstructionCount(4))
#define ASTRA_COP_DECOR_COUNT 57
#define ASTRA_COP_STATUS (ASTRA_COP_DECOR + ASTRA_COP_DECOR_COUNT)
#define ASTRA_COP_STATUS_COUNT 16

UBYTE renderCreate(tView *pView, tVPort *pVPort, tSimpleBufferManager *pBuffer);
void renderPalette(void);
/* Shadow colors only: never recolor the retained visible frame. */
void renderPreparePalette(void);
/* Publish viewport colors into all 32 raw copper palette slots. */
void renderSyncPalette(void);
/* Shadow colors changed: both physical lists must receive their next update. */
void renderPaletteChanged(void);
/* Override only the unpublished title's lettering; never mutate shadow colors. */
void renderTitleFlash(UBYTE bright);
/* Bind every pixel renderer to the actual back bitmap after vblank. */
void renderBindBack(tBitMap *pBack);
/* First rendering work after vblank, before input/logic. Ready backgrounds only;
 * PLAY scrolls, BOSS and both death phases retain their background positions. */
void renderAnimate(tGameState *pState);
/* Hero 0..3, enemies 4/5, enemy bullets 6/7. Shots and bonuses are BOBs.
 * Clears entity visibility when hardware/BOB submission is rejected. */
void renderFrame(tGameState *pState);
/* Main must skip BOTH viewProcessManagers and copProcessBlocks unless ready.
 * First target cuts over atomically; the other target is then repaired hidden.
 * Acknowledge is called after publication crosses vblank, before logic. */
UBYTE renderTargetReady(void);
UBYTE renderBothReady(void);
UWORD renderRevision(void);
void renderAcknowledge(tGameState *state);
/* Composition readiness is not a display acknowledgement. After renderFrame,
 * publish copper/palette, wait for vblank, then on the NEXT tick (inside perf
 * measurement, before logicUpdate) acknowledge this epoch if Ready is true.
 * Always test the boolean: epoch 0 is valid after wrap. renderFrame sets/clears
 * presentationBusy during combat rebuilds; call it even if logicUpdate returns 0.
 * No preparation or renderer work may be moved before agkPerfBegin. */
UBYTE renderSceneReady(void);
UBYTE renderReadyScene(void); /* Same boolean, retained for parent hook naming. */
UWORD renderSceneReadyEpoch(void);
/* Caller disables sprite DMA and unloads the view first; partial create safe. */
void renderDestroy(void);

#endif
