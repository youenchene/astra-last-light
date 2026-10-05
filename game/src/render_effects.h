#ifndef ASTRA_RENDER_EFFECTS_H
#define ASTRA_RENDER_EFFECTS_H

#include <ace/types.h>
#include "logic.h"

/* Uses the existing BOB manager; initialize before its single reallocation.
 * Queue after boss, shots and pickups; caller owns begin/end and blit waits. */
UBYTE renderEffectsCreate(void);
void renderEffectsQueue(const tGameState *pState);
void renderEffectsDestroy(void);

#endif
