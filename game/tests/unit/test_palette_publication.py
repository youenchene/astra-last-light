"""Execute palette publication, including physical-buffer title flashes."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT, function


class PalettePublicationTests(unittest.TestCase):
    def test_idle_lists_and_flash_restoration(self):
        source=(ROOT/'game/src/render.c').read_text()
        prelude=r'''
#include <assert.h>
#include <stdint.h>
typedef uint8_t UBYTE;typedef uint16_t UWORD;
typedef struct{UWORD value;}tMove;
typedef struct{tMove sMove;}tCopCmd;
typedef struct{tCopCmd *pList;}tCopBfr;
typedef struct{tCopBfr *pBackBfr;}tCopList;
typedef struct{tCopList *pCopList;}tView;
typedef struct{UWORD *pPalette;}tVPort;
static tView *s_pView;static tVPort *s_pVPort;
static tCopBfr *s_paletteCopperA;
static UBYTE s_paletteDirty[2];
#define ASTRA_COP_PALETTE 32
static unsigned writes;
static void copSetMoveVal(tMove *move,UWORD value){move->value=value;++writes;}
'''
        names=['renderSyncPalette','renderTitleFlash']
        if 'void renderPaletteChanged(' in source:
            names.insert(0,'renderPaletteChanged')
        else:
            prelude+='static void renderPaletteChanged(void){s_paletteDirty[0]=s_paletteDirty[1]=1;}\n'
        exercise=r'''
int main(void){
    tCopCmd commands[2][64]={0};tCopBfr copper[2]={{commands[0]},{commands[1]}};
    UWORD colors[32];tVPort port={colors};tCopList list={&copper[0]};tView view={&list};
    s_pView=&view;s_pVPort=&port;s_paletteCopperA=&copper[0];
    for(unsigned i=0;i<32;++i)colors[i]=i*17;
    renderPaletteChanged();
    for(unsigned n=0;n<40;++n){
        unsigned b=n&1;list.pBackBfr=&copper[b];writes=0;renderSyncPalette();
        assert(writes==(n<2?32:0));
        for(unsigned i=0;i<32;++i)assert(commands[b][32+i].sMove.value==colors[i]);
    }
    colors[0]=0x102;colors[4]=0xbdf;colors[11]=0xfa9;renderPaletteChanged();
    for(unsigned b=0;b<2;++b){list.pBackBfr=&copper[b];writes=0;renderSyncPalette();assert(writes==32);}
    list.pBackBfr=&copper[0];renderTitleFlash(1);
    assert(commands[0][38].sMove.value==65535>>4&&commands[0][46].sMove.value==65535>>4);
    list.pBackBfr=&copper[1];writes=0;renderSyncPalette();assert(!writes);
    list.pBackBfr=&copper[0];writes=0;renderSyncPalette();assert(writes==32);
    assert(commands[0][38].sMove.value==colors[6]&&commands[0][46].sMove.value==colors[14]);
    for(unsigned n=0;n<10;++n){
        list.pBackBfr=&copper[n&1];colors[1]=n;renderPaletteChanged();writes=0;
        renderSyncPalette();assert(writes==32&&commands[n&1][33].sMove.value==n);
    }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'palette.c').write_text(prelude+'\n'.join(function(source,n) for n in names)+exercise)
            subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined',str(path/'palette.c'),'-o',str(path/'palette')],check=True)
            subprocess.run([str(path/'palette')],check=True)
