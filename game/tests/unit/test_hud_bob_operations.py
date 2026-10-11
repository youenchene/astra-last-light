"""Execute real score and BOB eligibility paths with the diagnostic counters ON."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_title_composition import ROOT, function


class HudBobOperationTests(unittest.TestCase):
    def test_changed_glyphs_and_successful_pushes_follow_actual_eligibility(self):
        world=(ROOT/'game/src/render_world.c').read_text().replace('__attribute__((noinline)) ','')
        bobs=(ROOT/'game/src/render_bobs.c').read_text()
        prelude=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "logic.h"
#define ASTRA_HUD_BOB_DETAIL 1
#include "hud_bob_trace.h"
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
unsigned char galaxyTraceTarget=1;
unsigned short hudBobOperations[HO_COUNT],hudBobPushes[HB_CATEGORY_COUNT],hudBobUnaligned[HB_CATEGORY_COUNT];
static unsigned pushed,glyphCalls,waits;
void galaxyTraceMarkTarget(unsigned char mark) {(void)mark;}
#define galaxyTraceMark(mark) galaxyTraceMarkTarget(mark)
static struct {char scoreText[9];} history;
#define HISTORY history
static void blitWait(void) { ++waits; }
static void scoreCellDraw(UWORD x,UWORD y,UBYTE digit) {
    assert(y==6 && digit<10 && x>=162 && x<210 && (x-162)%6==0);
    ++glyphCalls;
}
typedef struct {struct {UWORD uwX,uwY;} sPos;} tBob;
#define BONUS_FRAMES BONUS_KIND_COUNT
#define BONUS_HEIGHT 16
#define BOB_WIDTH 16
#define LANCE_BOBS 4
static tBob s_pBonusBobs[BONUS_COUNT],s_pShotBobs[SHOT_COUNT],s_pLanceBobs[LANCE_BOBS];
static UBYTE *s_pBonusData[BONUS_FRAMES],*s_pBonusMask[BONUS_FRAMES],*s_pLanceData[2],*s_pLanceMask[2];
static void bobPush(tBob *b) {(void)b;++pushed;}
static void bobSetFrame(tBob *b,UBYTE *p,UBYTE *m) {(void)b;(void)p;(void)m;}
static UBYTE renderScenesOccludes(int x,int y,int w,int h) {(void)y;(void)w;(void)h;return x==100;}
'''
        exercise=r'''
int main(void) {
    memcpy(history.scoreText,"00000000",9);
    scoreDraw(600,0);
    assert(hudBobOperations[HO_SCORE_CALLS]==1 && hudBobOperations[HO_SCORE_CHANGED]==1);
    assert(hudBobOperations[HO_SCORE_GLYPHS]==glyphCalls && glyphCalls==1);
    assert(hudBobOperations[HO_SCORE_CLEARS]==0 && waits==1);
    scoreDraw(1200,0);
    assert(hudBobOperations[HO_SCORE_CHANGED]==3 && glyphCalls==3 && waits==2);
    scoreDraw(1200,0);
    assert(hudBobOperations[HO_SCORE_CALLS]==3 && glyphCalls==3 && waits==2);
    scoreDraw(1200,1);
    assert(hudBobOperations[HO_SCORE_GLYPHS]==11 && glyphCalls==11);
    assert(hudBobOperations[HO_SCORE_CLEARS]==0 && waits==3);
    assert(hudBobOperations[HO_SCORE_CHANGED]==3);
    tGameState s={0}; s.phase=PLAY;
    s.pickups[0].active=1;s.pickups[0].x=16;s.pickups[0].y=80;
    s.pickups[1]=s.pickups[0];s.pickups[1].x=-1;
    s.pickups[2]=s.pickups[0];s.pickups[2].kind=BONUS_KIND_COUNT;
    drawPickups(&s,1);
    assert(hudBobPushes[HB_PICKUP]==1 && hudBobUnaligned[HB_PICKUP]==0 && pushed==1);
    assert(s.pickups[0].visible && !s.pickups[1].visible && !s.pickups[2].visible);
    for(unsigned i=0;i<7;++i) {
        s.shots[i].active=1;s.shots[i].x=33;s.shots[i].y=80;
        s.shots[i].kind=i?SHOT_CHARGED:0;
    }
    s.shots[6].x=-1;
    drawShots(&s,1);
    assert(hudBobPushes[HB_SHOT]==1 && hudBobPushes[HB_LANCE]==4 && pushed==6);
    assert(hudBobUnaligned[HB_LANCE]==4 && !s.shots[5].visible && !s.shots[6].visible);
    drawShots(&s,0);
    assert(pushed==6);
    galaxyTraceTarget=0;
    drawPickups(&s,1);
    assert(pushed==7 && hudBobPushes[HB_PICKUP]==1);
}
'''
        code=prelude+'\n'.join(function(world,n) for n in ('numberText','scoreDraw'))
        code+='\n'.join(function(bobs,n) for n in ('fits','push','drawPickups','drawShots'))+exercise
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)
            (path/'counts.c').write_text(code)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'game/src'),
                            str(path/'counts.c'),'-o',str(path/'counts')],check=True)
            subprocess.run([str(path/'counts')],check=True)
