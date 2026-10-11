"""Execute the actual opaque score path against independent source-font pixels."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT, function
from test_presentation_rows import source_fonts


class ScoreCellTests(unittest.TestCase):
    def test_all_alignments_and_physical_histories_under_sanitizers(self):
        source = (ROOT / 'game/src/render_world.c').read_text().replace('__attribute__((noinline)) ', '')
        prelude = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../art/localization.h"
#include "hud_bob_trace.h"
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
typedef struct { UBYTE *Planes[4]; UWORD BytesPerRow; UBYTE Depth; } tBitMap;
static UBYTE pixels[40960], fontPixels[504];
static tBitMap bitmap, font, *s_pScreen=&bitmap, *s_pFont=&font;
static struct { char scoreText[9]; } history[2];
static unsigned buffer, waits;
#define HISTORY history[buffer]
#define galaxyTraceMark(mark) ((void)0)
static void blitWait(void) { ++waits; }
static void pixel(UBYTE *dst,unsigned x,unsigned y,unsigned ink) {
    for(unsigned p=0;p<4;++p) {
        unsigned offset=y*160+p*40+x/8, mask=128>>(x&7);
        dst[offset]=(dst[offset]&~mask)|((ink&(1u<<p))?mask:0);
    }
}
'''
        prelude += 'static const UBYTE glyphs[36][7]={' + ','.join(
            '{' + ','.join(map(str, row)) + '}' for row in source_fonts()[1]) + '};\n'
        declarations = ''.join(re.search(r'static ULONG ' + name + r'[^;]+;', source)[0]
                               for name in ('s_pGlyphMasks', 's_bossLabel'))
        exercise = r'''
static uint32_t seed=0x31415926;
static uint32_t randomWord(void) { seed=seed*1664525u+1013904223u; return seed; }
static void background(unsigned kind) {
    for(unsigned y=0;y<256;++y) for(unsigned p=0;p<4;++p) for(unsigned b=0;b<40;++b)
        pixels[y*160+p*40+b]=kind<16 ? ((kind&(1u<<p))?255:0) :
            kind==16 ? ((y+b+p)&1?0xa5:0x5a) : randomWord()>>24;
}
static void oracleCell(UBYTE *dst,unsigned x,unsigned digit) {
    for(unsigned row=0;row<7;++row) for(unsigned col=0;col<6;++col)
        pixel(dst,x+col,6+row,col<5 && (glyphs[26+digit][row]&(16u>>col))?6:1);
}
static void oracleScore(UBYTE *dst,ULONG value) {
    char text[9]; snprintf(text,sizeof(text),"%08u",value%100000000u);
    for(unsigned i=0;i<8;++i) oracleCell(dst,162+i*6,text[i]-'0');
}
int main(void) {
    bitmap.BytesPerRow=160; bitmap.Depth=4;
    for(unsigned p=0;p<4;++p) bitmap.Planes[p]=pixels+p*40;
    font.BytesPerRow=2; font.Depth=1; font.Planes[0]=fontPixels;
    for(unsigned g=0;g<36;++g) for(unsigned r=0;r<7;++r)
        fontPixels[(g*7+r)*2]=glyphs[g][r]<<3;
    fontMasksCreate();
    for(unsigned g=0;g<36;++g) for(unsigned r=0;r<7;++r)
        assert(s_pGlyphMasks[0][g][r]==(ULONG)glyphs[g][r]<<27);
    UBYTE expected[40960]; unsigned cells=0;
    for(unsigned x=144;x<160;++x) for(unsigned digit=0;digit<10;++digit)
        for(unsigned bg=0;bg<18;++bg) {
            background(bg); memcpy(expected,pixels,sizeof(pixels));
            oracleCell(expected,x,digit); scoreCellDraw(x,6,digit);
            assert(!memcmp(pixels,expected,sizeof(pixels))); ++cells;
        }
    static UBYTE images[2][40960];
    const ULONG edges[]={0,9,10,99,100,999,1000,9999,10000,65535,65536,
        9999999,10000000,99999999,100000000,4294967295u,0,600,1200};
    for(buffer=0;buffer<2;++buffer) {
        background(17); oracleScore(pixels,0);
        memcpy(images[buffer],pixels,sizeof(pixels));
        memcpy(HISTORY.scoreText,"00000000",9);
    }
    for(unsigned n=0;n<5019;++n) {
        ULONG score=n<19?edges[n]:randomWord();
        buffer=(n/3)&1;
        UBYTE dirty=n%31==0;
        char text[9]; snprintf(text,sizeof(text),"%08u",score%100000000u);
        unsigned changed=memcmp(HISTORY.scoreText,text,8)!=0;
        memcpy(pixels,images[buffer],sizeof(pixels));
        memcpy(expected,pixels,sizeof(pixels)); oracleScore(expected,score);
        waits=0; scoreDraw(score,dirty);
        assert(waits==(unsigned)(dirty||changed));
        assert(!memcmp(pixels,expected,sizeof(pixels)));
        assert(!memcmp(HISTORY.scoreText,text,8));
        memcpy(images[buffer],pixels,sizeof(pixels));
        for(unsigned repeat=0;repeat<2;++repeat) {
            waits=0; scoreDraw(score,0);
            assert(!waits && !memcmp(pixels,expected,sizeof(pixels)));
        }
        if(n%97==0) for(unsigned b=0;b<2;++b) {
            oracleScore(images[b],12345678);
            numberText(history[b].scoreText,12345678,8);
        }
    }
    printf("PASS score: %u cells, 5019 transitions, 10038 unchanged draws, 252 mask rows\n",cells);
}
'''
        code = prelude + declarations + '\n'.join(function(source, name) for name in (
            'pixelRead', 'fontMasksCreate', 'numberText', 'scoreCellDraw', 'scoreDraw')) + exercise
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'score.c').write_text(code)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O1',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            '-I', str(ROOT / 'game/src'), str(path / 'score.c'),
                            '-o', str(path / 'score')], check=True)
            subprocess.run([str(path / 'score')], check=True)
