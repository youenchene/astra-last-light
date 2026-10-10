#ifndef ASTRA_GALAXY_TRACE_H
#define ASTRA_GALAXY_TRACE_H
#ifdef ASTRA_PRESENTATION_TIMING
#include "logic.h"
void galaxyTraceBegin(void);
void galaxyTraceMemory(const void *code);
void galaxyTraceDecodeBegin(unsigned char patch);
void galaxyTraceDecodeEnd(void);
void galaxyTraceFrame(const tGameState *state);
#else
#define galaxyTraceBegin() ((void)0)
#define galaxyTraceMemory(code) ((void)0)
#define galaxyTraceDecodeBegin(patch) ((void)0)
#define galaxyTraceDecodeEnd() ((void)0)
#define galaxyTraceFrame(state) ((void)0)
#endif
#endif
