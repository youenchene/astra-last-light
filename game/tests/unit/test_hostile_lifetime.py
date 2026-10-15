"""Exhaustive horizontal lifetime oracle, including legacy signed wraps."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_title_composition import ROOT

class HostileLifetimeTests(unittest.TestCase):
    def test_every_signed_x_and_vertical_limit(self):
        code=(ROOT/'game/src/logic.c').read_text()+r'''
#include <assert.h>
static uint16_t reference(const tEntity *e){
    uint16_t life=(uint16_t)(((int32_t)(int16_t)(e->x+HOSTILE_W)*683)>>10)+2;
    if(e->vy){int16_t room=e->vy>0?PLAY_BOTTOM-HOSTILE_H-e->y:e->y-PLAY_TOP;
        if(room<0)room=0;
        uint16_t t=(uint16_t)((e->vy==1||e->vy==-1?room*2:room)+2);
        if(t<life)life=t;}
    return life;
}
int main(void){for(int32_t x=-32768;x<=32767;++x)
    for(int vy=-2;vy<=2;++vy){
        tEntity e={.x=x,.y=40+(uint16_t)x%190,.vy=vy};
        assert(reference(&e)==hostileLife(&e));
    }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'life.c').write_text(code)
            subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined',
                '-I',str(ROOT/'game/src'),str(path/'life.c'),'-o',str(path/'life')],check=True)
            subprocess.run([str(path/'life')],check=True)
