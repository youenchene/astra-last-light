#include "galaxy_trace.h"
#ifdef ASTRA_PRESENTATION_TIMING
#include <ace/managers/timer.h>
#include <ace/utils/custom.h>
#include <agk/debug.h>
#include <proto/exec.h>
extern const unsigned char galaxyBytes[];
/* Diagnostic only: retain slow frames and selected it9j event frames, with
 * explicit counts/overflow. Timing perturbs DMA/IRQ alignment: acceptance is OFF. */
typedef struct {
    UWORD total, decode, frame, stage, marks[7], tick, pf;
    UBYTE phase, level, busy, patch, events, effects;
} tGalaxyTrace;
static tGalaxyTrace s_trace[64];
static UWORD s_count, s_omitted, s_decode;
static ULONG s_start, s_decodeStart;
static UBYTE s_patch, s_reported;
static UWORD s_marks[7];
unsigned char galaxyTraceTarget;
static UWORD s_frames, s_targets;

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
void galaxyTraceBegin(const tGameState *state) {
    s_start=clockLines(); s_decode=0; s_patch=0;
    /* Canonical it9j frame IDs: F pickups, six-kill bursts, first boss draws,
     * first-sector deaths, S4 post-respawn, ordinary BOB stage116. No prep or
     * simulation timing changes are permitted when using these selectors. */
    switch((UWORD)(state->frame+1)) {
    case 713: case 721: case 725: case 751: case 801: case 816:
    case 1416: case 1585: case 2817: case 3487: case 4879: case 5550:
    case 6927: case 7597: case 7780: galaxyTraceTarget=1; break;
    default: galaxyTraceTarget=0;
    }
    ++s_frames; s_targets+=galaxyTraceTarget;
    for(UBYTE i=0;i<7;++i) s_marks[i]=0;
}
void galaxyTraceMarkTarget(unsigned char mark) { s_marks[mark]=clockLines()-s_start; }
void galaxyTraceDecodeBegin(unsigned char patch) { s_decodeStart=clockLines(); s_patch=patch; }
void galaxyTraceDecodeEnd(void) { s_decode+=clockLines()-s_decodeStart; }
void galaxyTraceFrame(const tGameState *state) {
    UWORD total=clockLines()-s_start;
    if(s_reported) return;
    if(total>=280 || galaxyTraceTarget) {
        if(s_count<64) {
            tGalaxyTrace *r=&s_trace[s_count++];
            r->total=total; r->decode=s_decode; r->frame=state->frame;
            r->stage=state->stageFrame; r->phase=state->phase; r->level=state->level;
            r->busy=state->presentationBusy; r->patch=s_patch;
            r->events=state->events; r->tick=state->boss.tick; r->pf=state->phaseFrame;
            r->effects=0;
            for(UBYTE i=0;i<EFFECT_COUNT;++i) r->effects+=state->effects[i].active;
            for(UBYTE i=0;i<7;++i) r->marks[i]=s_marks[i];
        }
        else ++s_omitted;
    }
    if(state->phase==WIN && state->sceneReady) galaxyTraceReport();
}
void galaxyTraceReport(void) {
    if(s_reported) return;
    s_reported=1;
    for(UWORD i=0;i<s_count;++i) {
        tGalaxyTrace *r=&s_trace[i];
        agkState("galaxy_diag",i); agkState("frame",r->frame); agkState("phase",r->phase);
        agkState("level",r->level+1); agkState("stage",r->stage); agkState("busy",r->busy);
        agkState("patch",r->patch); agkState("lines",r->total); agkState("decode",r->decode); agkEnd();
        agkState("it10_frame",r->frame); agkState("events",r->events);
        agkState("effects",r->effects); agkState("tick",r->tick); agkState("pf",r->pf);
        agkState("restore_end",r->marks[0]); agkState("logic_end",r->marks[1]);
        agkState("audio_end",r->marks[2]); agkState("hud_begin",r->marks[3]);
        agkState("hud_end",r->marks[4]); agkState("bobs_end",r->marks[5]);
        agkState("render_end",r->marks[6]); agkEnd();
    }
    agkState("galaxy_diag_omitted",s_omitted); agkEnd();
    agkState("it10_counts",s_frames); agkState("targets",s_targets);
    agkState("records",s_count); agkState("omitted",s_omitted); agkEnd();
}
#endif
