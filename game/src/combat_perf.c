#include "combat_perf.h"
#ifdef ASTRA_COMBAT_TIMING
#include <ace/managers/timer.h>
#include <ace/utils/custom.h>
#include <agk/debug.h>
/* Nested stages are inclusive. No heap, OS calls, or per-frame serial output.
 * PAL raster elapsed time includes interrupts and bus contention. */
static struct { ULONG start, total; UWORD line, calls, peak; } s_cost[CP_COUNT];
static UWORD s_frames, s_window, s_firstCase;
static UBYTE s_firstPhase, s_busy;
static UWORD sample(ULONG *clock) {
	ULONG before, after;
	UWORD line;
	do { before = timerGet(); line = getRayPos().bfPosY; after = timerGet(); }
	while(before != after);
	*clock = after;
	return line;
}
void combatPerfBegin(unsigned char stage) {
	s_cost[stage].line = sample(&s_cost[stage].start);
}
void combatPerfEnd(unsigned char stage) {
	ULONG clock;
	UWORD line = sample(&clock), blanks = clock - s_cost[stage].start;
	if(blanks * 313 + line < s_cost[stage].line) ++blanks;
	UWORD elapsed = blanks * 313 + line - s_cost[stage].line;
	s_cost[stage].total += elapsed;
	++s_cost[stage].calls;
	if(elapsed > s_cost[stage].peak) s_cost[stage].peak = elapsed;
}
void combatPerfFrame(const tGameState *state) {
	if(!s_frames) { s_firstPhase = state->phase; s_firstCase = combatStressCase(); }
	s_busy |= state->presentationBusy;
	if(++s_frames != 50) return;
	combatPerfFlush(state);
}
void combatPerfFlush(const tGameState *state) {
	if(!s_frames) return;
	for(UBYTE i = 0; i < CP_COUNT; ++i) {
		agkState("cp", s_window); agkState("stage", i);
		agkState("calls", s_cost[i].calls); agkState("lines", s_cost[i].total);
		agkState("peak", s_cost[i].peak); agkEnd();
		s_cost[i].total = s_cost[i].calls = s_cost[i].peak = 0;
	}
	agkState("cp_window", s_window++); agkState("frame", state->frame);
	agkState("frames", s_frames);
	agkState("first_phase", s_firstPhase); agkState("phase", state->phase);
	agkState("level", state->level); agkState("first_case", s_firstCase);
	agkState("case", combatStressCase()); agkEnd();
	agkState("cp_busy", s_window - 1); agkState("busy", s_busy); agkEnd();
	s_busy = 0;
	s_frames = 0;
}
#endif
