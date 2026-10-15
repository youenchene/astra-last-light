"""Compare incremental copper scroll commands with the complete builder."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_title_composition import ROOT, function

class DecorCopperTests(unittest.TestCase):
    def test_every_scroll_pair_preserves_all_commands(self):
        source=(ROOT/'game/src/render_world.c').read_text()
        prelude=r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
typedef uint8_t UBYTE;typedef uint16_t UWORD;typedef uint32_t ULONG;typedef int32_t LONG;
typedef struct{uintptr_t reg;UWORD value;}tMove;
typedef struct{UWORD x,y;}tWait;
typedef struct{tMove sMove;tWait sWait;}tCopCmd;
typedef struct{UBYTE *Planes[4];UWORD BytesPerRow;}tBitMap;
typedef struct{UBYTE ubPosY;}tView;
typedef struct{tView *pView;UWORD uwOffsY;}tVPort;
static tBitMap bitmap,*s_pDecor=&bitmap;
static tVPort port,*s_pVPort=&port;
static struct{UWORD ddfstrt,ddfstop,bpl1mod,bpl2mod,bplcon1,bplpt[8];}custom,*g_pCustom=&custom;
static struct{UWORD uwHi,uwLo;}g_pBplFetch[4];
static UWORD fetchModeGetCopWaitX(const tVPort *p){(void)p;return 0xdf;}
static UWORD fetchModeGetDDfStrt(const tVPort *p){(void)p;return 56;}
static UWORD fetchModeGetDDfStop(const tVPort *p){(void)p;return 208;}
static void fetchModeApplyXScrollCopper(const tVPort *p,UWORD *start,UWORD *mod){(void)p;*start-=8;*mod-=2;}
static LONG fetchModeCalcBplOffsetX(const tVPort *p,UWORD scroll,UBYTE fine){(void)p;(void)fine;return ((scroll-1)>>4)*2;}
static UWORD fetchModeCalcBplShift(const tVPort *p,UWORD scroll,UBYTE fine){(void)p;(void)fine;return ((-scroll)&15)*17;}
static void copSetMove(tMove *m,void *reg,UWORD value){m->reg=(uintptr_t)reg;m->value=value;}
static void copSetMoveVal(tMove *m,UWORD value){m->value=value;}
static void copSetWait(tWait *w,UWORD x,UWORD y){w->x=x;w->y=y;}
'''
        exercise=r'''
int main(void){
    tView view={44};port.pView=&view;
    static UBYTE data[40000];bitmap.BytesPerRow=192;
    for(unsigned p=0;p<4;++p)bitmap.Planes[p]=data+p*48;
    for(unsigned level=0;level<4;++level)for(unsigned band=0;band<2;++band)
    for(unsigned before=0;before<64;++before)for(unsigned after=0;after<64;++after){
        tCopCmd a[14]={0},b[14]={0};unsigned y=band?220:29,source=level*48+band*24;
        decorCopperSwitch(a,y,&bitmap,source,before,1);memcpy(b,a,sizeof(a));
        decorCopperSwitch(a,y,&bitmap,source,after,1);decorCopperScroll(b,y,source,before,after);
        assert(!memcmp(a,b,sizeof(a)));
    }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'copper.c').write_text(prelude+function(source,'decorCopperSwitch')+function(source,'decorCopperScroll')+exercise)
            subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined','-Wno-pointer-to-int-cast',str(path/'copper.c'),'-o',str(path/'copper')],check=True)
            subprocess.run([str(path/'copper')],check=True)
