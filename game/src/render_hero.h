#ifndef ASTRA_RENDER_HERO_H
#define ASTRA_RENDER_HERO_H

#include <ace/utils/extview.h>
#include "logic.h"

/* Owns hardware channels 0..3: one 32x24, 15-colour hero made of two
 * attached 16px columns (0/1 and 2/3). Plain sprites, not multiplexed. */
UBYTE renderHeroCreate(const tView *pView, ULONG *pBlank);
void renderHeroDraw(const tGameState *pState);
/* Partial-create-safe; caller has stopped sprite DMA. */
void renderHeroDestroy(void);

#endif
