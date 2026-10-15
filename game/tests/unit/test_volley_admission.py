"""Exact pool-state oracle for shared per-volley trajectory admission."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT


class VolleyAdmissionTests(unittest.TestCase):
    def test_random_volleys_match_original_pool_scans(self):
        code=(ROOT/'game/src/logic.c').read_text()+r'''
#include <assert.h>
static uint8_t referenceAdmission(tGameState *s,tEntity *e){
    uint8_t fits=logicHostileChannelMask(s),best=BULLET_SPRITE_CAPACITY;
    uint8_t counts[4]={0};
    int16_t y=e->y;int8_t vy=e->vy;uint16_t age=hostileLife(e);
    e->age=age;e->channel=0;
    for(unsigned i=0;i<HOSTILE_COUNT;++i){
        tEntity *o=&s->hostile[i];
        if(!o->active||o->channel<4||o->channel>7)continue;
        unsigned channel=o->channel-4;uint8_t bit=1u<<o->channel;++counts[channel];
        if(!(fits&bit))continue;
        if(!o->age)o->age=hostileLife(o);
        if(!staysApart(o,y,vy,age)){fits&=~bit;if(!fits)break;}
    }
    for(unsigned ch=0;ch<4;++ch)if((fits&(16u<<ch))&&counts[ch]<best){
        e->channel=ch+4;best=counts[ch];
    }
    if(!e->channel){e->active=0;e->visible=0;return 0;}return 1;
}
static void referenceFan(tGameState *s,int16_t x,int16_t y,uint8_t rays,int8_t aim){
    int radius=rays/2;
    for(int ray=-radius;ray<=radius;++ray){
        int16_t ry=y+ray*FAN_SPACING,rx=x+(ray<0?-ray:ray)*FAN_STAGGER;
        if(ry<PLAY_TOP||ry+HOSTILE_H>PLAY_BOTTOM)continue;
        tEntity *e=spawn(s->hostile,HOSTILE_COUNT,rx,ry,s->level,1,HOSTILE_VX,
                        (int8_t)clamp(aim+ray,-2,2));
        if(e)referenceAdmission(s,e);
    }
}
static uint32_t seed=751;
static uint32_t randomWord(void){seed=seed*1664525u+1013904223u;return seed;}
int main(void){
    for(unsigned n=0;n<30000;++n){
        tGameState a,b;logicInit(&a);a.level=n%4;a.phase=n%3?PLAY:BOSS;
        for(unsigned i=0;i<HOSTILE_COUNT;++i){
            tEntity *e=&a.hostile[i];
            e->active=randomWord()%3!=0;e->visible=randomWord()%2;
            e->channel=4+randomWord()%4;e->age=randomWord()%250;
            e->x=randomWord()%310;e->y=PLAY_TOP+randomWord()%150;
            e->vy=(int)(randomWord()%5)-2;
        }
        b=a;
        int16_t x=40+randomWord()%240,y=PLAY_TOP+randomWord()%150;
        uint8_t rays=3+2*(randomWord()%4);int8_t aim=(int)(randomWord()%3)-1;
        referenceFan(&a,x,y,rays,aim);fireFan(&b,x,y,rays,aim);
        assert(!memcmp(&a,&b,sizeof(a)));
    }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'volley.c').write_text(code)
            subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined',
                            '-I',str(ROOT/'game/src'),str(path/'volley.c'),
                            '-o',str(path/'volley')],check=True)
            subprocess.run([str(path/'volley')],check=True)
