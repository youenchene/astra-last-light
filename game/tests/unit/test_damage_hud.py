"""Run initial and dirty production HUD paths against source-font pixel oracles."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT, function
from test_presentation_rows import source_fonts, paint_text, reference_hud


class DamageHudTests(unittest.TestCase):
    def test_both_buffers_initial_and_dirty_levels(self):
        source = (ROOT / 'game/src/render_world.c').read_text()
        declarations = source[source.index('static UBYTE s_ubLevel'):source.index('/* All display writes')]
        font = source_fonts()[1]
        prelude = r'''
#include <stdint.h>
#include <string.h>
#include "logic.h"
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
typedef struct { UBYTE pixels[256][320]; } tBitMap;
typedef struct { UWORD pPalette[32]; } tVPort;
#define STAR_COUNT 48
#define MINTERM_COOKIE 0
static tBitMap buffers[2], *s_pScreen, *s_pLabels;
static tVPort viewport, *s_pVPort = &viewport;
static UBYTE s_buffer;
static void starsReset(void) {}
static void panelQueue(tPhase phase) {(void)phase;}
static void scoreDraw(ULONG n, UBYTE dirty) {(void)n;(void)dirty;}
static void blitRect(tBitMap *b,UWORD x,UWORD y,UWORD w,UWORD h,UBYTE c) {
    for(unsigned yy=y; yy<y+h; ++yy) memset(&b->pixels[yy][x],c,w);
}
static void blitCopy(tBitMap *a,int x,int y,tBitMap *b,int xx,int yy,int w,int h,int m) {}
static void blitCopyAligned(tBitMap *a,int x,int y,tBitMap *b,int xx,int yy,int w,int h) {}
'''
        painter = 'static const UBYTE font[36][7] = {' + ','.join(
            '{' + ','.join(map(str, rows)) + '}' for rows in font) + '};\n' + r'''
static void textDraw(UWORD x,UWORD y,const char *text,UBYTE scale,UBYTE ink) {
    const char *alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    for(unsigned i=0;text[i];++i) {
        const char *letter=strchr(alphabet,text[i]);
        if(!letter) continue;
        for(unsigned row=0;row<7;++row) for(unsigned col=0;col<5;++col)
            if(font[letter-alphabet][row] & (16>>col)) s_pScreen->pixels[y+row][x+i*6+col]=ink;
    }
}
static void numberText(char *text,ULONG value,UBYTE digits) {
    text[digits]=0;
    while(digits) {text[--digits]='0'+value%10; value/=10;}
}
'''
        functions = '\n'.join(function(source, name) for name in (
            'queueText', 'queueRect', 'queueCentered', 'queueNumber', 'numberDraw',
            'renderWorldBegin', 'hudDraw'))
        wrapper = r'''
void draw(unsigned buffer,unsigned level,unsigned initial,UBYTE *pixels) {
    s_buffer=buffer; s_pScreen=&buffers[buffer];
    memcpy(s_pScreen->pixels,pixels,256*320);
    tGameState state={0}; state.phase=PLAY; state.weaponLevel=level; state.speedLevel=2;
    if(initial) {
        renderWorldBegin(&state);
        for(unsigned i=0;i<s_commandCount;++i) {
            tWorldCommand *cmd=&s_commands[i];
            if(cmd->scale) textDraw(cmd->x,cmd->y,cmd->text,cmd->scale,cmd->color);
        }
    } else hudDraw(&state,0);
    memcpy(pixels,s_pScreen->pixels,256*320);
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'hud.c').write_text(prelude + declarations + painter + functions + wrapper)
            subprocess.run(['cc', '-std=c11', '-shared', '-fPIC', '-I', str(ROOT/'game/src'),
                            str(path/'hud.c'), str(ROOT/'game/src/logic.c'), '-o', str(path/'hud.so')], check=True)
            lib = ctypes.CDLL(str(path/'hud.so'))
            memory = [(ctypes.c_ubyte * (256*320))() for _ in range(2)]
            for initial_level in range(3):
                for step, level in enumerate((initial_level, 2, 1, 0, 2)):
                    for buffer in range(2):
                        if step == 0:
                            image = reference_hud(0)
                            memory[buffer][:] = [p for row in image for p in row]
                        lib.draw(buffer, level, step == 0, memory[buffer])
                        expected = reference_hud(0)
                        paint_text(expected, str(level), 50, 249, 6, font, 5)
                        paint_text(expected, '2', 98, 249, 6, font, 5)
                        for y in range(249,256):
                            self.assertEqual(list(memory[buffer][y*320+8:y*320+104]), expected[y][8:104],
                                             (initial_level, step, level, buffer, y))
                            self.assertEqual(expected[y][43:50], [0]*7)


if __name__ == '__main__':
    unittest.main()
