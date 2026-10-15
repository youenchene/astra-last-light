"""Independent pixel oracle for the production fixed-geometry shot blits."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT


class ShotBlitTests(unittest.TestCase):
    def test_pixels_overlaps_physical_histories_and_partial_cleanup(self):
        source=(ROOT/'game/src/render_shots.c').read_text()
        source='\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
        anchor='g_pCustom->bltsize = size;'
        self.assertEqual(source.count(anchor),1)
        source=source.replace(anchor,'testBlit(size);')
        internal=(ROOT/'game/src/render_internal.h').read_text()
        internal='\n'.join(line for line in internal.splitlines() if not line.startswith('#include'))
        prelude=r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "logic.h"
typedef uint8_t UBYTE;typedef uint16_t UWORD;typedef uint32_t ULONG;
typedef int16_t WORD;
typedef struct{UBYTE *Planes[4];UWORD BytesPerRow,Rows;UBYTE Depth,Flags;}tBitMap;
#define BMF_INTERLEAVED 1
#define hudBobPushed(category,x) ((void)0)
static unsigned allocations,frees,fail;
static void *memAllocChipClear(unsigned bytes){++allocations;return fail?0:calloc(1,bytes);}
static void memFree(void *p,unsigned bytes){(void)bytes;assert(p);++frees;free(p);}
static UBYTE renderScenesOccludes(int x,int y,unsigned w,unsigned h){(void)y;(void)w;(void)h;return x>=136;}
void renderShotsBind(tBitMap *back);
void renderShotsDestroy(void);
#define USEA 0x800
#define USEB 0x400
#define USEC 0x200
#define USED 0x100
#define MINTERM_A 0xf0
#define MINTERM_COOKIE 0xca
#define ASHIFTSHIFT 12
#define HSIZEBITS 6
typedef struct{
    UWORD bltcon0,bltcon1,bltafwm,bltalwm;
    WORD bltamod,bltbmod,bltcmod,bltdmod;
    UBYTE *bltapt,*bltbpt,*bltcpt,*bltdpt;
}tCustom;
static tCustom custom,*g_pCustom=&custom;
static void blitWait(void){}
static void testBlit(UWORD size){
    unsigned words=size&63,lines=size>>6;
    assert((words==1||words==2)&&(lines==16||lines==40));
    UBYTE *a=custom.bltapt,*b=custom.bltbpt,*d=custom.bltdpt;
    if((custom.bltcon0&255)==MINTERM_A){
        assert(words==2);
        assert(custom.bltcon1==0&&custom.bltafwm==65535&&custom.bltalwm==65535);
        for(unsigned line=0;line<lines;++line){
            memcpy(d,a,4);a+=4+custom.bltamod;d+=4+custom.bltdmod;
        }
    }else{
        unsigned shift=custom.bltcon0>>12;
        assert((custom.bltcon0&255)==MINTERM_COOKIE&&custom.bltcon1==shift<<12);
        assert(custom.bltafwm==65535&&custom.bltalwm==(words==1?65535:0));
        assert(custom.bltamod==(words==1?0:-2)&&custom.bltbmod==custom.bltamod);
        assert(custom.bltcmod==40-words*2&&custom.bltdmod==custom.bltcmod);
        assert(custom.bltcpt==custom.bltdpt);
        for(unsigned line=0;line<lines;++line){
            UWORD maskWord=*(UWORD*)a,inkWord=*(UWORD*)b;
            if(words==1)assert(!(maskWord&255)&&shift<=8);
            ULONG mask=((ULONG)maskWord<<16)>>shift,ink=((ULONG)(inkWord&maskWord)<<16)>>shift;
            UWORD *dst=(UWORD*)d;
            ULONG old=((ULONG)dst[0]<<16)|(words==2?dst[1]:0),value=(old&~mask)|ink;
            dst[0]=value>>16;if(words==2)dst[1]=value;
            a+=2;b+=2;d+=40;
        }
    }
}
'''
        exercise=r'''
static UWORD screenWords[2][256*80],expected[256*80],previous[2][256*80];
static UWORD normal[16],normalMask[16],lance[80],lanceMask[80];
static tBitMap screens[2],assets[4];
static uint32_t seed=17;
static uint32_t randomWord(void){seed=seed*1664525u+1013904223u;return seed;}
static void setup(tBitMap *bm,UWORD *data,unsigned width,unsigned rows){
    bm->BytesPerRow=width/2;bm->Rows=rows;bm->Depth=4;bm->Flags=BMF_INTERLEAVED;
    for(unsigned p=0;p<4;++p)bm->Planes[p]=(UBYTE*)(data+p*(width/16));
}
static void oracle(UWORD *dst,tGameState *s,unsigned show){
    unsigned lances=0;
    for(unsigned i=0;i<SHOT_COUNT;++i){
        tEntity *e=&s->shots[i];e->visible=0;
        unsigned charged=e->kind==SHOT_CHARGED,height=charged?10:4;
        if(!show||!e->active||e->kind>SHOT_CHARGED||e->x<0||e->x>303||e->y<56||e->y+height>216)continue;
        if((s->phase==SECTOR_INTRO||s->phase==BOSS_INTRO)&&e->x>=136)continue;
        if(charged&&lances++==4)continue;
        if(charged&&lances>4)continue;
        unsigned frame=(s->frame>>2)&1;
        UWORD *data=charged?lance+frame*40:normal,*mask=charged?lanceMask+frame*40:normalMask;
        for(unsigned row=0;row<height;++row)for(unsigned col=0;col<16;++col){
            if(!(mask[row*4]&(0x8000u>>col)))continue;
            unsigned x=e->x+col,y=e->y+row;
            for(unsigned p=0;p<4;++p){
                UWORD *word=dst+(y*4+p)*20+x/16,b=0x8000u>>(x&15);
                *word=(*word&~b)|((data[row*4+p]&(0x8000u>>col))?b:0);
            }
        }
        e->visible=1;
    }
}
int main(void){
    for(unsigned b=0;b<2;++b)setup(&screens[b],screenWords[b],320,256);
    setup(&assets[0],normal,16,4);setup(&assets[1],normalMask,16,4);
    setup(&assets[2],lance,16,20);setup(&assets[3],lanceMask,16,20);
    for(unsigned row=0;row<4;++row)for(unsigned p=0;p<4;++p){normal[row*4+p]=randomWord();normalMask[row*4+p]=0x7ffeu>>(row&1);}
    for(unsigned row=0;row<20;++row)for(unsigned p=0;p<4;++p){lance[row*4+p]=randomWord();lanceMask[row*4+p]=0xfffeu>>(row%3);}
    fail=1;assert(!renderShotsCreate(&screens[0],&screens[1],assets,assets+1,assets+2,assets+3));renderShotsDestroy();
    fail=0;assert(renderShotsCreate(&screens[0],&screens[1],assets,assets+1,assets+2,assets+3));
    for(unsigned n=0;n<1024;++n){
        unsigned b=(n/3)&1;renderShotsBind(&screens[b]);renderShotsRestore();
        assert(!memcmp(screenWords[b],previous[b],sizeof(previous[b])));
        for(unsigned w=0;w<256*80;++w)screenWords[b][w]=randomWord();
        memcpy(previous[b],screenWords[b],sizeof(previous[b]));
        memcpy(expected,screenWords[b],sizeof(expected));
        tGameState s,t;logicInit(&s);s.phase=n%5==0?SECTOR_INTRO:PLAY;s.frame=n;
        for(unsigned i=0;i<12;++i){
            tEntity *e=&s.shots[i];e->active=(n+i)%7!=0;e->kind=(n+i)%3==0;
            e->x=n%4==0?150+i%4:(n*17+i*23)%304;e->y=n%4==0?90+i%3:56+(n+i*17)%137;
        }
        unsigned show=n%11!=0;t=s;oracle(expected,&t,show);
        UWORD front[256*80];memcpy(front,screenWords[!b],sizeof(front));
        renderShotsDraw(&s,show);
        assert(!memcmp(&s,&t,sizeof(s)));
        assert(!memcmp(screenWords[b],expected,sizeof(expected)));
        assert(!memcmp(screenWords[!b],front,sizeof(front)));
    }
    for(unsigned b=0;b<2;++b){renderShotsBind(&screens[b]);renderShotsRestore();assert(!memcmp(screenWords[b],previous[b],sizeof(previous[b])));}
    assert(allocations==2);renderShotsDiscard();renderShotsDestroy();renderShotsDestroy();assert(frees==1);
}
'''
        code='\n'.join((prelude,internal,source,exercise))
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)
            for narrow in (False,True):
                fixture=code.replace('0x7ffeu>>(row&1)', '0x7f00u' if narrow else '0x7ffeu>>(row&1)')
                (path/'shots.c').write_text(fixture)
                subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined',
                                '-I',str(ROOT/'game/src'),str(path/'shots.c'),str(ROOT/'game/src/logic.c'),
                                '-o',str(path/'shots')],check=True)
                subprocess.run([str(path/'shots')],check=True)
