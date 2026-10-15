"""Execute the patched AGK meter, including missed vblanks on window boundaries."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PerfBoundaryTests(unittest.TestCase):
    def test_actual_partial_counts_and_last_frame_drops(self):
        patch = load(ROOT / 'game/tools/patch-perf.py')
        kit = Path(os.environ.get('AGK_KIT', Path.home() / 'Code/amiga/amiga-game-kit'))
        source = patch.transform((kit / 'runtime/src/perf.c').read_text())
        prelude = '''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
typedef struct { UWORD bfPosY; } tRayPos;
static ULONG clockTick;
static UWORD beam = 10;
static unsigned windows, frames, drops, finalFrames, finalDrops, markers;
static unsigned recordFrames, recordDrops, maxLoad;
static ULONG timerGet(void) { return clockTick; }
static tRayPos getRayPos(void) { return (tRayPos){beam}; }
static void agkTick(void) {}
static UBYTE agkIsReady(void) { return 1; }
static void agkState(const char *key, ULONG value) {
    if(!strcmp(key,"perf frames")) { ++windows; recordFrames=value; }
    if(!strcmp(key,"dropped")) recordDrops=value;
    if(!strcmp(key,"maxload")) maxLoad=value;
    if(!strcmp(key,"perf_complete")) { ++markers; finalFrames=value; }
}
static void agkEnd(void) {
    if(markers) { finalDrops=recordDrops; return; }
    frames+=recordFrames; drops+=recordDrops;
    assert(recordFrames > 0 && recordFrames <= 50);
    /* Regular serial reporting takes time; it must stay inside the new frame. */
    beam+=12;
}
void agkPerfReport(void);
'''
        exercise = '''
int main(int argc, char **argv) {
    assert(argc==3);
    unsigned count=atoi(argv[1]), miss=atoi(argv[2]);
    /* Guarded arithmetic is byte-for-byte the original formula, including
     * large sums, long stalls, and every nonzero legacy frame divisor. */
    uint32_t seed=17;
    for(unsigned n=0;n<20000;++n) {
        seed=seed*1664525u+1013904223u;
        ULONG sum=n<1000?n:seed;
        UWORD divisor=1+n%50, lines=n<1000?n:(UWORD)seed;
        UBYTE vbls=1+n%255;
        assert(astraPerfAverage(sum,divisor)==(UWORD)(sum/divisor));
        assert(astraPerfPercent(lines,vbls)==(UWORD)((lines*100)/(313*vbls)));
        assert(astraPerfPercent(lines,1)==(UWORD)((lines*100)/313));
    }
    for(unsigned i=0;i<count;++i) {
        agkPerfBegin();
        beam+=20;
        agkPerfEnd();
        clockTick+=1+(i+1==count ? miss : 0); beam=10;
    }
    /* Boundary Begin accounts final completed-frame drops, but never End: no
     * artificial sample is added for the key/flush/marker itself. */
    agkPerfBegin();
    astraPerfFinish(count);
    astraPerfFinish(count);
    /* Harness hold ticks after completion cannot reopen the meter. */
    for(unsigned i=0;i<3;++i) { ++clockTick; agkPerfBegin(); agkPerfEnd(); }
    agkPerfReport();
    assert(frames==count && finalFrames==count);
    assert(drops==miss && finalDrops==miss);
    assert(markers==1 && windows==(count+49)/50);
    if(count%50==1 && count>1) assert(maxLoad==10); /* 20+12 lines */
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for header in ('agk/perf.h', 'agk/debug.h', 'ace/managers/timer.h', 'ace/utils/custom.h'):
                path = folder / header
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('')
            (folder/'meter.c').write_text(prelude+source+exercise)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(folder),
                            str(folder/'meter.c'),'-o',str(folder/'meter')],check=True)
            for count in (0,1,49,50,51,99,100,101):
                for miss in ((0,) if not count else (0,1,3)):
                    subprocess.run([str(folder/'meter'),str(count),str(miss)],check=True)
        with self.assertRaises(ValueError):
            patch.transform(source)

    def test_parser_rejects_missing_duplicate_and_wrong_boundaries(self):
        boundary = load(ROOT/'tools/perf_boundary.py')
        perf = {'windows':[{'frames':50,'dropped':1,'load':20,'maxload':110},
                           {'frames':7,'dropped':1,'load':30,'maxload':105}], 'dropped':2}
        text = ('AGK perf frames=50 dropped=1 load=20 maxload=110\n'
                'AGK perf frames=7 dropped=1 load=30 maxload=105\n'
                'AGK perf_complete=57 dropped=2 boundary_frame=123\n')
        self.assertEqual(boundary.complete_performance(text,perf)['measured_frames'],57)
        for bad in ('',text+text,text.replace('57','50'),text+'AGK perf frames=1\n',
                    text.replace('frames=7','frames=6'), text.replace(' boundary_frame=123','')):
            with self.assertRaises(ValueError):
                boundary.complete_performance(bad,perf)

    def test_stage_partial_flush_is_idempotent(self):
        source = (ROOT/'game/src/combat_perf.c').read_text()
        prelude = '''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
typedef struct { UWORD bfPosY; } tRayPos;
static unsigned recorded, windows, calls, lines;
static UWORD beam;
static ULONG timerGet(void) { return 0; }
static tRayPos getRayPos(void) { return (tRayPos){beam}; }
static void agkEnd(void) {}
static void agkState(const char *key, ULONG value) {
    if(!strcmp(key,"cp_window")) ++windows;
    if(!strcmp(key,"frames")) recorded+=value;
    if(!strcmp(key,"calls")) calls+=value;
    if(!strcmp(key,"lines")) lines+=value;
}
'''
        exercise = '''
int main(int argc,char **argv) {
    assert(argc==2);
    unsigned count=atoi(argv[1]);
    tGameState state={0};
    combatPerfFlush(&state);
    for(unsigned i=0;i<count;++i) {
        beam=10;
        combatPerfBegin(CP_LOGIC);
        beam=20;
        combatPerfEnd(CP_LOGIC);
        ++state.frame;
        combatPerfFrame(&state);
    }
    combatPerfFlush(&state);
    combatPerfFlush(&state);
    assert(recorded==count && windows==(count+49)/50);
    assert(calls==count && lines==count*10);
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for header in ('agk/debug.h','ace/managers/timer.h','ace/utils/custom.h'):
                path = folder/header
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('')
            (folder/'stage.c').write_text(prelude+source+exercise)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',
                            '-DASTRA_COMBAT_TIMING=1','-I',str(folder),'-I',str(ROOT/'game/src'),
                            str(folder/'stage.c'),'-o',str(folder/'stage')],check=True)
            for count in (0,1,49,50,51,100,101):
                subprocess.run([str(folder/'stage'),str(count)],check=True)
