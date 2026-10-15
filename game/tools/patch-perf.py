"""Reproducible, fail-closed project-local AGK final-window accounting patch."""
from pathlib import Path
import sys


def transform(source):
    def replace(before, after):
        nonlocal source
        if source.count(before) != 1:
            raise ValueError('AGK perf source anchor missing or ambiguous: ' + before)
        source = source.replace(before, after, 1)

    replace('static ULONG s_ulSumLines;',
            'static ULONG s_ulSumLines;\nstatic ULONG s_ulReportedFrames, s_ulReportedDrops;')
    replace('static UBYTE s_isStarted;', 'static UBYTE s_isStarted, s_isFinished;')
    replace('void agkPerfReport(void) {', '''/* Same arithmetic and endpoints, cheaper common PAL50 report path. */
static UWORD astraPerfAverage(ULONG sum, UWORD frames) {
    if(sum <= 65535UL) return (UWORD)((UWORD)sum / frames);
    return (UWORD)(sum / frames);
}
static UWORD astraPerfPercent(UWORD lines, UBYTE vbls) {
    if(vbls == 1 && lines <= 655) {
        UWORD numerator = lines * 100;
        return numerator / PAL_LINES;
    }
    return (lines * 100) / (PAL_LINES * vbls);
}
void agkPerfReport(void) {''')
    replace('UWORD uwAvgLines = (UWORD)(s_ulSumLines / s_uwFrames);',
            'UWORD uwAvgLines = astraPerfAverage(s_ulSumLines, s_uwFrames);')
    replace('(uwAvgLines * 100) / (PAL_LINES * s_ubFrameVbls)',
            'astraPerfPercent(uwAvgLines, s_ubFrameVbls)')
    replace('(s_uwMaxLines * 100) / (PAL_LINES * s_ubFrameVbls)',
            'astraPerfPercent(s_uwMaxLines, s_ubFrameVbls)')
    replace('\tagkTick();', '\tagkTick();\n\tif(s_isFinished) return;')
    replace('\ts_ulLastVblank = ulVblank;',
            '\t/* Close the preceding frame, including its missed vblanks, before\n'
            '\t * reporting. The new frame includes ordinary report overhead. */\n'
            '\tif(s_uwFrames >= REPORT_EVERY) agkPerfReport();\n'
            '\ts_ulLastVblank = ulVblank;')
    replace('\tif(++s_uwFrames >= REPORT_EVERY) {\n\t\tagkPerfReport();\n\t}',
            '\t++s_uwFrames;')
    replace('\ts_uwFrames = 0;',
            '\ts_ulReportedFrames += s_uwFrames;\n'
            '\ts_ulReportedDrops += s_uwDropped;\n\ts_uwFrames = 0;')
    source += '''
/* Called at the next Begin, after previous-frame drops have been accounted,
 * before any new simulation/render work. Final report/marker/hold are outside the
 * completed-frame measurement; no dummy frame or rounded window is added. */
void astraPerfFinish(ULONG logicFrame) {
    if(s_isFinished) return;
    s_isFinished = 1;
    agkPerfReport();
    s_isStarted = 0;
    agkState("perf_complete", s_ulReportedFrames);
    agkState("dropped", s_ulReportedDrops);
    agkState("boundary_frame", logicFrame);
    agkEnd();
}
'''
    replace('#define PAL_LINES 313', '''#define PAL_LINES 313
#ifdef ASTRA_PRESENTATION_TIMING
ULONG astraTraceAgkStart;
UBYTE astraTraceAgkReport;
extern void astraTraceAgkEnd(ULONG end, UWORD whole);
#endif''')
    replace('\tif(s_uwFrames >= REPORT_EVERY) agkPerfReport();', '''#ifdef ASTRA_PRESENTATION_TIMING
    astraTraceAgkStart = ulVblank * PAL_LINES + uwLine;
    astraTraceAgkReport = s_uwFrames >= REPORT_EVERY;
#endif
\tif(s_uwFrames >= REPORT_EVERY) agkPerfReport();''')
    replace('\ts_ulSumLines += uwLines;', '''#ifdef ASTRA_PRESENTATION_TIMING
    astraTraceAgkEnd(astraTraceAgkStart + uwLines, uwLines);
#endif
\ts_ulSumLines += uwLines;''')
    return source


if __name__ == '__main__':
    Path(sys.argv[2]).write_text(transform(Path(sys.argv[1]).read_text()))
