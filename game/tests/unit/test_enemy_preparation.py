"""Exercise the production enemy writer and both physical DMA caches."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT, function


class EnemyPreparationTests(unittest.TestCase):
    def test_retiring_wave_prepares_unused_slots_without_changing_scanout(self):
        source = (ROOT / 'game/src/render_enemies.c').read_text().replace(
            '__attribute__((noinline, optimize("Os"))) ', '')
        for part, name in ((0, 'pixelsLow'), (1, 'pixelsHigh')):
            anchor = f's_pStreams[{part}].pLoaded[buffer][slot] = {name};'
            if 'static void prepareNextWave' in source:
                self.assertEqual(source.count(anchor), 1)
            source = source.replace(anchor, '++copies; ' + anchor)
        stream = (ROOT / 'game/src/render_stream.h').read_text()
        stream = '\n'.join(line for line in stream.splitlines()
                           if not line.startswith('#include'))
        # Count actual image-copy cache misses, not control-word writes.
        stream = stream.replace('*pWriter->pLoaded = pPixels;',
                                '++copies; *pWriter->pLoaded = pPixels;')
        prelude = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "logic.h"
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef int16_t WORD;
typedef uint32_t ULONG;
typedef struct { UWORD value; } tMove;
typedef struct { tMove sMove; } tCopCmd;
typedef struct { tCopCmd *pList; } tCopBfr;
typedef struct { tCopBfr *pBackBfr; } tCopList;
typedef struct { tCopList *pCopList; UBYTE ubPosX, ubPosY; } tView;
#define ASTRA_COP_SPRITES 0
static unsigned copies;
static void copSetMoveVal(tMove *move, UWORD value) { move->value=value; }
'''
        declarations = source[source.index('#define ENEMY_CHANNEL'):source.index('UBYTE renderEnemiesCreate')]
        helpers = function(source, 'gatherEnemies')
        if 'static void prepareNextWave' in source:
            helpers += function(source, 'prepareNextWave')
        exercise = r'''
static ULONG rows[2][2][6*17+1];
static tCopCmd commands[2][16];
static tCopBfr copper[2];
static tCopList list;
static tView view;
static void draw(tGameState *state, unsigned buffer, unsigned count, unsigned frame) {
    list.pBackBfr=&copper[buffer];
    ULONG front[2][6*17+1];
    ULONG controls[2][6];
    memcpy(front[0],rows[0][!buffer],sizeof(front[0]));
    memcpy(front[1],rows[1][!buffer],sizeof(front[1]));
    for(unsigned part=0;part<2;++part) for(unsigned slot=0;slot<6;++slot)
        controls[part][slot]=rows[part][buffer][slot*17];
    copies=0; renderEnemiesDraw(state);
    for(unsigned part=0;part<2;++part) {
        assert(!memcmp(front[part],rows[part][!buffer],sizeof(front[part])));
        assert(rows[part][buffer][count*17]==0);
        for(unsigned slot=count+1;slot<6;++slot)
            assert(controls[part][slot]==rows[part][buffer][slot*17]);
        for(unsigned slot=0;slot<count;++slot) {
            assert(!memcmp(rows[part][buffer]+slot*17+1,s_pPixels[frame][part],16*sizeof(ULONG)));
            assert(state->enemies[slot].visible);
        }
    }
}
int main(void) {
    copper[0].pList=commands[0]; copper[1].pList=commands[1];
    view.pCopList=&list; view.ubPosX=129; view.ubPosY=44; s_pView=&view;
    for(unsigned part=0;part<2;++part) {
        s_pStreams[part].pCopperA=&copper[0];
        s_pStreams[part].ubChannel=4+part;
        s_pStreams[part].ubHeight=16; s_pStreams[part].ubSlots=6;
        for(unsigned b=0;b<2;++b) s_pStreams[part].pRows[b]=rows[part][b];
    }
    for(unsigned f=0;f<24;++f) for(unsigned p=0;p<2;++p) for(unsigned r=0;r<16;++r)
        s_pPixels[f][p][r]=1+f*100+p*20+r;
    for(unsigned level=0;level<4;++level) for(unsigned wave=0;wave<5;++wave) {
        tGameState state; logicInit(&state); state.phase=PLAY; state.level=level;
        // Get the next cycle member using actual spawning rules, not a duplicate table.
        state.wave=wave; state.waveTimer=0;
        logicUpdate(&state,0); unsigned kind=state.enemies[0].kind;
        for(unsigned slot=0;slot<6;++slot) state.enemies[slot].channel=4;
        draw(&state,0,6,level*6+kind); draw(&state,1,6,level*6+kind);
        for(unsigned count=5;count>0;--count) {
            state.enemies[count].active=0;
            state.events=0;
            for(unsigned tick=0;tick<12;++tick) {
                draw(&state,tick&1,count,level*6+kind);
                assert(copies<=2); // At most one unused attached slot per tick.
            }
        }
        state.enemies[0].active=0;
        state.events=EVENT_EXPLOSION | EVENT_BONUS_DROP;
        draw(&state,0,0,level*6+kind); assert(copies==0);
        memset(state.waves,0,sizeof(state.waves)); state.waveTimer=0;
        logicUpdate(&state,0); kind=state.enemies[0].kind;
        draw(&state,1,6,level*6+kind);
        assert(copies<=2); // Regression: formerly all twelve images reload here.
        draw(&state,0,6,level*6+kind); assert(copies<=2);
        // Rapid all-at-once retirement must fall back to exact current pixels.
        memset(state.enemies,0,sizeof(state.enemies));
        memset(state.waves,0,sizeof(state.waves)); state.waveTimer=0;
        logicUpdate(&state,0); kind=state.enemies[0].kind;
        draw(&state,1,6,level*6+kind); draw(&state,0,6,level*6+kind);
        // Final quota / death / boss never warm future enemy pixels.
        memset(state.enemies,0,sizeof(state.enemies)); state.events=0;
        state.wave=g_stageWaveQuota[level];
        draw(&state,0,0,level*6+kind); assert(copies==0);
        state.wave=1; state.phase=HERO_DYING; state.resumePhase=PLAY;
        draw(&state,1,0,level*6+kind); assert(copies==0);
        state.phase=BOSS;
        ULONG saved[2][2][6*17+1]; memcpy(saved,rows,sizeof(rows));
        copies=0; renderEnemiesDraw(&state);
        assert(copies==0 && !memcmp(saved,rows,sizeof(rows)));
    }
}
'''
        code = '\n'.join((prelude, stream, declarations, helpers, function(source, 'renderEnemiesDraw'), exercise))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'enemy.c').write_text(code)
            subprocess.run(['cc', '-std=c11', '-O1', '-fsanitize=address,undefined',
                            '-Wno-pointer-to-int-cast', '-I', str(ROOT / 'game/src'),
                            str(path / 'enemy.c'), str(ROOT / 'game/src/logic.c'),
                            '-o', str(path / 'enemy')], check=True)
            subprocess.run([str(path / 'enemy')], check=True)
