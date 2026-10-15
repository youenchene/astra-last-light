"""Independent whole-bitmap oracle for byte-aligned tiny HUD bar deltas."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT, function


class ChargePatchTests(unittest.TestCase):
    def test_each_bar_position_and_cross_byte_delta(self):
        source=(ROOT/'game/src/render_world.c').read_text()
        prelude=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t UBYTE;typedef uint16_t UWORD;
typedef struct{UBYTE *Planes[4];UWORD BytesPerRow;}tBitMap;
static UBYTE pixels[40960],expected[40960];
static tBitMap bitmap,*s_pScreen=&bitmap;
static unsigned waits;
static void blitWait(void){++waits;}
'''
        exercise=r'''
int main(void){
    bitmap.BytesPerRow=160;for(unsigned p=0;p<4;++p)bitmap.Planes[p]=pixels+p*40;
    for(unsigned first=0;first<100;++first)for(unsigned width=1;width<=4&&first+width<=100;++width)
        for(unsigned c=0;c<2;++c){
            unsigned color=c?15:2;
            for(unsigned b=0;b<40960;++b)pixels[b]=(b*17+first+width)&255;
            memcpy(expected,pixels,sizeof(pixels));
            for(unsigned y=19;y<23;++y)for(unsigned x=44+first;x<44+first+width;++x)
                for(unsigned p=0;p<4;++p){
                    unsigned offset=y*160+p*40+x/8,mask=128>>(x&7);
                    expected[offset]=(expected[offset]&~mask)|((color&(1u<<p))?mask:0);
                }
            waits=0;chargePatch(first,width,color);assert(waits==1);
            assert(!memcmp(pixels,expected,sizeof(pixels)));
        }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'bar.c').write_text(prelude+function(source,'chargePatch')+exercise)
            subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined',str(path/'bar.c'),'-o',str(path/'bar')],check=True)
            subprocess.run([str(path/'bar')],check=True)
