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
    return source


if __name__ == '__main__':
    Path(sys.argv[2]).write_text(transform(Path(sys.argv[1]).read_text()))
