"""Full state equivalence against the original shot/enemy collision loop."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT


class ShotCollisionTests(unittest.TestCase):
    def test_order_damage_rewards_and_boss_death_are_unchanged(self):
        code=(ROOT/'game/src/logic.c').read_text()+r'''
#include <assert.h>
static void reference(tGameState *s){
    for(unsigned i=0;i<SHOT_COUNT;++i){
        tEntity *shot=&s->shots[i];
        if(!shot->active||!shot->visible||!onScreen(shot,shotHeight(shot)))continue;
        if(s->phase==BOSS&&s->boss.active&&s->boss.visible&&
           overlap(shot->x,shot->y,shotWidth(shot),shotHeight(shot),s->boss.x,s->boss.y,BOSS_W,BOSS_H)){
            shot->active=0;
            if(shot->hp){s->boss.hp=s->boss.hp>shot->hp?s->boss.hp-shot->hp:0;
                s->boss.flashTicks=BOSS_FLASH_FRAMES;if(!s->boss.hp){killBoss(s);return;}}
            continue;
        }
        if(s->phase==BOSS)continue;
        for(unsigned j=0;j<ENEMY_COUNT;++j){
            tEntity *e=&s->enemies[j];
            if(!e->active||!e->visible||!onScreen(e,ENEMY_H)||
               !overlap(shot->x,shot->y,shotWidth(shot),shotHeight(shot),e->x,e->y,ENEMY_W,ENEMY_H))continue;
            shot->active=0;
            if(e->hp<=shot->hp){retireEnemy(s,e,1);addScore(s,(uint16_t)(100+e->kind*50));s->events|=EVENT_EXPLOSION;}
            else e->hp-=shot->hp;
            break;
        }
    }
}
static uint32_t seed=66;
static uint32_t randomWord(void){seed=seed*1664525u+1013904223u;return seed;}
int main(void){
    for(unsigned n=0;n<30000;++n){
        tGameState a,b;logicInit(&a);a.phase=n%4?PLAY:BOSS;a.score=randomWord();
        a.boss=(tBoss){.active=1,.visible=1,.x=200,.y=104,.hp=1+n%20};
        a.waves[0]=(tWaveTrack){.planned=6,.spawned=6,.remaining=6};
        for(unsigned i=0;i<ENEMY_COUNT+SHOT_COUNT;++i){
            tEntity *e=i<ENEMY_COUNT?&a.enemies[i]:&a.shots[i-ENEMY_COUNT];
            e->active=randomWord()%3!=0;e->visible=randomWord()%2;e->hp=randomWord()%7;
            e->x=(int)(randomWord()%350)-10;e->y=40+randomWord()%185;
            e->kind=i<ENEMY_COUNT?randomWord()%6:randomWord()%2;
            if(n%3==0){e->x=200+i%5;e->y=104+i%7;e->visible=e->active=1;}
            if(i<6)e->waveId=1;
        }
        b=a;reference(&a);collideShots(&b);assert(!memcmp(&a,&b,sizeof(a)));
    }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'collision.c').write_text(code)
            subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined',
                            '-I',str(ROOT/'game/src'),str(path/'collision.c'),
                            '-o',str(path/'collision')],check=True)
            subprocess.run([str(path/'collision')],check=True)
