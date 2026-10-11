#ifndef ASTRA_CAMPAIGN_PROBE_H
#define ASTRA_CAMPAIGN_PROBE_H
#include "../../src/logic.h"
/* NON-SHIPPING state injection. This is not an ordinary campaign clear. */
void campaignProbeBeforeUpdate(tGameState *state);
void campaignProbeAfterFrame(tGameState *state);
#endif
