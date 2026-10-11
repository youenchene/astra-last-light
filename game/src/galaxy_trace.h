#ifndef ASTRA_GALAXY_TRACE_H
#define ASTRA_GALAXY_TRACE_H
#include "hud_bob_trace.h"
#ifdef ASTRA_PRESENTATION_TIMING
#include "logic.h"
void galaxyTraceBegin(const tGameState *state);
void galaxyTraceMemory(const void *code);
void galaxyTraceDecodeBegin(unsigned char patch);
void galaxyTraceDecodeEnd(void);
void galaxyTraceFrame(const tGameState *state);
extern unsigned char galaxyTraceTarget;
void galaxyTraceMarkTarget(unsigned char mark);
#ifdef ASTRA_HUD_BOB_TIMING
#ifdef ASTRA_HUD_BOB_DETAIL
#define galaxyTraceMark(mark) do { if(((mark) >= 3 && (mark) <= 5) || (mark) == 7 || (mark) == 8) { if(galaxyTraceTarget) galaxyTraceMarkTarget(mark); } } while(0)
#else
#define galaxyTraceMark(mark) do { if((mark) >= 3 && (mark) <= 5 && galaxyTraceTarget) galaxyTraceMarkTarget(mark); } while(0)
#endif
#elif defined(ASTRA_FRAME_BREAKDOWN)
#define galaxyTraceMark(mark) do { if(galaxyTraceTarget) galaxyTraceMarkTarget(mark); } while(0)
#else
#define galaxyTraceMark(mark) ((void)0)
#endif
void galaxyTraceReport(void);
#else
#define galaxyTraceBegin(state) ((void)0)
#define galaxyTraceMemory(code) ((void)0)
#define galaxyTraceDecodeBegin(patch) ((void)0)
#define galaxyTraceDecodeEnd() ((void)0)
#define galaxyTraceFrame(state) ((void)0)
#define galaxyTraceMark(mark) ((void)0)
#define galaxyTraceReport() ((void)0)
#endif
#endif
