#ifndef ASTRA_COMBAT_PERF_H
#define ASTRA_COMBAT_PERF_H
#include "logic.h"
enum { CP_RESTORE, CP_LOGIC, CP_AUDIO, CP_RENDER, CP_BOBS, CP_SPRITES,
	CP_COPPER, CP_PUBLISH, CP_WAIT, CP_INJECT, CP_COUNT };
#ifdef ASTRA_COMBAT_TIMING
void combatPerfBegin(unsigned char stage);
void combatPerfEnd(unsigned char stage);
void combatPerfFrame(const tGameState *state);
void combatPerfFlush(const tGameState *state);
#else
#define combatPerfBegin(stage) ((void)0)
#define combatPerfEnd(stage) ((void)0)
#define combatPerfFrame(state) ((void)0)
#define combatPerfFlush(state) ((void)0)
#endif
#ifdef ASTRA_COMBAT_STRESS
void combatStressBefore(tGameState *state);
void combatStressAfter(const tGameState *state);
void combatStressSubmitted(unsigned char bitmap, unsigned char copper, unsigned long clock);
void combatStressAcknowledged(unsigned char bitmap, unsigned char copper, unsigned long clock);
unsigned char combatStressCaptureHeld(void);
void combatStressRelease(void);
unsigned short combatStressCase(void);
#else
#define combatStressBefore(state) ((void)0)
#define combatStressAfter(state) ((void)0)
#define combatStressSubmitted(bitmap, copper, clock) ((void)0)
#define combatStressAcknowledged(bitmap, copper, clock) ((void)0)
#define combatStressCase() 65535
#endif
#endif
