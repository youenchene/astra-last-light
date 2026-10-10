"""Exercise production formatting at the word/long boundary and score wrap."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT, function


class HudNumbersTests(unittest.TestCase):
    def test_score_cache_tracks_physical_buffers_and_wrap(self):
        source = (ROOT / 'game/src/render_world.c').read_text()
        source = source.replace('__attribute__((noinline)) ', '')
        prelude = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
static struct { char scoreText[9]; } history[2];
static unsigned buffer, clears;
static char pixels[2][9];
static void *s_pScreen;
#define HISTORY history[buffer]
#define galaxyTraceMark(mark) ((void)0)
static void blitRect(void *screen,UWORD x,UWORD y,UWORD w,UWORD h,UBYTE ink) {
    (void)screen; assert(y==6 && h==7 && ink==1 && (w==6 || w==48));
    assert(x>=162 && x+w<=210); ++clears;
    memset(pixels[buffer]+(x-162)/6, ' ', w/6);
}
static void textDraw(UWORD x,UWORD y,const char *text,UBYTE scale,UBYTE ink) {
    assert(y==6 && scale==1 && ink==6);
    memcpy(pixels[buffer]+(x-162)/6,text,strlen(text));
}
'''
        exercise = r'''
int main(void) {
    const ULONG values[] = {0,600,1200,9900,10000,65535,65536,99999999,
        100000000,4294967295u,0,100,600,0};
    for(unsigned i=0;i<sizeof(values)/sizeof(*values);++i) {
        buffer=(i/3)&1; /* Deliberately not simple alternating parity. */
        char expected[9];
        snprintf(expected,sizeof(expected),"%08u",values[i]%100000000u);
        scoreDraw(values[i],i<2 || i==10);
        assert(!strcmp(pixels[buffer],expected));
        assert(!strcmp(HISTORY.scoreText,expected));
        clears=0;
        scoreDraw(values[i],0);
        assert(clears==0);
    }
    /* Composition copies the frozen score into both bitmap histories. */
    for(buffer=0;buffer<2;++buffer) {
        numberText(HISTORY.scoreText,12345678,8);
        memcpy(pixels[buffer],HISTORY.scoreText,9);
    }
    for(buffer=0;buffer<2;++buffer) {
        scoreDraw(12345679,0);
        assert(!strcmp(pixels[buffer],"12345679"));
    }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'cache.c').write_text(prelude + function(source, 'numberText') +
                                         function(source, 'scoreDraw') + exercise)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(path / 'cache.c'), '-o', str(path / 'cache')], check=True)
            subprocess.run([str(path / 'cache')], check=True)

    def test_counters_scores_and_word_boundary(self):
        source = (ROOT / 'game/src/render_world.c').read_text()
        source = source.replace('__attribute__((noinline)) ', '')
        prelude = '''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
'''
        exercise = '''
static void check(uint32_t value, unsigned digits) {
    char actual[12], expected[12];
    memset(actual, 0x55, sizeof(actual));
    numberText(actual, value, digits);
    snprintf(expected, sizeof(expected), "%0*u", digits,
        value % (digits == 1 ? 10 : 100000000));
    assert(!strcmp(actual, expected));
    assert(actual[digits + 1] == 0x55);
}
int main(void) {
    for(uint32_t n = 0; n <= 65536; ++n) check(n, 8);
    for(uint32_t n = 0; n < 256; ++n) check(n, 1);
    const uint32_t edges[] = {9999999,10000000,99999999,100000000,
        4294967294u,4294967295u};
    for(unsigned i=0;i<sizeof(edges)/sizeof(*edges);++i) check(edges[i],8);
    uint32_t n = 12345;
    for(unsigned i=0;i<100000;++i) {
        n = n * 1664525u + 1013904223u;
        check(n,8);
    }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'numbers.c').write_text(prelude + function(source, 'numberText') + exercise)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(path / 'numbers.c'), '-o', str(path / 'numbers')], check=True)
            subprocess.run([str(path / 'numbers')], check=True)
