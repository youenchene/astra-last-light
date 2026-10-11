#ifndef ASTRA_RENDER_ENEMIES_H
#define ASTRA_RENDER_ENEMIES_H

#include <ace/utils/extview.h>
#include "logic.h"

/* Publishes attached pair 4/5 only when logic's hostile mask excludes 4.
 * Up to six 16x16 enemies/asteroids, frozen during HERO_DYING from PLAY.
 * Publishes blank in other owned phases; never overwrites boss bullets.
 * Borrows the view and blank sprite word. Palette is external. */
UBYTE renderEnemiesCreate(const tView *pView, ULONG *pBlank);
/* Rejected entities get visible = 0, so they cannot collide next tick. */
void renderEnemiesDraw(tGameState *pState);
/* Idempotent/partial-create-safe; stop sprite DMA first. */
void renderEnemiesDestroy(void);

#endif
