"""Compare optimized scheduling against the original rotating-priority rule."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT


class EnemyScheduleTests(unittest.TestCase):
    def test_exact_schedule_for_formations_and_overlapping_states(self):
        code = (ROOT/'game/src/logic.c').read_text() + r'''
#include <assert.h>
static void reference(tGameState *s) {
    uint8_t assigned=0,start=(uint16_t)s->simFrame%ENEMY_COUNT;
    tEntity *accepted[ENEMY_SPRITE_CAPACITY];
    resetSchedule(s->enemies,ENEMY_COUNT);
    for(uint8_t i=0;i<ENEMY_COUNT;++i) {
        uint8_t index=start+i,fits=1;
        if(index>=ENEMY_COUNT)index-=ENEMY_COUNT;
        tEntity *e=&s->enemies[index];
        if(!e->active||!onScreen(e,ENEMY_H)||assigned==ENEMY_SPRITE_CAPACITY)continue;
        for(uint8_t j=0;j<assigned;++j) {
            const tEntity *o=accepted[j];
            if(e->y<o->y+ENEMY_H+2&&e->y+ENEMY_H+2>o->y){fits=0;break;}
        }
        if(fits){e->visible=1;e->channel=4;accepted[assigned++]=e;}
    }
}
static uint32_t seed=17;
static uint32_t randomWord(void){seed=seed*1664525u+1013904223u;return seed;}
int main(void){
    for(unsigned n=0;n<30000;++n){
        tGameState a,b;logicInit(&a);a.simFrame=randomWord();
        a.waves[0].planned=6;
        for(unsigned i=0;i<ENEMY_COUNT;++i){
            tEntity *e=&a.enemies[i];
            e->active=randomWord()%3!=0;e->visible=randomWord()%2;e->channel=randomWord()%8;
            e->x=(int)(randomWord()%370)-25;
            e->y=(int)(randomWord()%210)+20;
            e->waveId=randomWord()%20;e->waveMember=randomWord()%9;
            if(n%2==0){
                e->active=i<6&&(n%7!=i);e->waveId=1;e->waveMember=i;
                e->y=56+i*27+randomWord()%10;
            }
        }
        b=a;reference(&a);scheduleEnemies(&b,0);
        assert(!memcmp(&a,&b,sizeof(a)));
        unsigned separated=updateEnemies(&a,n&1);b=a;
        reference(&a);scheduleEnemies(&b,separated);assert(!memcmp(&a,&b,sizeof(a)));
    }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)
            (path/'schedule.c').write_text(code)
            subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined',
                            '-I',str(ROOT/'game/src'),str(path/'schedule.c'),
                            '-o',str(path/'schedule')],check=True)
            subprocess.run([str(path/'schedule')],check=True)
