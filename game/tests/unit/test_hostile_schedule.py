"""Phase ownership range checks must match the original channel bit masks."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_title_composition import ROOT, function

class HostileScheduleTests(unittest.TestCase):
    def test_all_phases_channels_and_edge_bounds(self):
        source=(ROOT/'game/src/logic.c').read_text()
        gather=function((ROOT/'game/src/render_bullets.c').read_text(),'gatherChannels')
        code=source+r'''
#include <assert.h>
typedef uint8_t UBYTE;typedef uint32_t ULONG;
#define BULLET_FIRST_CHANNEL 4
static void reference(tGameState *s){
    uint8_t mask=logicHostileChannelMask(s);
    for(unsigned i=0;i<HOSTILE_COUNT;++i){tEntity *e=&s->hostile[i];
        if(!e->active){e->visible=0;e->channel=0;continue;}
        if((e->channel<4||e->channel>7||!(mask&(1u<<e->channel)))&&!admitHostile(s,e))continue;
        e->visible=onScreen(e,HOSTILE_H);
    }
    for(unsigned i=0;i<SHOT_COUNT;++i){tEntity *e=&s->shots[i];e->channel=0;
        e->visible=e->active&&e->x<=BOB_MAX_X&&onScreen(e,shotHeight(e));}
}
static uint32_t seed=475;
static uint32_t randomWord(void){seed=seed*1664525u+1013904223u;return seed;}
'''+gather+r'''
int main(void){for(unsigned n=0;n<12000;++n){
    tGameState a,b;logicInit(&a);a.phase=n%10;a.resumePhase=n%2?PLAY:BOSS;
    for(unsigned i=0;i<HOSTILE_COUNT+SHOT_COUNT;++i){
        tEntity *e=i<HOSTILE_COUNT?&a.hostile[i]:&a.shots[i-HOSTILE_COUNT];
        e->active=randomWord()%3!=0;e->visible=randomWord()%2;e->channel=randomWord()%12;
        e->x=(int)(randomWord()%350)-15;e->y=40+randomWord()%190;
        e->vy=(int)(randomWord()%5)-2;e->age=randomWord()%220;e->kind=i%2;
    }
    b=a;reference(&a);scheduleBullets(&b);assert(!memcmp(&a,&b,sizeof(a)));
    ULONG expect[4]={0},actual[4]={0};UBYTE mask=logicHostileChannelMask(&a),show=logicCombatActive(&a);
    for(unsigned i=0;i<HOSTILE_COUNT;++i){tEntity *e=&a.hostile[i];e->visible=0;
        if(!show||!e->active||e->x<=-6||e->x>=320||e->y<56||e->y>208)continue;
        if(e->channel<4||e->channel>7||!(mask&(1u<<e->channel)))continue;
        expect[e->channel-4]|=1u<<i;
    }
    gatherChannels(b.hostile,mask,show,actual);
    assert(!memcmp(&a,&b,sizeof(a))&&!memcmp(expect,actual,sizeof(expect)));
}}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'schedule.c').write_text(code)
            subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined',
                '-I',str(ROOT/'game/src'),str(path/'schedule.c'),'-o',str(path/'schedule')],check=True)
            subprocess.run([str(path/'schedule')],check=True)
