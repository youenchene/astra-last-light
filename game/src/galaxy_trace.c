#include "galaxy_trace.h"
#ifdef ASTRA_PRESENTATION_TIMING
#include <ace/managers/timer.h>
#include <ace/utils/custom.h>
#include <agk/debug.h>
#include <proto/exec.h>
extern const unsigned char galaxyBytes[];
/* Diagnostic only: retain the first 32 slow frames; no per-frame serial output.
 * Report overflow explicitly. Never use this intrusive trace for acceptance. */
typedef struct {
    UWORD total, decode, frame, stage;
    UBYTE phase, level, busy, patch;
} tGalaxyTrace;
static tGalaxyTrace s_trace[32];
static UWORD s_count, s_omitted, s_decode;
static ULONG s_start, s_decodeStart;
static UBYTE s_patch, s_reported;

/* Called only before systemUnuse; never make an Exec call during gameplay. */
void galaxyTraceMemory(const void *code) {
    agkState("galaxy_memory",1);
    agkState("code_flags",TypeOfMem((APTR)code));
    agkState("data_flags",TypeOfMem((APTR)galaxyBytes));
    agkState("code_address",(ULONG)code);
    agkState("data_address",(ULONG)galaxyBytes);agkEnd();
}

static ULONG clockLines(void) {
    ULONG before, after;
    UWORD line;
    do { before=timerGet(); line=getRayPos().bfPosY; after=timerGet(); } while(before!=after);
    return before*313+line;
}
void galaxyTraceBegin(void) { s_start=clockLines(); s_decode=0; s_patch=0; }
void galaxyTraceDecodeBegin(unsigned char patch) { s_decodeStart=clockLines(); s_patch=patch; }
void galaxyTraceDecodeEnd(void) { s_decode+=clockLines()-s_decodeStart; }
void galaxyTraceFrame(const tGameState *state) {
    UWORD total=clockLines()-s_start;
    if(total>=280) {
        if(s_count<32) s_trace[s_count++]=(tGalaxyTrace){total,s_decode,state->frame,
            state->stageFrame,state->phase,state->level,state->presentationBusy,s_patch};
        else ++s_omitted;
    }
    if(s_reported || state->phase!=WIN || !state->sceneReady) return;
    s_reported=1;
    for(UWORD i=0;i<s_count;++i) {
        tGalaxyTrace *r=&s_trace[i];
        agkState("galaxy_diag",i); agkState("frame",r->frame); agkState("phase",r->phase);
        agkState("level",r->level+1); agkState("stage",r->stage); agkState("busy",r->busy);
        agkState("patch",r->patch); agkState("lines",r->total); agkState("decode",r->decode); agkEnd();
    }
    agkState("galaxy_diag_omitted",s_omitted); agkEnd();
}
#endif
