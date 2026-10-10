"""Execute production navigation pixels against an independent indexed drawing."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT, function


class TitleNavigationTests(unittest.TestCase):
    def test_metallic_pixels_mirror_bounds_and_three_row_budget(self):
        source = (ROOT / 'game/src/render_world.c').read_text()
        prelude = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
typedef struct { UBYTE *Planes[4]; } tBitMap;
static UBYTE pixels[40960];
static tBitMap bitmap, *s_pScreen = &bitmap;
static void blitWait(void) {}
'''
        exercise = r'''
static unsigned pixel(unsigned x, unsigned y) {
    unsigned ink=0;
    for(unsigned p=0; p<4; ++p)
        if(bitmap.Planes[p][y*160+x/8] & (128>>(x%8))) ink |= 1<<p;
    return ink;
}
int main(void) {
    const char *expected[9] = {"....62.....", "...6F3.....", "..6F5666662",
        ".6F55555542", "6F5544FFF32", ".3543333321", "..343222221",
        "...321.....", "....21....."};
    const unsigned positions[4][2] = {{88,202},{122,202},{0,0},{309,247}};
    for(unsigned p=0; p<4; ++p) bitmap.Planes[p] = pixels + p*40;
    for(unsigned test=0; test<4; ++test) for(unsigned bg=0; bg<16; ++bg) {
        for(unsigned y=0; y<256; ++y) for(unsigned p=0; p<4; ++p)
            memset(bitmap.Planes[p]+y*160, bg&(1<<p) ? 255 : 0, 40);
        unsigned left=positions[test][0], top=positions[test][1], right=test&1;
        UWORD cursor=0;
        for(unsigned step=1; step<=3; ++step) {
            assert(titleIconStep(left,top,right,&cursor)==(step==3));
            assert(cursor==step*3);
            for(unsigned y=0; y<256; ++y) for(unsigned x=0; x<320; ++x) {
                unsigned want=bg;
                if(y>=top && y<top+cursor && x>=left && x<left+11) {
                    char c=expected[y-top][right ? 10-(x-left) : x-left];
                    if(c!='.') want=c=='F' ? 15 : c-'0';
                }
                assert(pixel(x,y)==want);
            }
        }
        assert(titleIconStep(left,top,right,&cursor) && cursor==9);
    }
}
'''
        panel = function(source, 'panelQueue')
        for command in ('queueText(88, 202, "", 255, 0)',
                        'queueText(105, 203, "OR", 1, 4)',
                        'queueText(122, 202, "", 255, 1)',
                        'queueText(137, 203, "TO CHANGE SECTOR", 1, 4)'):
            self.assertIn(command, panel)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'icons.c').write_text(prelude + function(source, 'titleIconStep') + exercise)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Werror', str(path / 'icons.c'),
                            '-o', str(path / 'icons')], check=True)
            subprocess.run([str(path / 'icons')], check=True)


if __name__ == '__main__':
    unittest.main()
