#ifndef ASTRA_RENDER_BOBS_H
#define ASTRA_RENDER_BOBS_H

#include <ace/utils/bitmap.h>
#include "logic.h"

/* Blitter objects: four bonus pickups (16x16), player shots (16x4 bolt) and
 * charged lances (16x10, two flash frames), a 64x48 boss and eight effects.
 * Boss/effect children share this manager and its single reallocation.
 *
 * Borrows distinct 320x256, 4bpp interleaved CHIP front/back screens.
 * Owns the ACE BOB manager and child lifetimes; children own their textures.
 * Create once with the OS available; no other BOB manager may be active.
 * Requires ACE_BOB_WRAP_Y=false and ACE_BOB_PRISTINE_BUFFER disabled. */
UBYTE renderBobsCreate(tBitMap *pFront, tBitMap *pScreen);
void renderBobsBind(tBitMap *pScreen);

/* Frame order, including frames outside PLAY/BOSS:
 *   Begin -> parent WorldAnimate -> input/logic -> HUD -> Draw(current state).
 * On scene changes close an empty queue, then Discard before composition.
 * Begin selects the actual back bitmap's queue, restores its N-2 background
 * and waits before world animation may blit. */
void renderBobsBegin(void);

/* AFTER world animation and logic, using the current state.
 * visible = drawn this frame; undrawable shots/pickups get visible = 0,
 * so they cannot collide on the next tick. Waits for the blitter. */
void renderBobsDraw(tGameState *pState);

/* Only after a full world redraw: drop stale saved backgrounds. */
void renderBobsDiscard(void);

/* Waits for the blitter; destroys manager before textures. Idempotent. */
void renderBobsDestroy(void);

#endif
