"""Full pool-state oracle for every signed-byte velocity and tick parity."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT


class ProjectileMotionTests(unittest.TestCase):
    def test_all_velocities_edges_and_lifetime(self):
        code=(ROOT/'game/src/logic.c').read_text()+r'''
#include <assert.h>
static void reference(tEntity *pool,uint8_t count,uint8_t shots,uint32_t frame){
    for(unsigned i=0;i<count;++i){
        tEntity *e=&pool[i];unsigned width=shots?shotWidth(e):HOSTILE_W,height=shots?shotHeight(e):HOSTILE_H;
        if(!e->active)continue;
        e->x+=shots?e->vx:halfStep(e->vx,frame);e->y+=shots?e->vy:halfStep(e->vy,frame);
        if(!shots&&e->age)--e->age;
        if(e->x>(shots?BOB_MAX_X:WORLD_W-1)||e->x<=-(int)width||e->y<PLAY_TOP||e->y+height>PLAY_BOTTOM)e->active=0;
    }
}
int main(void){
    for(int v=-128;v<=127;++v)for(unsigned f=0;f<4;++f)for(unsigned shots=0;shots<2;++shots){
        tEntity a[32],b[32];memset(a,0xa5,sizeof(a));
        for(unsigned i=0;i<32;++i){
            a[i].active=i%7!=0;a[i].kind=i&1;a[i].vx=v;a[i].vy=(int8_t)(i*7+v);
            a[i].x=i%2?300+i:-10+(int)i;a[i].y=40+i*6;a[i].age=i%3?i:0;
        }
        memcpy(b,a,sizeof(a));reference(a,32,shots,f);moveProjectiles(b,32,shots,f);
        assert(!memcmp(a,b,sizeof(a)));
    }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'motion.c').write_text(code)
            subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined',
                            '-I',str(ROOT/'game/src'),str(path/'motion.c'),'-o',str(path/'motion')],check=True)
            subprocess.run([str(path/'motion')],check=True)
