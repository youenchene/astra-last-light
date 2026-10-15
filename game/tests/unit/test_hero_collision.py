"""Exact hero collision ordering, screen bounds, damage and death cleanup."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_title_composition import ROOT

class HeroCollisionTests(unittest.TestCase):
    def test_full_state_matches_original_checks(self):
        code=(ROOT/'game/src/logic.c').read_text()+r'''
#include <assert.h>
static void reference(tGameState *s){
    if(s->invulnerable)return;
    if(s->phase==BOSS&&s->boss.active&&s->boss.visible&&
       overlap(s->x+PLAYER_HIT_X,s->y+PLAYER_HIT_Y,PLAYER_HIT_W,PLAYER_HIT_H,
       s->boss.x,s->boss.y,BOSS_W,BOSS_H)){hurtHero(s);return;}
    for(unsigned i=0;i<HOSTILE_COUNT;++i){tEntity *e=&s->hostile[i];
        if(!e->active||!e->visible||!onScreen(e,HOSTILE_H))continue;
        if(overlap(s->x+PLAYER_HIT_X,s->y+PLAYER_HIT_Y,PLAYER_HIT_W,PLAYER_HIT_H,
          e->x,e->y,HOSTILE_W,HOSTILE_H)){hurtHero(s);return;}}
    if(s->phase==BOSS)return;
    for(unsigned i=0;i<ENEMY_COUNT;++i){tEntity *e=&s->enemies[i];
        if(e->active&&e->visible&&onScreen(e,ENEMY_H)&&
          overlap(s->x+PLAYER_HIT_X,s->y+PLAYER_HIT_Y,PLAYER_HIT_W,PLAYER_HIT_H,
          e->x,e->y,ENEMY_W,ENEMY_H)){hurtHero(s);return;}}
}
static uint32_t seed=327;
static uint32_t randomWord(void){seed=seed*1664525u+1013904223u;return seed;}
int main(void){for(unsigned n=0;n<30000;++n){
    tGameState a,b;logicInit(&a);a.phase=n%3?PLAY:BOSS;
    a.x=randomWord()%289;a.y=40+randomWord()%170;a.shield=n%3;a.invulnerable=n%7==0;
    a.boss=(tBoss){.active=1,.visible=1,.x=200,.y=104,.hp=20};
    for(unsigned i=0;i<ENEMY_COUNT+HOSTILE_COUNT;++i){
        tEntity *e=i<ENEMY_COUNT?&a.enemies[i]:&a.hostile[i-ENEMY_COUNT];
        e->active=randomWord()%3!=0;e->visible=randomWord()%2;
        e->x=(int)(randomWord()%350)-15;e->y=40+randomWord()%190;
        if(n%3==0){e->x=a.x+12+i%3;e->y=a.y+8+i%5;}}
    b=a;reference(&a);collideHero(&b);assert(!memcmp(&a,&b,sizeof(a)));
}}
'''
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'hero.c').write_text(code)
            subprocess.run(['cc','-std=c11','-O1','-fsanitize=address,undefined',
                '-I',str(ROOT/'game/src'),str(path/'hero.c'),'-o',str(path/'hero')],check=True)
            subprocess.run([str(path/'hero')],check=True)
