#ifndef ASTRA_CAMPAIGN_AUDIO_H
#define ASTRA_CAMPAIGN_AUDIO_H

#include <ace/types.h>
#include "logic.h"

/* Forget playback after shared-player creation/destruction; preserve mute.
 * Does not touch hardware, so it cannot interrupt the original ACE intro. */
void campaignAudioReset(void);

/* Call only after both startup logos, once per frame with an edge-triggered
 * muteToggle. Levels are zero-based. Scene/death phases retain sector music. */
void campaignAudioUpdate(UBYTE level, tPhase phase, UBYTE muteToggle);

#endif
