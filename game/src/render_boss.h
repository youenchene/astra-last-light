#ifndef ASTRA_RENDER_BOSS_H
#define ASTRA_RENDER_BOSS_H

#include <ace/types.h>
#include "logic.h"

/* Called only by render_bobs, after manager creation and before reallocation.
 * Owns textures and one BOB; never creates or ends a manager/queue. */
UBYTE renderBossCreate(void);
void renderBossQueue(tGameState *pState, UBYTE show);
void renderBossDestroy(void);

#endif
