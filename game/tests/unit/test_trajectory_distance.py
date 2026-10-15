"""Keep analytic admission exact, including signed-byte velocities and wraps."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT


class TrajectoryDistanceTests(unittest.TestCase):
    def test_endpoint_equivalence(self):
        code=(ROOT/'game/src/logic.c').read_text()+r'''
#include <assert.h>
static unsigned reference(const tEntity *o,int16_t y,int8_t vy,uint16_t age){
    int16_t apart=HOSTILE_H+HOSTILE_GAP,dy=(int16_t)(y-o->y);int8_t ov=o->vy;
    if(dy>=0){if(dy<apart)return 0;if(vy>=ov)return 1;}
    else{if(dy>-apart)return 0;if(vy<=ov)return 1;}
    int16_t t=(int16_t)(o->age<age?o->age:age);
    int16_t d1=(int16_t)(dy*2+(int16_t)(vy-ov)*t);
    return dy>=0?d1>=2*apart:d1<=-2*apart;
}
static uint32_t seed=211;
static uint32_t randomWord(void){seed=seed*1664525u+1013904223u;return seed;}
int main(void){
    for(unsigned n=0;n<200000;++n){
        tEntity o={0};o.y=randomWord();o.vy=randomWord();o.age=randomWord();
        int16_t y=randomWord();int8_t vy=randomWord();uint16_t age=randomWord();
        assert(reference(&o,y,vy,age)==staysApart(&o,y,vy,age));
    }
    for(int a=-2;a<=2;++a)for(int b=-2;b<=2;++b)
        for(int dy=-152;dy<=152;++dy)for(unsigned age=0;age<220;age+=3){
            tEntity o={.y=100,.vy=a,.age=age};
            assert(reference(&o,100+dy,b,age)==staysApart(&o,100+dy,b,age));
        }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'distance.c').write_text(code)
            subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined',
                            '-I',str(ROOT/'game/src'),str(path/'distance.c'),'-o',str(path/'distance')],check=True)
            subprocess.run([str(path/'distance')],check=True)
