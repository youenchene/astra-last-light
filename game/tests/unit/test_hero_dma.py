"""Exercise both prebuilt hero images and physical copper/DMA buffers."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT, function


class HeroDmaTests(unittest.TestCase):
    def test_animation_only_writes_back_control_words(self):
        source=(ROOT/'game/src/render_hero.c').read_text()
        header=(ROOT/'game/src/render_stream.h').read_text()
        header='\n'.join(line for line in header.splitlines() if not line.startswith('#include'))
        declarations=source[source.index('#define HERO_HEIGHT'):source.index('/* Cold conversion')]
        prelude=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "hero_presentation.h"
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
typedef struct{UWORD value;}tMove;
typedef struct{tMove sMove;}tCopCmd;
typedef struct{tCopCmd *pList;}tCopBfr;
typedef struct{tCopBfr *pBackBfr;}tCopList;
typedef struct{tCopList *pCopList;UBYTE ubPosX,ubPosY;}tView;
#define ASTRA_COP_SPRITES 0
static void copSetMoveVal(tMove *p,UWORD v){p->value=v;}
'''
        exercise=r'''
static ULONG rows[4][2][51];
static tCopCmd commands[2][16];
static tCopBfr copper[2];static tCopList list;static tView view;
int main(void){
    copper[0].pList=commands[0];copper[1].pList=commands[1];
    view.pCopList=&list;view.ubPosX=129;view.ubPosY=44;s_pView=&view;
    for(unsigned part=0;part<4;++part){
        s_pStreams[part].pCopperA=&copper[0];s_pStreams[part].ubChannel=part;
        for(unsigned b=0;b<2;++b){
            s_pStreams[part].pRows[b]=rows[part][b];
            for(unsigned f=0;f<2;++f)for(unsigned r=1;r<=24;++r)
                rows[part][b][f*25+r]=1+part*100+f*30+r;
        }
    }
    for(unsigned n=0;n<2048;++n){
        unsigned b=(n/3)&1;list.pBackBfr=&copper[b];
        tGameState s;logicInit(&s);s.phase=PLAY;s.frame=n;s.x=n%289;s.y=56+n%137;
        s.heroBlink=n%3==0;s.invulnerable=n%7;
        ULONG before[4][2][51];memcpy(before,rows,sizeof(rows));
        renderHeroDraw(&s);
        unsigned f=(n>>3)&1,enabled=heroPresentationVisible(&s);
        for(unsigned part=0;part<4;++part){
            assert(!memcmp(before[part][!b],rows[part][!b],sizeof(rows[part][!b])));
            for(unsigned frame=0;frame<2;++frame)for(unsigned r=1;r<=24;++r)
                assert(before[part][b][frame*25+r]==rows[part][b][frame*25+r]);
            UWORD *control=(UWORD*)&rows[part][b][f*25];
            if(enabled){
                unsigned x=128+s.x+(part/2)*16,start=44+s.y,stop=start+24;
                assert(control[0]==(UWORD)((start<<8)|((x>>1)&255)));
                assert(control[1]==(UWORD)((stop<<8)|((part&1)?128:0)|((start>>6)&4)|((stop>>7)&2)|(x&1)));
                assert(rows[part][b][(f+1)*25]==0);
            }else assert(rows[part][b][f*25]==0);
            uint32_t address=(uintptr_t)&rows[part][b][f*25];
            assert(commands[b][part*2].sMove.value==(address>>16));
            assert(commands[b][part*2+1].sMove.value==(address&65535));
        }
    }
}
'''
        code='\n'.join((prelude,header,declarations,function(source,'renderHeroDraw'),exercise))
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'hero.c').write_text(code)
            subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined',
                            '-Wno-pointer-to-int-cast','-I',str(ROOT/'game/src'),
                            str(path/'hero.c'),str(ROOT/'game/src/logic.c'),'-o',str(path/'hero')],check=True)
            subprocess.run([str(path/'hero')],check=True)
