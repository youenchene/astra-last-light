"""Actual scene closure must finish patch work before foreground publication work."""
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]


def function(source,name):
    match=re.search(r'^void '+name+r'\([^;{}]*\)\s*\{',source,re.M)
    end=source.index('{',match.start())+1;depth=1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[match.start():end]


class GalaxyCloseTests(unittest.TestCase):
    def test_both_bitmap_repairs_and_foreground_are_separate_steps(self):
        source=(ROOT/'game/src/render_scenes.c').read_text()
        prelude=r'''
#include <assert.h>
typedef unsigned char UBYTE;
#define SCENE_X 136
#define SCENE_Y 56
#define SCENE_W 176
#define SCENE_H 152
static struct {unsigned short row;UBYTE ready;} s_history[2];
static UBYTE s_buffer;
#define s_row s_history[s_buffer].row
#define s_ready s_history[s_buffer].ready
static unsigned calls[2], frameCalls;
static UBYTE renderWorldRestoreCorridor(unsigned x,unsigned y,unsigned w,unsigned h) {
    assert(x==SCENE_X && w==SCENE_W && h==8);
    assert(y==SCENE_Y+(calls[s_buffer]/2)*8);
    ++frameCalls;
    return ++calls[s_buffer]%2==0;
}
'''
        body=r'''
int main(void) {
    renderScenesClose();
    for(unsigned step=0;step<=SCENE_H/8*2;++step) for(s_buffer=0;s_buffer<2;++s_buffer) {
        frameCalls=0;renderScenesEraseStep();
        assert(s_ready==(step==SCENE_H/8*2));
        if(s_ready) assert(frameCalls==0); /* This frame can draw foreground. */
        else assert(frameCalls==1);
    }
    assert(calls[0]==SCENE_H/8*2 && calls[1]==SCENE_H/8*2);
    for(s_buffer=0;s_buffer<2;++s_buffer) {
        frameCalls=0;renderScenesEraseStep();assert(frameCalls==0);
    }
    renderScenesClose();
    assert(!s_history[0].ready && !s_history[1].ready);
    assert(!s_history[0].row && !s_history[1].row);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'close.c';exe=Path(temp)/'close'
            path.write_text(prelude+function(source,'renderScenesClose')+function(source,'renderScenesEraseStep')+body)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-I',str(ROOT/'game/src'),str(path),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
