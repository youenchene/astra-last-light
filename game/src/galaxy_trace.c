#include "galaxy_trace.h"
#ifdef ASTRA_PRESENTATION_TIMING
#include <ace/managers/timer.h>
#include <ace/utils/custom.h>
#include <agk/debug.h>
#include <proto/exec.h>
extern const unsigned char galaxyBytes[];
#ifdef ASTRA_HUD_BOB_TIMING
#define TRACE_MARK_COUNT HB_STAMP_COUNT
static UBYTE s_valid[TRACE_MARK_COUNT];
static UWORD s_faults;
unsigned short hudBobOperations[HO_COUNT];
unsigned short hudBobPushes[HB_CATEGORY_COUNT], hudBobUnaligned[HB_CATEGORY_COUNT];
#else
#define TRACE_MARK_COUNT 33
#endif
/* Diagnostic only: six campaign burst frames or four ordinary BOB events.
 * No clocks on other frames; acceptance always uses diagnostics OFF. */
typedef struct {
    UWORD total, decode, frame, stage, marks[TRACE_MARK_COUNT], tick, pf, prefix, suffix, whole, report;
    UBYTE phase, level, busy, patch, events, effects;
#ifdef ASTRA_HUD_BOB_TIMING
    UBYTE valid[TRACE_MARK_COUNT];
    UWORD faults, operations[HO_COUNT], pushes[HB_CATEGORY_COUNT], unaligned[HB_CATEGORY_COUNT];
#endif
} tGalaxyTrace;
static tGalaxyTrace s_trace[10];
static UWORD s_count, s_omitted, s_decode;
static ULONG s_start, s_decodeStart;
static UBYTE s_patch, s_reported;
static UWORD s_marks[TRACE_MARK_COUNT];
extern ULONG astraTraceAgkStart;
extern UBYTE astraTraceAgkReport;
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
    ++s_frames;
    switch((UWORD)(state->frame+1)) {
#ifdef ASTRA_CAMPAIGN_PROBE
    case 751: case 2817: case 4879: case 6927:
#ifdef ASTRA_HUD_BOB_TIMING
    case 7704: case 7780:
#endif
#else
    case 816: case 954: case 977: case 981:
#endif
        galaxyTraceTarget=1; break;
    default: galaxyTraceTarget=0;
    }
    if(!galaxyTraceTarget) return;
    ++s_targets;
    s_start=clockLines(); s_decode=0; s_patch=0;
    for(UBYTE i=0;i<TRACE_MARK_COUNT;++i) s_marks[i]=0;
#ifdef ASTRA_HUD_BOB_TIMING
    s_faults=0;
    for(UBYTE i=0;i<TRACE_MARK_COUNT;++i) s_valid[i]=0;
    for(UBYTE i=0;i<HO_COUNT;++i) hudBobOperations[i]=0;
    for(UBYTE i=0;i<HB_CATEGORY_COUNT;++i) hudBobPushes[i]=hudBobUnaligned[i]=0;
#endif
}
void galaxyTraceMarkTarget(unsigned char mark) {
#ifdef ASTRA_HUD_BOB_TIMING
    if(mark>=TRACE_MARK_COUNT || s_valid[mark]) { ++s_faults; return; }
    s_valid[mark]=1;
#endif
    s_marks[mark]=clockLines()-s_start;
}
void galaxyTraceDecodeBegin(unsigned char patch) {
    if(galaxyTraceTarget) { s_decodeStart=clockLines(); s_patch=patch; }
}
void galaxyTraceDecodeEnd(void) {
    if(galaxyTraceTarget) s_decode+=clockLines()-s_decodeStart;
}
void galaxyTraceFrame(const tGameState *state) {
    if(s_reported || !galaxyTraceTarget) return;
    UWORD total=clockLines()-s_start;
    {
        if(s_count<10) {
            tGalaxyTrace *r=&s_trace[s_count++];
            r->total=total; r->decode=s_decode; r->frame=state->frame;
            r->stage=state->stageFrame; r->phase=state->phase; r->level=state->level;
            r->busy=state->presentationBusy; r->patch=s_patch;
            r->events=state->events; r->tick=state->boss.tick; r->pf=state->phaseFrame;
            r->effects=0;
            for(UBYTE i=0;i<EFFECT_COUNT;++i) r->effects+=state->effects[i].active;
            r->prefix=s_start-astraTraceAgkStart;
            r->report=astraTraceAgkReport;
            for(UBYTE i=0;i<TRACE_MARK_COUNT;++i) r->marks[i]=s_marks[i];
#ifdef ASTRA_HUD_BOB_TIMING
            for(UBYTE i=0;i<TRACE_MARK_COUNT;++i) r->valid[i]=s_valid[i];
            r->faults=s_faults;
            for(UBYTE i=0;i<HO_COUNT;++i) r->operations[i]=hudBobOperations[i];
            for(UBYTE i=0;i<HB_CATEGORY_COUNT;++i) {
                r->pushes[i]=hudBobPushes[i]; r->unaligned[i]=hudBobUnaligned[i];
            }
#endif
        }
        else ++s_omitted;
    }
}
/* Called after AGK has sampled its own endpoint: no additional clock read. */
void astraTraceAgkEnd(ULONG end, UWORD whole) {
    if(galaxyTraceTarget && s_count) {
        tGalaxyTrace *r=&s_trace[s_count-1];
        r->suffix=end-s_start-r->total;
        r->whole=whole;
    }
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
        agkState("it11_frame",r->frame);
        agkState("format_begin",r->marks[7]); agkState("format_end",r->marks[8]); agkEnd();
        agkState("split_frame",r->frame); agkState("prefix",r->prefix);
        agkState("suffix",r->suffix); agkState("whole",r->whole);
        agkState("report",r->report); agkEnd();
        for(UBYTE j=0;j<TRACE_MARK_COUNT;++j) {
            agkState("stamp_frame",r->frame); agkState("index",j);
            agkState("at",r->marks[j]);
#ifdef ASTRA_HUD_BOB_TIMING
            agkState("valid",r->valid[j]);
#endif
            agkEnd();
        }
#ifdef ASTRA_HUD_BOB_TIMING
        agkState("hb_frame",r->frame); agkState("faults",r->faults);
#ifdef ASTRA_HUD_BOB_DETAIL
        agkState("ops_valid",1);
#else
        agkState("ops_valid",0);
#endif
        agkEnd();
        for(UBYTE j=0;j<HO_COUNT;++j) {
            agkState("hud_op_frame",r->frame); agkState("index",j);
            agkState("count",r->operations[j]); agkEnd();
        }
        for(UBYTE j=0;j<HB_CATEGORY_COUNT;++j) {
            agkState("bob_op_frame",r->frame); agkState("category",j);
            agkState("pushes",r->pushes[j]); agkState("unaligned",r->unaligned[j]); agkEnd();
        }
#endif
    }
    agkState("galaxy_diag_omitted",s_omitted); agkEnd();
    agkState("it10_counts",s_frames); agkState("targets",s_targets);
    agkState("records",s_count); agkState("omitted",s_omitted); agkEnd();
}
#endif
