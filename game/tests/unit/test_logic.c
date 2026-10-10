#include "../../src/logic.h"
#include "../../src/hero_presentation.h"
#include <stdio.h>
#include <string.h>

static int failures;
#define CHECK(expr) do { if(!(expr)) { \
	fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #expr); ++failures; \
} } while(0)
static const tInput idle = {0, 0, 0};
static const tInput fire = {0, 0, 1};

static void finishScene(tGameState *s) {
	logicScenePresented(s, s->sceneEpoch);
	for(unsigned tick = 0; tick < SCENE_FRAMES; ++tick) logicUpdate(s, &idle);
}
static void finishDeath(tGameState *s) {
	unsigned ticks = s->phase == HERO_DYING ? HERO_DEATH_FRAMES : BOSS_DEATH_FRAMES;
	for(unsigned tick = 0; tick < ticks; ++tick) logicUpdate(s, &idle);
}
static void returnToTitle(tGameState *s) {
	logicSetPresentationBusy(s, 0);
	for(unsigned tick = 0; tick < GAMEOVER_FRAMES; ++tick) logicUpdate(s, &idle);
	CHECK(s->phase == TITLE && s->titleInputBlocked);
	logicSetPresentationBusy(s, 0);
	logicUpdate(s, &idle);
}
static void start(tGameState *s) {
	logicInit(s); logicUpdate(s, &fire); finishScene(s); logicUpdate(s, &idle);
}
static void waitBossIntro(tGameState *s) {
	for(unsigned tick = 0; tick < 500 && s->phase == PLAY; ++tick)
		logicUpdate(s, &idle);
	CHECK(s->phase == BOSS_INTRO);
}
static void arriveBoss(tGameState *s) {
	waitBossIntro(s);
	finishScene(s);
}
static unsigned hostileCount(const tGameState *s);
static tEntity entity(int16_t x, int16_t y, uint8_t hp) {
	tEntity e;
	memset(&e, 0, sizeof(e));
	e.x = x; e.y = y; e.hp = hp; e.active = 1; e.visible = 1;
	e.fireCountdown = 50;
	return e;
}
static void testLongerBossFights(void) {
	const unsigned hp[LEVEL_COUNT] = {216, 336, 432, 480};
	const unsigned lanceHits[LEVEL_COUNT] = {36, 56, 72, 80};
	for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
		tGameState s;
		start(&s);
		s.level = level;
		s.wave = g_stageWaveQuota[level];
		arriveBoss(&s);
		CHECK(s.phase == BOSS && s.boss.hp == hp[level] && s.boss.maxHp == hp[level]);
		logicUpdate(&s, &idle); /* Put the boss on its first movement phase. */
		unsigned hits = 0;
		while(s.phase == BOSS && hits < lanceHits[level]) {
			s.invulnerable = 2;
			s.shots[0] = entity(s.boss.x + 4, s.boss.y + 4, 6);
			s.shots[0].kind = SHOT_CHARGED;
			logicUpdate(&s, &idle);
			++hits;
			CHECK(s.boss.hp == hp[level] - hits * 6);
		}
		CHECK(hits == lanceHits[level] && s.phase == BOSS_DYING);
		CHECK(s.score == 2000 + level * 1000);
	}
}

static void testInitAndBounds(void) {
	tGameState s;
	tInput input = {-127, -127, 0};
	logicInit(&s);
	CHECK(s.phase == TITLE && s.level == 0 && s.lives == 3);
	CHECK(s.frame == 0 && s.score == 0 && !s.enemies[0].active);
	CHECK(logicUpdate(&s, &idle) == 0);
	logicUpdate(&s, &fire);
	CHECK(s.phase == SECTOR_INTRO && (s.events & EVENT_LEVEL));
	finishScene(&s);
	CHECK(s.x == 32 && s.y == 126);
	s.x = 1; s.y = PLAY_TOP + 1;
	logicUpdate(&s, &input);
	CHECK(s.x == 0 && s.y == PLAY_TOP);
	input.dx = 127; input.dy = 127;
	s.x = WORLD_W - PLAYER_W - 1; s.y = PLAY_BOTTOM - PLAYER_H - 1;
	logicUpdate(&s, &input);
	CHECK(s.x == WORLD_W - PLAYER_W && s.y == PLAY_BOTTOM - PLAYER_H);
	CHECK(logicUpdate(NULL, &idle) == 0);
	CHECK(logicUpdate(&s, NULL) == 1);
}
static void testHoldAndCharge(void) {
	tGameState s;
	unsigned i, shots = 0;
	start(&s);
	for(i = 0; i < CHARGE_FRAMES; ++i) {
		logicUpdate(&s, &fire);
		if(s.events & EVENT_SHOT) ++shots;
	}
	CHECK(shots == 0 && s.charge == CHARGE_FRAMES);
	CHECK(s.events & EVENT_CHARGE);
	for(i = 0; i < 10; ++i) {
		logicUpdate(&s, &fire);
		CHECK(s.charge == CHARGE_FRAMES && !(s.events & (EVENT_SHOT | EVENT_CHARGE)));
	}
	logicUpdate(&s, &idle);
	CHECK((s.events & EVENT_SHOT) && (s.events & EVENT_LANCE) && s.charge == 0);
	for(i = 0; i < SHOT_COUNT; ++i)
		if(s.shots[i].active && s.shots[i].kind == SHOT_CHARGED) break;
	CHECK(i < SHOT_COUNT);
	logicUpdate(&s, &idle);
	CHECK(!(s.events & (EVENT_SHOT | EVENT_LANCE)));
	start(&s);
	for(i = 0; i < SHOT_COUNT; ++i) s.shots[i] = entity(100, 60 + (int16_t)i * 12, 1);
	logicUpdate(&s, &fire);
	CHECK(!(s.events & EVENT_SHOT));
	s.charge = CHARGE_FRAMES;
	logicUpdate(&s, &idle);
	CHECK(!(s.events & (EVENT_SHOT | EVENT_LANCE)) && s.charge == 0);
}
static void testHitsAndDeath(void) {
	tGameState s;
	start(&s);
	s.enemies[0] = entity(100, 90, 1);
	s.shots[0] = entity(96, 94, 1);
	logicUpdate(&s, &idle);
	CHECK(!s.enemies[0].active && !s.shots[0].active);
	CHECK(s.score == 100 && (s.events & EVENT_EXPLOSION));
	s.invulnerable = 0;
	s.hostile[0] = entity(s.x + PLAYER_HIT_X, s.y + PLAYER_HIT_Y, 1);
	s.hostile[1] = s.hostile[0];
	logicUpdate(&s, &idle);
	CHECK(s.lives == 2 && s.phase == HERO_DYING);
	CHECK(s.events & EVENT_HIT);
	finishDeath(&s);
	CHECK(s.invulnerable == RESPAWN_FRAMES);
	s.hostile[0] = entity(s.x, s.y, 1);
	logicUpdate(&s, &idle);
	CHECK(s.lives == 2);
	s.invulnerable = 0; s.lives = 1;
	s.enemies[0] = entity(s.x, s.y, 1);
	logicUpdate(&s, &fire);
	CHECK(s.phase == HERO_DYING && s.lives == 0);
	for(unsigned tick = 0; tick < HERO_DEATH_FRAMES; ++tick) logicUpdate(&s, &fire);
	CHECK(s.phase == GAMEOVER && s.lives == 0);
	logicUpdate(&s, &fire);
	CHECK(s.phase == GAMEOVER);
	returnToTitle(&s); logicUpdate(&s, &fire);
	CHECK(s.phase == SECTOR_INTRO && s.lives == 3 && s.score == 0 && s.level == 0);
}
static void testCollisionEdgesAndDrops(void) {
	tGameState s;
	start(&s); s.invulnerable = 0;
	s.hostile[0] = entity(s.x + PLAYER_W, s.y, 1);
	logicUpdate(&s, &idle);
	CHECK(s.lives == 3);
	s.hostile[0] = entity(s.x, s.y, 1); s.hostile[0].visible = 0;
	logicUpdate(&s, &idle);
	CHECK(s.lives == 3);
	s.enemies[0] = entity(100, 90, 1); s.enemies[0].visible = 0;
	s.shots[0] = entity(100, 90, 1);
	logicUpdate(&s, &idle);
	CHECK(s.enemies[0].active && s.score == 0);
}
static void checkSchedule(const tGameState *s) {
	unsigned i, j, perChannel[8] = {0};
	for(i = 0; i < BONUS_COUNT; ++i) {
		CHECK(s->pickups[i].channel == 0);
		CHECK(s->pickups[i].visible == (s->pickups[i].active && s->pickups[i].x >= 0 &&
			s->pickups[i].x < WORLD_W && s->pickups[i].y >= PLAY_TOP && s->pickups[i].y + 16 <= PLAY_BOTTOM));
	}
	/* Player shots are BOBs: no sprite channel, drawable up to BOB_MAX_X. */
	for(i = 0; i < SHOT_COUNT; ++i) {
		const tEntity *e = &s->shots[i];
		int h = e->kind == SHOT_CHARGED ? CHARGED_SHOT_H : SHOT_H;
		CHECK(e->channel == 0);
		CHECK(e->visible == (e->active && e->x >= 0 && e->x <= BOB_MAX_X &&
			e->y >= PLAY_TOP && e->y + h <= PLAY_BOTTOM));
	}
	for(i = 0; i < ENEMY_COUNT; ++i) {
		const tEntity *e = &s->enemies[i];
		if(!e->active) CHECK(!e->visible);
		if(!e->visible) { CHECK(!e->channel); continue; }
		CHECK(e->channel == 4 && ++perChannel[4] <= ENEMY_SPRITE_CAPACITY);
		CHECK(e->x >= 0 && e->x < WORLD_W && e->y >= PLAY_TOP && e->y + ENEMY_H <= PLAY_BOTTOM);
		for(j = i + 1; j < ENEMY_COUNT; ++j) if(s->enemies[j].visible)
			CHECK(e->y + ENEMY_H + 2 <= s->enemies[j].y || s->enemies[j].y + ENEMY_H + 2 <= e->y);
	}
	/* Every thrown on-screen hostile bullet is shown, on its own channel. */
	for(i = 0; i < HOSTILE_COUNT; ++i) {
		const tEntity *e = &s->hostile[i];
		if(!e->active) { CHECK(!e->visible && !e->channel); continue; }
		CHECK(e->channel >= 4 && e->channel <= 7);
		CHECK(logicHostileChannelMask(s) & (1u << e->channel));
		CHECK(e->visible == (e->x >= 0 && e->x < WORLD_W &&
			e->y >= PLAY_TOP && e->y + HOSTILE_H <= PLAY_BOTTOM));
		CHECK(++perChannel[e->channel] <= BULLET_SPRITE_CAPACITY);
		for(j = i + 1; j < HOSTILE_COUNT; ++j) {
			const tEntity *o = &s->hostile[j];
			if(!o->active || o->channel != e->channel) continue;
			CHECK(e->y + HOSTILE_H + 2 <= o->y || o->y + HOSTILE_H + 2 <= e->y);
		}
	}
}
static void testStagesAndBosses(void) {
	tGameState s;
	unsigned level, tick, i;
	uint32_t score = 0;
	start(&s);
	CHECK(strcmp(g_stageNames[0], "Orbital Graveyard") == 0);
	CHECK(strcmp(g_stageNames[3], "Stellar Citadel") == 0);
	for(level = 0; level < LEVEL_COUNT; ++level) {
		CHECK(s.level == level && s.phase == PLAY);
		CHECK(g_stageFrames[level] >= 1750 && g_stageFrames[level] <= 2500);
		for(tick = 0; s.phase == PLAY && tick < 15000; ++tick) {
			s.invulnerable = 2; logicUpdate(&s, &idle); checkSchedule(&s);
		}
		CHECK(s.phase == BOSS_INTRO && s.wave == g_stageWaveQuota[level]);
		finishScene(&s);
		CHECK(s.stageFrame > g_stageFrames[level]);
		CHECK(s.boss.hp == s.boss.maxHp && s.boss.hp > 0);
		CHECK(s.boss.active && !s.boss.visible && s.boss.kind == level);
		for(tick = 0; tick < 160; ++tick) {
			s.invulnerable = 2; logicUpdate(&s, &idle); checkSchedule(&s);
			CHECK(s.boss.visible);
			for(i = 0; i < ENEMY_COUNT; ++i) CHECK(!s.enemies[i].active);
		}
		const unsigned bossTicks[] = {128, 136, 144, 160};
		CHECK(s.boss.tick == bossTicks[level]);
		s.boss.hp = 1;
		s.shots[0] = entity(s.boss.x, s.boss.y + 8, 1);
		logicUpdate(&s, &idle);
		CHECK(s.phase == BOSS_DYING && s.boss.hp == 0);
		CHECK(s.score > score && (s.events & EVENT_EXPLOSION));
		score = s.score;
		finishDeath(&s); finishScene(&s);
		if(level < LEVEL_COUNT - 1) finishScene(&s);
	}
	CHECK(s.phase == WIN && s.level == 3);
	finishScene(&s);
	logicUpdate(&s, &fire);
	CHECK(s.phase == SECTOR_INTRO && s.level == 0 && s.score == 0);
}
static void testDeterminismAndSaturation(void) {
	struct { uint32_t before; tGameState state; uint32_t after; } guarded;
	tGameState second;
	unsigned i;
	tInput input = {0, 0, 1};
	guarded.before = 0x12345678; guarded.after = 0x87654321;
	start(&guarded.state); start(&second);
	for(i = 0; i < 12000; ++i) {
		input.dx = (i & 64) ? 1 : -1; input.dy = (i & 128) ? 1 : -1;
		input.fire = (i & 63) != 0;
		logicUpdate(&guarded.state, &input); logicUpdate(&second, &input);
		CHECK(memcmp(&guarded.state, &second, sizeof(second)) == 0);
	}
	CHECK(guarded.before == 0x12345678 && guarded.after == 0x87654321);
	start(&second); second.score = UINT32_MAX - 10;
	second.enemies[0] = entity(100, 90, 1); second.shots[0] = entity(100, 90, 1);
	logicUpdate(&second, &idle);
	CHECK(second.score == UINT32_MAX);
	second.frame = UINT32_MAX; logicUpdate(&second, &idle);
	CHECK(second.frame == 0);
	start(&second);
	for(i = 0; i < ENEMY_COUNT; ++i) second.enemies[i] = entity(200, 100, 2);
	logicUpdate(&second, &idle); checkSchedule(&second);
	{ unsigned visible = 0;
		for(i = 0; i < ENEMY_COUNT; ++i) visible += second.enemies[i].visible;
		CHECK(visible == 1);
	}
}
static void testWavesDamageAndExpiry(void) {
	tGameState s;
	unsigned i;
	start(&s); s.waveTimer = 1;
	logicUpdate(&s, &idle);
	CHECK(s.wave == 1);
	for(i = 0; i < FORMATION_SIZE; ++i) {
		CHECK(s.enemies[i].active && s.enemies[i].visible);
		if(i) CHECK(s.enemies[i].y - s.enemies[i - 1].y >= ENEMY_H + 2);
	}
	start(&s);
	s.enemies[0] = entity(100, 90, 3);
	s.enemies[0].kind = ENEMY_GUNNER;
	s.shots[0] = entity(100, 90, 1);
	logicUpdate(&s, &idle);
	CHECK(s.enemies[0].hp == 2 && s.score == 0 && !s.shots[0].active);
	s.shots[0] = entity(100, 90, 6); s.shots[0].kind = SHOT_CHARGED;
	logicUpdate(&s, &idle);
	CHECK(!s.enemies[0].active && s.score == 200);
	s.enemies[0] = entity(-15, 90, 1); s.enemies[0].vx = -2;
	s.shots[0] = entity(319, 90, 1); s.shots[0].vx = 6;
	s.hostile[0] = entity(-14, 90, 1); s.hostile[0].vx = -3;
	logicUpdate(&s, &idle);
	CHECK(!s.enemies[0].active && !s.shots[0].active && !s.hostile[0].active);
	CHECK(s.score == 200);
	s.invulnerable = 1; s.hostile[0] = entity(s.x + PLAYER_HIT_X, s.y + PLAYER_HIT_Y, 1);
	logicUpdate(&s, &idle);
	CHECK(s.lives == 2);
	start(&s); s.waveTimer = 1;
	for(i = 0; i < ENEMY_COUNT; ++i) s.enemies[i] = entity(200, 60 + (int16_t)i * 8, 7);
	logicUpdate(&s, &idle);
	for(i = 0; i < ENEMY_COUNT; ++i) CHECK(s.enemies[i].hp == 7);
}
static void testDistinctBossPatternsAndHostileLimit(void) {
	tGameState s;
	unsigned level, tick, i, count;
	int16_t x[LEVEL_COUNT], y[LEVEL_COUNT];
	const unsigned rays[LEVEL_COUNT] = {5, 7, 7, 9};
	CHECK(strcmp(g_stageNames[1], "Veil Nebula") == 0);
	CHECK(strcmp(g_stageNames[2], "Imperial Foundry") == 0);
	for(level = 0; level < LEVEL_COUNT; ++level) {
		start(&s); s.level = (uint8_t)level; s.wave = g_stageWaveQuota[level];
		arriveBoss(&s);
		for(tick = 0; tick < 50; ++tick) logicUpdate(&s, &idle);
		x[level] = s.boss.x; y[level] = s.boss.y;
		count = 0;
		for(i = 0; i < HOSTILE_COUNT; ++i) if(s.hostile[i].active) ++count;
		CHECK(count >= 3 && count <= rays[level]);
		checkSchedule(&s);
		/* A full pool refuses new rays without disturbing live bullets. */
		for(i = 0; i < HOSTILE_COUNT; ++i) {
			s.hostile[i] = entity(200, PLAY_TOP + (int16_t)(i / 2) * 9, 7);
			s.hostile[i].channel = 6 + (i & 1);
		}
		s.boss.cooldown = 1;
		logicUpdate(&s, &idle);
		for(i = 0; i < HOSTILE_COUNT; ++i) CHECK(s.hostile[i].hp == 7);
	}
	for(level = 0; level < LEVEL_COUNT; ++level)
		for(i = level + 1; i < LEVEL_COUNT; ++i) CHECK(x[level] != x[i] || y[level] != y[i]);
}
static void testChargedGeometry(void) {
	tGameState s;
	unsigned kind, edge;
	/* Touching upper/lower edges misses; one pixel inside either edge hits. */
	const int16_t enemyY[] = {84, 85, 109, 110};
	const unsigned hits[] = {0, 1, 1, 0};
	CHECK(CHARGED_SHOT_W == 16 && CHARGED_SHOT_H == 10);
	for(edge = 0; edge < 4; ++edge) {
		start(&s);
		s.shots[0] = entity(100, 100, 6); s.shots[0].kind = SHOT_CHARGED;
		s.enemies[0] = entity(115, enemyY[edge], 3);
		logicUpdate(&s, &idle);
		CHECK(s.enemies[0].active == !hits[edge]);
		CHECK(s.shots[0].active == !hits[edge]);
	}
	start(&s);
	s.shots[0] = entity(100, 100, 6); s.shots[0].kind = SHOT_CHARGED;
	s.enemies[0] = entity(116, 100, 3);
	logicUpdate(&s, &idle);
	CHECK(s.enemies[0].active && s.shots[0].active);
	for(kind = SHOT_NORMAL; kind <= SHOT_CHARGED; ++kind) {
		int h = kind == SHOT_CHARGED ? CHARGED_SHOT_H : SHOT_H;
		int speed = kind == SHOT_CHARGED ? 4 : 6;
		for(edge = 0; edge < 2; ++edge) {
			start(&s); s.y = edge ? PLAY_BOTTOM - PLAYER_H : PLAY_TOP;
			s.charge = kind == SHOT_CHARGED ? CHARGE_FRAMES : 1;
			logicUpdate(&s, &idle);
			CHECK(s.shots[0].active && s.shots[0].visible);
			CHECK(s.shots[0].kind == kind && s.shots[0].vx == speed);
			CHECK(s.shots[0].x == s.x + PLAYER_W + speed);
			CHECK(s.shots[0].y == s.y + (PLAYER_H - h) / 2);
		}
		for(edge = 0; edge < 4; ++edge) {
			start(&s);
			s.shots[0] = entity(100, edge < 2 ? PLAY_TOP - 1 + edge :
				PLAY_BOTTOM - h + edge - 2, 1);
			s.shots[0].kind = (uint8_t)kind;
			logicUpdate(&s, &idle);
			CHECK(s.shots[0].active == (edge == 1 || edge == 2));
			CHECK(s.shots[0].visible == s.shots[0].active);
		}
	}
}

static void testHostileAdmission(void) {
	tGameState s;
	unsigned i;
	/* Two parallel bullets share a channel only HOSTILE_H + HOSTILE_GAP apart. */
	for(unsigned gap = HOSTILE_H + HOSTILE_GAP - 1; gap <= HOSTILE_H + HOSTILE_GAP; ++gap) {
		start(&s); s.waveTimer = 60000;
		s.hostile[0] = entity(200, 100, 1); s.hostile[0].channel = 6;
		s.hostile[1] = entity(200, 100, 1); s.hostile[1].channel = 7;
		s.hostile[2] = entity(260, (int16_t)(100 + gap), 1);
		logicUpdate(&s, &idle);
		CHECK(s.hostile[2].active == (gap == HOSTILE_H + HOSTILE_GAP));
		CHECK(s.hostile[2].visible == s.hostile[2].active);
		checkSchedule(&s);
	}
	/* A converging path is refused even when the rows are clear right now. */
	start(&s); s.waveTimer = 60000;
	s.hostile[0] = entity(200, 100, 1); s.hostile[0].channel = 6;
	s.hostile[1] = entity(200, 100, 1); s.hostile[1].channel = 7;
	s.hostile[2] = entity(200, 160, 1); s.hostile[2].vy = -2;
	logicUpdate(&s, &idle);
	CHECK(!s.hostile[2].active && !s.hostile[2].visible);
	/* A diverging path below them is admitted. */
	s.hostile[2] = entity(200, 120, 1); s.hostile[2].vy = 2;
	logicUpdate(&s, &idle);
	CHECK(s.hostile[2].active && s.hostile[2].visible);
	checkSchedule(&s);
	/* Crossing-free paths stay apart until both leave the corridor. */
	start(&s); s.waveTimer = 60000;
	s.hostile[0] = entity(300, 100, 1); s.hostile[0].vx = HOSTILE_VX; s.hostile[0].vy = -1;
	s.hostile[1] = entity(300, 120, 1); s.hostile[1].vx = HOSTILE_VX; s.hostile[1].vy = 1;
	s.hostile[0].visible = s.hostile[1].visible = 0;
	logicUpdate(&s, &idle);
	CHECK(s.hostile[0].channel == 6 && s.hostile[1].channel == 7);
	for(i = 0; i < 260; ++i) { s.invulnerable = 2; logicUpdate(&s, &idle); checkSchedule(&s); }
	CHECK(!hostileCount(&s));
	/* The remaining-life bound never runs out before the bullet leaves. */
	for(int vy = -2; vy <= 2; ++vy) {
		start(&s); s.waveTimer = 60000; s.x = 0; s.y = PLAY_TOP;
		s.hostile[0] = entity(310, 132, 1); s.hostile[0].vx = HOSTILE_VX;
		s.hostile[0].vy = (int8_t)vy; s.hostile[0].visible = 0;
		logicUpdate(&s, &idle);
		while(s.hostile[0].active) {
			CHECK(s.hostile[0].age > 0);
			s.invulnerable = 2; logicUpdate(&s, &idle);
		}
	}
	/* A renderer-dropped shot still cannot cause damage. */
	start(&s);
	s.shots[0] = entity(100, 100, 6); s.shots[0].kind = SHOT_CHARGED;
	s.shots[0].visible = 0; s.enemies[0] = entity(100, 100, 1);
	logicUpdate(&s, &idle);
	CHECK(s.enemies[0].active && s.score == 0);
	/* An object moving off the left edge cannot hit from its old visibility. */
	start(&s); s.x = 0; s.invulnerable = 0;
	s.enemies[0] = entity(0, s.y, 1); s.enemies[0].vx = -2;
	logicUpdate(&s, &idle);
	CHECK(s.lives == 3 && !s.enemies[0].visible);
}

static void testSchedulingScanlineBoundaries(void) {
	tGameState s;
	/* Exhaust every alignment against two full channel rows. */
	for(int16_t otherY = PLAY_TOP; otherY <= PLAY_BOTTOM - HOSTILE_H; ++otherY) {
		start(&s); s.waveTimer = 60000;
		s.hostile[0] = entity(250, 120, 1); s.hostile[0].channel = 6;
		s.hostile[1] = entity(250, 120, 1); s.hostile[1].channel = 7;
		s.hostile[2] = entity(200, otherY, 1);
		logicUpdate(&s, &idle);
		unsigned fits = otherY >= 120 + HOSTILE_H + HOSTILE_GAP || otherY + HOSTILE_H + HOSTILE_GAP <= 120;
		CHECK(s.hostile[0].visible && s.hostile[0].channel == 6);
		CHECK(s.hostile[1].visible && s.hostile[1].channel == 7);
		CHECK(s.hostile[2].active == fits && s.hostile[2].visible == fits);
		CHECK(s.hostile[2].channel == (fits ? 6 : 0));
	}
}

static void testWaveCadenceAndFormations(void) {
	tGameState s, second;
	const unsigned delay[] = {150, 140, 130, 120};
	const unsigned duration[] = {1800, 2000, 2200, 2400};
	unsigned level, tick, form, i, j, freeSlots;
	for(level = 0; level < LEVEL_COUNT; ++level) {
		logicInit(&s); s.level = (uint8_t)level; logicUpdate(&s, &fire);
		finishScene(&s);
		CHECK(s.waveTimer == 25 && g_stageFrames[level] == duration[level]);
		for(tick = 1; tick < duration[level]; ++tick) {
			unsigned alive = 0, previous = s.wave, timer = s.waveTimer;
			for(i = 0; i < ENEMY_COUNT; ++i) alive += s.enemies[i].active;
			s.invulnerable = 2; logicUpdate(&s, &idle);
			CHECK(s.wave == previous + (!alive && timer <= 1));
			if(s.wave != previous) CHECK(s.waveTimer == delay[level]);
			checkSchedule(&s);
		}
		CHECK(s.wave > 1);
		s.invulnerable = 2; logicUpdate(&s, &idle);
		CHECK(s.phase == PLAY && s.stageFrame == duration[level]);
	}
	for(form = 0; form < 5; ++form) {
		start(&s); s.wave = (uint16_t)form; s.waveTimer = 1;
		second = s;
		logicUpdate(&s, &idle); logicUpdate(&second, &idle);
		CHECK(memcmp(&s, &second, sizeof(s)) == 0);
		for(i = 0; i < ENEMY_COUNT; ++i) {
			CHECK(s.enemies[i].active == (i < FORMATION_SIZE));
			if(!s.enemies[i].active) continue;
			CHECK(s.enemies[i].visible && s.enemies[i].x >= 240);
			CHECK(s.enemies[i].x + ENEMY_W <= WORLD_W);
			for(j = 0; j < i; ++j) {
				int dy = s.enemies[i].y - s.enemies[j].y;
				CHECK(dy >= ENEMY_H + 2 || dy <= -ENEMY_H - 2);
			}
		}
		{
			CHECK(s.waves[0].planned == 6 && s.waves[0].spawned == 6);
			CHECK(s.waves[0].remaining == 6 && !s.waves[0].failed);
			for(i = 0; i < FORMATION_SIZE; ++i) {
				/* Combat tick 2 is the first (odd) enemy motion tick. */
				int dy = form == ENEMY_WEAVER ? 1 : form == ENEMY_DART ? (i < 3 ? 1 : -1) : 0;
				CHECK(s.enemies[i].y == 60 + (int)i * 27 + dy);
				CHECK(s.enemies[i].x == (i % 2 ? 280 : 304) - (form == ENEMY_DART ? 2 : 1));
				CHECK(s.enemies[i].kind == (form == 4 ? ENEMY_ASTEROID : form) && s.enemies[i].waveMember == i);
			}
		}
		checkSchedule(&s);
		for(freeSlots = 0; freeSlots < ENEMY_COUNT; ++freeSlots) {
			start(&s); s.wave = (uint16_t)form; s.waveTimer = 1;
			for(i = freeSlots; i < ENEMY_COUNT; ++i) s.enemies[i] = entity(200, 70, 7);
			logicUpdate(&s, &idle);
			CHECK(s.wave == form && s.waveTimer == 0);
			CHECK(!s.waves[0].planned && !s.waves[0].spawned && !s.waves[0].remaining);
			for(i = 0; i < ENEMY_COUNT; ++i) {
				CHECK(s.enemies[i].active == (i >= freeSlots));
				if(i >= freeSlots) CHECK(s.enemies[i].hp == 7);
			}
		}
	}
}

static void testSectorWaveCycles(void) {
	const unsigned kinds[4][5] = {
		{ENEMY_SCOUT, ENEMY_WEAVER, ENEMY_GUNNER, ENEMY_DART, ENEMY_ASTEROID},
		{ENEMY_WEAVER, ENEMY_DART, ENEMY_WEAVER, ENEMY_GUNNER, ENEMY_ASTEROID},
		{ENEMY_GUNNER, ENEMY_SCOUT, ENEMY_GUNNER, ENEMY_DART, ENEMY_ASTEROID},
		{ENEMY_DART, ENEMY_GUNNER, ENEMY_WEAVER, ENEMY_DART, ENEMY_ASTEROID}
	};
	for(unsigned level = 0; level < LEVEL_COUNT; ++level)
		for(unsigned wave = 0; wave < g_stageWaveQuota[level]; ++wave) {
			tGameState s;
			start(&s); s.level = level; s.wave = wave; s.waveTimer = 1;
			logicUpdate(&s, &idle);
			CHECK(s.wave == wave + 1 && s.waves[0].remaining == 6);
			for(unsigned i = 0; i < ENEMY_COUNT; ++i) {
				CHECK(s.enemies[i].active == (i < 6));
				if(i < 6) CHECK(s.enemies[i].kind == kinds[level][wave % 5]);
			}
			if(wave % 5 == 4) {
				for(unsigned tick = 0; tick < 100; ++tick) {
					logicUpdate(&s, &idle); CHECK(!hostileCount(&s));
				}
			}
			checkSchedule(&s);
		}
}

static void testSectorSelection(void) {
	tGameState s;
	tInput right = {1, 0, 0}, left = {-1, 0, 0};
	logicInit(&s);
	logicUpdate(&s, &left);
	CHECK(s.level == 3);
	logicUpdate(&s, &left);
	CHECK(s.level == 3);
	logicUpdate(&s, &idle);
	logicUpdate(&s, &right);
	CHECK(s.level == 0);
	logicUpdate(&s, &idle);
	logicUpdate(&s, &right);
	logicUpdate(&s, &fire);
	CHECK(s.phase == SECTOR_INTRO && s.level == 1 && s.lives == 3);
}

static void shootMember(tGameState *s, unsigned index) {
	tEntity *e = &s->enemies[index];
	e->x = 200; e->vx = 0; e->kind = ENEMY_SCOUT;
	e->visible = 1;
	s->shots[0] = entity(200, e->y, 6);
	s->waveTimer = 60000; s->invulnerable = 2;
	logicUpdate(s, &idle);
}
static void testWaveRewards(void) {
	tGameState s;
	unsigned i, wave, id;
	for(wave = 0; wave < 5; ++wave) {
		start(&s); s.wave = wave; s.waveTimer = 1; logicUpdate(&s, &idle);
		for(i = 0; i < FORMATION_SIZE; ++i)
			CHECK(s.enemies[i].kind == (wave == 4 ? ENEMY_ASTEROID : wave));
		id = s.enemies[0].waveId;
		for(i = 0; i < FORMATION_SIZE; ++i) {
			shootMember(&s, i);
			CHECK(!!(s.events & EVENT_BONUS_DROP) == (i == FORMATION_SIZE - 1));
			CHECK(s.waves[id - 1].killed == i + 1);
			CHECK(s.waves[id - 1].remaining == FORMATION_SIZE - 1 - i);
		}
		CHECK(s.waves[id - 1].killed == s.waves[id - 1].planned);
		CHECK(s.pickups[0].active && s.pickups[0].kind == BONUS_POWER);
		CHECK(s.bonusCycle == 1);
		logicUpdate(&s, &idle); CHECK(!(s.events & EVENT_BONUS_DROP));
	}
	/* A due wave waits for the last survivor, then safely reuses the tracker. */
	start(&s); s.waveTimer = 1; logicUpdate(&s, &idle); id = s.enemies[0].waveId;
	for(i = 0; i < FORMATION_SIZE - 1; ++i) shootMember(&s, i);
	s.waveTimer = 1; logicUpdate(&s, &idle);
	CHECK(s.wave == 1 && !s.waveTimer && s.waves[id - 1].remaining == 1);
	shootMember(&s, FORMATION_SIZE - 1);
	CHECK(s.events & EVENT_BONUS_DROP);
	s.waveTimer = 0; logicUpdate(&s, &idle);
	CHECK(s.wave == 2 && s.waves[id - 1].remaining == FORMATION_SIZE);
	for(i = 0; i < FORMATION_SIZE; ++i) shootMember(&s, i);
	CHECK(s.events & EVENT_BONUS_DROP);
	CHECK(s.pickups[1].kind == BONUS_FIRE && s.bonusCycle == 2);
	/* Escape permanently disqualifies the otherwise complete wave. */
	start(&s); s.waveTimer = 1; logicUpdate(&s, &idle);
	s.enemies[0].x = -16; logicUpdate(&s, &idle);
	for(i = 1; i < FORMATION_SIZE; ++i) shootMember(&s, i);
	CHECK(s.waves[0].failed && s.waves[0].killed == 5 && !s.waves[0].remaining);
	CHECK(!(s.events & EVENT_BONUS_DROP) && s.bonusCycle == 0);
	/* Inject partial trackers: the gate prevents pool-pressure truncation in play,
	 * but retirement must still reject incomplete or failed formations. */
	for(wave = 0; wave < 3; ++wave)
		for(unsigned available = 0; available < FORMATION_SIZE; ++available) {
			start(&s); s.wave = wave;
			s.waveTimer = 60000;
			s.waves[0].planned = FORMATION_SIZE; s.waves[0].spawned = available;
			s.waves[0].remaining = available;
			for(i = 0; i < available; ++i) {
				s.enemies[i] = entity(280, 60 + i * 27, 1);
				s.enemies[i].waveId = 1; s.enemies[i].waveMember = i;
			}
			logicUpdate(&s, &idle);
			for(i = 0; i < available; ++i) {
				shootMember(&s, i);
				CHECK(!(s.events & EVENT_BONUS_DROP));
			}
			CHECK(!s.waves[0].remaining && s.waves[0].killed == available);
			CHECK(s.bonusCycle == 0 && !s.pickups[0].active);
		}
	start(&s); s.waveTimer = 1; logicUpdate(&s, &idle);
	s.stageFrame = g_stageFrames[0] - 1; logicUpdate(&s, &idle);
	CHECK(s.phase == PLAY && s.waves[0].remaining == 6 && !(s.events & EVENT_BONUS_DROP));
	start(&s); s.waveTimer = 1; logicUpdate(&s, &idle);
	s.lives = 1; s.invulnerable = 0; s.hostile[0] = entity(s.x + PLAYER_HIT_X, s.y + PLAYER_HIT_Y, 1);
	logicUpdate(&s, &idle);
	CHECK(s.phase == HERO_DYING && s.waves[0].remaining == 6);
	finishDeath(&s);
	CHECK(s.phase == GAMEOVER && !s.waves[0].remaining && !(s.events & EVENT_BONUS_DROP));
	/* Even a clear directly over the hero must render its pickup first. */
	start(&s); s.waveTimer = 1; logicUpdate(&s, &idle);
	for(i = 0; i < FORMATION_SIZE - 1; ++i) shootMember(&s, i);
	s.x = 200; s.y = PLAY_BOTTOM - PLAYER_H; shootMember(&s, FORMATION_SIZE - 1);
	CHECK((s.events & EVENT_BONUS_DROP) && !(s.events & EVENT_BONUS_PICKUP));
	CHECK(s.weaponLevel == 0 && s.pickups[0].active);
	logicUpdate(&s, &idle);
	CHECK(s.weaponLevel == 1 && (s.events & EVENT_BONUS_PICKUP));
}
static void collect(tGameState *s, unsigned kind, unsigned visible) {
	s->pickups[0] = entity(s->x, s->y, 1);
	s->pickups[0].kind = kind; s->pickups[0].visible = visible;
	s->waveTimer = 60000; logicUpdate(s, &idle);
}
static void testFiveBonusCycle(void) {
	const unsigned kinds[] = {BONUS_POWER, BONUS_FIRE, BONUS_SPEED, BONUS_SHIELD, BONUS_LIFE};
	tGameState s;
	CHECK(BONUS_COUNT == 4 && BONUS_KIND_COUNT == 5 && BONUS_FIRE == 4);
	start(&s);
	for(unsigned wave = 0; wave < 10; ++wave) {
		memset(s.pickups, 0, sizeof(s.pickups));
		s.waveTimer = 0; logicUpdate(&s, &idle);
		for(unsigned i = 0; i < FORMATION_SIZE; ++i) shootMember(&s, i);
		CHECK(s.pickups[0].active && s.pickups[0].kind == kinds[wave % 5]);
		CHECK(s.bonusCycle == (wave + 1) % 5);
	}
	/* Each kind replaces an oldest slot when all four pickup slots are full. */
	for(unsigned kind = 0; kind < BONUS_KIND_COUNT; ++kind) {
		start(&s); s.bonusCycle = kind; s.waveTimer = 0; logicUpdate(&s, &idle);
		for(unsigned i = 0; i < BONUS_COUNT; ++i) {
			s.pickups[i] = entity(250, 180, 1); s.pickups[i].age = i * 20;
		}
		for(unsigned i = 0; i < FORMATION_SIZE; ++i) shootMember(&s, i);
		CHECK(s.pickups[3].active && !s.pickups[3].age && s.pickups[3].kind == kinds[kind]);
	}
	start(&s);
	collect(&s, BONUS_FIRE, 0);
	CHECK(!s.shotLevel && !s.weaponLevel);
	logicUpdate(&s, &idle);
	CHECK(s.shotLevel == 1 && !s.weaponLevel);
	collect(&s, BONUS_POWER, 1);
	CHECK(s.shotLevel == 1 && s.weaponLevel == 1);
}
static void testBonusesAndPersistence(void) {
	tGameState s;
	unsigned kind, i;
	start(&s);
	collect(&s, BONUS_POWER, 0);
	CHECK(s.weaponLevel == 0 && s.pickups[0].active && !(s.events & EVENT_BONUS_PICKUP));
	logicUpdate(&s, &idle);
	CHECK(s.weaponLevel == 1 && !s.pickups[0].active && (s.events & EVENT_BONUS_PICKUP));
	for(kind = 0; kind < BONUS_KIND_COUNT; ++kind)
		for(i = 0; i < 4; ++i) collect(&s, kind, 1);
	CHECK(s.weaponLevel == 2 && s.speedLevel == 2 && s.shield == 2 && s.lives == 5);
	CHECK(s.shotLevel == 2);
	{ tInput right = {1, 0, 1}; int x = s.x;
		logicUpdate(&s, &right);
		logicUpdate(&s, &right);
		logicUpdate(&s, &idle);
		CHECK(s.x == x + 5 && s.shots[0].hp == 3);
	}
	s.invulnerable = 0; s.hostile[0] = entity(s.x + PLAYER_HIT_X, s.y + PLAYER_HIT_Y, 1);
	logicUpdate(&s, &idle);
	CHECK(s.shield == 1 && s.lives == 5 && s.invulnerable == 30 && (s.events & EVENT_HIT));
	logicUpdate(&s, &idle); CHECK(s.shield == 1);
	s.shield = 0; s.invulnerable = 0; s.hostile[0] = entity(s.x + PLAYER_HIT_X, s.y + PLAYER_HIT_Y, 1);
	logicUpdate(&s, &idle);
	CHECK(s.lives == 4 && s.weaponLevel == 1 && s.speedLevel == 1 && !s.shield);
	CHECK(s.shotLevel == 1);
	s.shield = 2; s.phase = CLEAR; s.sceneReady = 1; s.phaseFrame = SCENE_FRAMES - 1;
	logicUpdate(&s, &idle);
	CHECK(s.level == 1 && s.weaponLevel == 1 && s.speedLevel == 1 && s.shield == 2);
	CHECK(s.shotLevel == 1);
	finishScene(&s);
	s.pickups[0] = entity(250, 100, 1); s.pickups[0].age = BONUS_LIFETIME - 1;
	s.pickups[1] = entity(0, 100, 1); s.pickups[1].vx = -1;
	logicUpdate(&s, &idle); logicUpdate(&s, &idle);
	CHECK(!s.pickups[0].active && !s.pickups[1].active);
	s.phase = GAMEOVER; s.phaseFrame = 0; returnToTitle(&s);
	CHECK(!s.weaponLevel && !s.shotLevel && !s.speedLevel && !s.shield && !s.bonusCycle);
	/* Full pickup pool replaces oldest, still requiring a rendered frame. */
	start(&s); s.waveTimer = 1; logicUpdate(&s, &idle);
	for(i = 0; i < BONUS_COUNT; ++i) {
		s.pickups[i] = entity(250, 180, 1); s.pickups[i].age = i * 20;
	}
	for(i = 0; i < FORMATION_SIZE; ++i) shootMember(&s, i);
	CHECK(s.pickups[3].age == 0 && s.pickups[3].x == 200);
}
static void testFairShootingAndBossBounds(void) {
	tGameState s;
	unsigned i, tick, seen[SHOT_COUNT] = {0}, level;
	start(&s); s.waveTimer = 60000;
	for(i = 0; i < ENEMY_COUNT; ++i) s.enemies[i] = entity(250, 98, 1);
	for(i = 0; i < SHOT_COUNT; ++i) s.shots[i] = entity(100, 104, 1);
	for(tick = 0; tick < SHOT_COUNT; ++tick) {
		unsigned targets = 0, shots = 0;
		logicUpdate(&s, &idle); checkSchedule(&s);
		for(i = 0; i < SHOT_COUNT; ++i) { seen[i] += s.shots[i].visible; shots += s.shots[i].visible; }
		for(i = 0; i < ENEMY_COUNT; ++i) targets += s.enemies[i].visible;
		CHECK(shots == SHOT_COUNT && targets == 1);
	}
	for(i = 0; i < SHOT_COUNT; ++i) CHECK(seen[i] == SHOT_COUNT);
	for(level = 0; level < LEVEL_COUNT; ++level) {
		start(&s); s.level = level; s.wave = g_stageWaveQuota[level];
		arriveBoss(&s);
		for(tick = 0; tick < 256; ++tick) {
			s.invulnerable = 2; logicUpdate(&s, &idle);
			CHECK(s.boss.y >= PLAY_TOP && s.boss.y + BOSS_H <= PLAY_BOTTOM);
			CHECK(s.boss.x >= 0 && s.boss.x <= BOSS_MAX_X);
		}
	}
}
static void testFormationFireAndChargePriority(void) {
	tGameState s;
	start(&s); s.waveTimer = 60000;
	s.enemies[0] = entity(200, 80, 1);
	s.enemies[0].age = 39; s.enemies[0].waveMember = 1;
	logicUpdate(&s, &idle);
	CHECK(!s.hostile[0].active);
	s.enemies[0].age = 39; s.enemies[0].waveMember = 0;
	s.enemies[0].fireCountdown = 1;
	logicUpdate(&s, &idle);
	CHECK(s.hostile[0].active);
	s.hostile[0].active = 0;
	s.enemies[0].age = 39; s.enemies[0].kind = ENEMY_ASTEROID;
	logicUpdate(&s, &idle);
	CHECK(!s.hostile[0].active);
	s.enemies[0].age = 79; s.enemies[0].kind = ENEMY_GUNNER; s.enemies[0].waveMember = 5;
	s.enemies[0].fireCountdown = 0;
	logicUpdate(&s, &idle);
	CHECK(s.hostile[0].active);
	start(&s); s.waveTimer = 60000;
	for(unsigned i = 0; i < ENEMY_COUNT; ++i) s.enemies[i] = entity(250, 98, 1);
	for(unsigned i = 0; i < SHOT_COUNT; ++i) s.shots[i] = entity(100, 104, 1);
	s.shots[0].kind = SHOT_CHARGED;
	logicUpdate(&s, &idle);
	CHECK(s.shots[0].visible);
	checkSchedule(&s);
}

/* Same-tick fans fill the pool's lowest free slots in ray order. A refused
 * ray leaves its slot free for the next ray, across both enemies' fans. */
static void testSameTickFansFillLowestFreeSlots(void) {
	tGameState s;
	uint8_t wasActive[HOSTILE_COUNT];
	unsigned i, admitted = 0, freeSeen = 0;
	start(&s); s.waveTimer = 60000; s.invulnerable = 2;
	for(i = 0; i < 2; ++i) {
		s.enemies[i] = entity(200, (int16_t)(i ? 140 : 100), 1);
		s.enemies[i].kind = ENEMY_GUNNER; s.enemies[i].fireCountdown = 1;
	}
	/* Both PLAY channels block each centre ray; holes interleave the pool. */
	for(i = 0; i < 4; ++i) {
		s.hostile[i * 2] = entity(150, (int16_t)((i & 2 ? 140 : 100) + (ENEMY_H - HOSTILE_H) / 2), 1);
		s.hostile[i * 2].vx = HOSTILE_VX; s.hostile[i * 2].channel = (uint8_t)(6 + (i & 1));
	}
	for(i = 0; i < HOSTILE_COUNT; ++i) wasActive[i] = s.hostile[i].active;
	logicUpdate(&s, &idle);
	for(i = 0; i < HOSTILE_COUNT; ++i) {
		if(wasActive[i]) { CHECK(s.hostile[i].active); continue; }
		++freeSeen;
		if(s.hostile[i].active) { CHECK(freeSeen == ++admitted); }
	}
	CHECK(admitted > 0 && admitted < 2 * 5); /* Two sector-1 gunners, five rays each. */
	checkSchedule(&s);
}

static unsigned hostileCount(const tGameState *s) {
	unsigned count = 0;
	for(unsigned i = 0; i < HOSTILE_COUNT; ++i) count += s->hostile[i].active;
	return count;
}

/* Empty-pool fan oracle: attempted rays may be clipped at corridor edges, and
 * admitted rays still move on this combat tick, even without a body step. */
static void checkEmptyFan(const tGameState *s, int x, int y, unsigned rays, int aim) {
	unsigned accepted = 0, attempted = 0;
	for(int ray = -(int)(rays / 2); ray <= (int)(rays / 2); ++ray) {
		++attempted;
		int originY = y + ray * 22;
		int vy = aim + ray;
		if(vy < -2) vy = -2;
		if(vy > 2) vy = 2;
		int movedY = originY + vy / 2 + ((s->simFrame & 1) ? vy % 2 : 0);
		if(originY < PLAY_TOP || originY + HOSTILE_H > PLAY_BOTTOM) continue;
		/* Accepted rays may leave the corridor immediately; preserve slot order. */
		const tEntity *e = &s->hostile[accepted++];
		CHECK(e->x == x + (ray < 0 ? -ray : ray) * 6 - 1 - (int)(s->simFrame & 1));
		CHECK(e->y == movedY && e->vx == -3 && e->vy == vy);
		CHECK(e->active == (movedY >= PLAY_TOP && movedY + HOSTILE_H <= PLAY_BOTTOM));
	}
	CHECK(attempted == rays);
	for(unsigned i = accepted; i < HOSTILE_COUNT; ++i) CHECK(!s->hostile[i].active);
}

static void testHalfSpeedMovement(void) {
	tGameState s;
	for(unsigned speed = 0; speed <= 2; ++speed) {
		for(int sign = -1; sign <= 1; sign += 2) {
			tInput input = {sign, sign, 0};
			start(&s); s.x = 100; s.y = 100; s.speedLevel = speed;
			logicUpdate(&s, &input); logicUpdate(&s, &input);
			CHECK(s.x == 100 + sign * (3 + (int)speed));
			CHECK(s.y == 100 + sign * (3 + (int)speed));
			CHECK(!s.moveRemainderX && !s.moveRemainderY);
		}
	}
	start(&s);
	{ tInput right = {1, 1, 0}, left = {-1, -1, 0};
		logicUpdate(&s, &right);
		CHECK(s.moveRemainderX == 1 && s.moveRemainderY == 1);
		logicUpdate(&s, &idle);
		CHECK(s.x == 33 && s.y == 127);
		logicUpdate(&s, &left);
		CHECK(s.x == 32 && s.y == 126 && !s.moveRemainderX);
		s.x = WORLD_W - PLAYER_W; s.y = PLAY_BOTTOM - PLAYER_H;
		logicUpdate(&s, &right);
		CHECK(!s.moveRemainderX && !s.moveRemainderY);
		s.moveRemainderX = 1; s.moveRemainderY = -1;
		s.phase = CLEAR; s.sceneReady = 1; s.phaseFrame = SCENE_FRAMES - 1;
		logicUpdate(&s, &idle);
		CHECK(!s.moveRemainderX && !s.moveRemainderY);
	}
	for(unsigned parity = 0; parity < 2; ++parity) {
		start(&s); s.simFrame = parity; s.waveTimer = 60000;
		s.enemies[0] = entity(240, 80, 1); s.enemies[0].vx = -3;
		s.enemies[1] = entity(240, 110, 1); s.enemies[1].kind = ENEMY_WEAVER;
		s.enemies[1].vx = -2;
		s.pickups[0] = entity(240, 180, 1); s.pickups[0].vx = -1;
		s.hostile[0] = entity(180, 160, 1); s.hostile[0].vx = -3; s.hostile[0].vy = -1;
		s.shots[0] = entity(80, 200, 1); s.shots[0].vx = 6;
		logicUpdate(&s, &idle); logicUpdate(&s, &idle);
		CHECK(s.enemies[0].x == 237);
		CHECK(s.enemies[1].x == 238 && s.enemies[1].y == 111);
		CHECK(s.pickups[0].x == 239);
		CHECK(s.hostile[0].x == 177 && s.hostile[0].y == 159);
		CHECK(s.shots[0].x == 92);
	}
}

static void testHeroCoreAndCurtainGeometry(void) {
	tGameState s;
	CHECK(PLAYER_W == 32 && PLAYER_H == 24 && PLAYER_HIT_W == 8 && PLAYER_HIT_H == 8);
	CHECK(HOSTILE_W == 6 && HOSTILE_H == 8 && HOSTILE_COUNT == 32);
	/* Former second/third dots must not create ghost hits at coreX. */
	for(unsigned offset = 6; offset <= 12; offset += 6) {
		start(&s); s.x = 100; s.y = 100; s.invulnerable = 0;
		s.hostile[0] = entity(s.x + PLAYER_HIT_X - offset, s.y + PLAYER_HIT_Y, 1);
		logicUpdate(&s, &idle);
		CHECK(s.lives == 3 && !(s.events & EVENT_HIT));
		s.hostile[0] = entity(s.x + PLAYER_HIT_X, s.y + PLAYER_HIT_Y, 1);
		logicUpdate(&s, &idle);
		CHECK(s.lives == 2 && (s.events & EVENT_HIT));
	}
	for(unsigned actor = 0; actor < 2; ++actor) {
		for(unsigned edge = 0; edge < 4; ++edge) {
			start(&s); s.x = 100; s.y = 100; s.invulnerable = 0;
			tEntity *e = actor ? &s.enemies[0] : &s.hostile[0];
			/* Visual wing contact misses; one pixel crossing the core hits. */
			*e = entity(112, edge < 2 ? 108 - (actor ? ENEMY_H : HOSTILE_H) + edge : 115 + edge - 2, 1);
			logicUpdate(&s, &idle);
			CHECK(s.lives == (edge == 1 || edge == 2 ? 2 : 3));
		}
	}
	start(&s); s.x = 100; s.y = 100; s.invulnerable = 0;
	s.hostile[0] = entity(120, 108, 1); /* Exact right core edge. */
	logicUpdate(&s, &idle); CHECK(s.lives == 3);
	s.hostile[0] = entity(119, 108, 1); s.hostile[0].visible = 0;
	logicUpdate(&s, &idle); CHECK(s.lives == 3);
	s.hostile[0].visible = 1;
	logicUpdate(&s, &idle); CHECK(s.lives == 2);
	start(&s); s.pickups[0] = entity(s.x + PLAYER_W - 1, s.y, 1);
	logicUpdate(&s, &idle); CHECK(s.weaponLevel == 1);
	for(unsigned edge = 0; edge < 6; ++edge) {
		const int xs[] = {-HOSTILE_W, -HOSTILE_W + 1, 319, 320, 100, 100};
		start(&s); s.hostile[0] = entity(xs[edge], edge == 4 ? PLAY_TOP - 1 :
			(edge == 5 ? PLAY_BOTTOM - HOSTILE_H + 1 : PLAY_TOP), 1);
		logicUpdate(&s, &idle);
		CHECK(s.hostile[0].active == (edge == 1 || edge == 2));
		CHECK(s.hostile[0].visible == (edge == 2));
		checkSchedule(&s);
	}
}

static void testRepeatedDenseVolleys(void) {
	tGameState s;
	for(unsigned kind = 0; kind <= ENEMY_ASTEROID; ++kind) {
		if(kind == ENEMY_BOSS) continue;
		start(&s); s.waveTimer = 60000;
		s.enemies[0] = entity(240, 120, 1); s.enemies[0].kind = kind;
		for(unsigned tick = 1; tick <= 184; ++tick) {
			/* Keep one attacker visible and remove earlier bullets to count volleys. */
			memset(s.hostile, 0, sizeof(s.hostile));
			s.enemies[0].visible = 1;
			logicUpdate(&s, &idle);
			unsigned age = (4 + 4 * tick) / 5;
			CHECK(s.enemies[0].age == age);
			unsigned expected = kind == ENEMY_ASTEROID ? 0 :
				(tick >= 50 && (tick - 50) % 96 == 0 ? (kind == ENEMY_GUNNER ? 5 : 3) : 0);
			CHECK(hostileCount(&s) == expected);
			for(unsigned i = 0; i < HOSTILE_COUNT; ++i) if(s.hostile[i].active) {
				CHECK(s.hostile[i].vx == -3 && s.hostile[i].vy >= -2 && s.hostile[i].vy <= 2);
			}
			checkSchedule(&s);
		}
	}
	for(unsigned member = 0; member < FORMATION_SIZE; ++member) {
		start(&s); s.waveTimer = 60000;
		s.enemies[0] = entity(240, 120, 1); s.enemies[0].waveMember = member;
		s.enemies[0].fireCountdown = 50 + member * 10;
		for(unsigned tick = 0; tick < 48 + member * 10; ++tick) {
			logicUpdate(&s, &idle); CHECK(!hostileCount(&s));
		}
		logicUpdate(&s, &idle); CHECK(!hostileCount(&s));
		logicUpdate(&s, &idle); CHECK(hostileCount(&s) == 3);
	}
	/* Fan geometry: chevron stagger and an always-open 14px gap. */
	start(&s); s.waveTimer = 60000; s.y = 120 - 4;
	s.enemies[0] = entity(240, 120, 3); s.enemies[0].kind = ENEMY_GUNNER; s.enemies[0].age = 39;
	s.enemies[0].fireCountdown = 1;
	s.simFrame = 1;
	logicUpdate(&s, &idle);
	CHECK(hostileCount(&s) == 5);
	for(unsigned i = 1; i < 5; ++i) {
		int ray = (int)i - 2;
		CHECK(s.hostile[i].y - s.hostile[i - 1].y >= FAN_SPACING);
		CHECK(s.hostile[i].y - s.hostile[i - 1].y - HOSTILE_H >= 14);
		CHECK(s.hostile[i].x == 239 + (ray < 0 ? -ray : ray) * FAN_STAGGER);
	}
	/* Every allocation limit, including a partially fitting five-ray fan. */
	for(unsigned freeSlots = 0; freeSlots <= 5; ++freeSlots) {
		start(&s); s.waveTimer = 60000;
		s.enemies[0] = entity(240, 120, 1); s.enemies[0].kind = ENEMY_GUNNER; s.enemies[0].age = 39;
		s.enemies[0].fireCountdown = 1;
		for(unsigned i = freeSlots; i < HOSTILE_COUNT; ++i) {
			s.hostile[i] = entity(60, PLAY_TOP + (i / 2) % 14 * 11, 7);
			s.hostile[i].channel = 6 + (i & 1);
		}
		logicUpdate(&s, &idle);
		for(unsigned i = freeSlots; i < HOSTILE_COUNT; ++i) CHECK(s.hostile[i].hp == 7);
		CHECK(hostileCount(&s) <= HOSTILE_COUNT);
	}
	/* Packed rows: only displayable bullets survive, and all of them show. */
	start(&s); s.waveTimer = 60000;
	for(unsigned i = 0; i < HOSTILE_COUNT; ++i) s.hostile[i] = entity(200, 56 + (i % 24) * 6, 1);
	logicUpdate(&s, &idle);
	unsigned shown = 0;
	for(unsigned i = 0; i < HOSTILE_COUNT; ++i) shown += s.hostile[i].visible;
	CHECK(shown == hostileCount(&s) && shown >= 20); checkSchedule(&s);
}

static void testBossHalfPhaseAndCadence(void) {
	const unsigned cadence[] = {64, 52, 44, 36};
	const unsigned rates[] = {16, 17, 18, 20}, rays[] = {5, 7, 7, 9};
	tGameState s;
	for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
		start(&s); s.level = level; s.wave = g_stageWaveQuota[level];
		arriveBoss(&s);
		unsigned accumulator = s.enemyAccumulator;
		for(unsigned tick = 1; tick <= 1024; ++tick) {
			int16_t x = s.boss.x, y = s.boss.y;
			unsigned beforeTick = s.boss.tick;
			memset(s.hostile, 0, sizeof(s.hostile)); s.invulnerable = 2;
			logicUpdate(&s, &idle);
			unsigned enemyTick = (accumulator + rates[level] * tick) / 20;
			CHECK(s.boss.tick == enemyTick);
			if(enemyTick == beforeTick || (enemyTick > 1 && (enemyTick & 1)))
				CHECK(s.boss.x == x && s.boss.y == y);
			CHECK(s.boss.x >= 0 && s.boss.x <= BOSS_MAX_X);
			CHECK(s.boss.y >= PLAY_TOP && s.boss.y + BOSS_H <= PLAY_BOTTOM);
			unsigned expected = 0;
			if(tick >= 50 && (tick - 50) % cadence[level] == 0) {
				if(level == 3 && !(enemyTick & 64)) expected = 5;
				else {
					int radius = rays[level] / 2;
					int fanY = s.boss.y + (BOSS_H - HOSTILE_H) / 2;
					int delta = s.y + PLAYER_H / 2 - fanY - HOSTILE_H / 2;
					int aim = level == 1 ? 0 : (delta < 0 ? -1 : delta > 0);
					checkEmptyFan(&s, s.boss.x - HOSTILE_W, fanY, rays[level], aim);
					for(int ray = -radius; ray <= radius; ++ray) {
						int origin = fanY + ray * FAN_SPACING;
						int vy = aim + ray;
						if(vy < -2) vy = -2;
						if(vy > 2) vy = 2;
						int moved = origin + vy / 2 + ((s.simFrame & 1) ? vy % 2 : 0);
						if(origin >= PLAY_TOP && origin + HOSTILE_H <= PLAY_BOTTOM &&
							moved >= PLAY_TOP && moved + HOSTILE_H <= PLAY_BOTTOM) ++expected;
					}
				}
			}
			CHECK(hostileCount(&s) == expected);
			for(unsigned i = 0; i < HOSTILE_COUNT; ++i) if(s.hostile[i].active) {
				CHECK(s.hostile[i].vx == HOSTILE_VX && s.hostile[i].vy >= -2 && s.hostile[i].vy <= 2);
				for(unsigned j = 0; j < i; ++j) if(s.hostile[j].active)
					CHECK(s.hostile[i].y != s.hostile[j].y);
			}
			checkSchedule(&s);
		}
	}
}
static void testFanCorridorEdges(void) {
	tGameState s;
	/* Rays beyond the corridor are skipped, never clamped onto the edge. */
	const int16_t ys[2][3] = {{60, 83, 105}, {159, 181, 204}};
	const int16_t xs[2][3] = {{239, 245, 251}, {251, 245, 239}};
	const int8_t velocities[2][3] = {{1, 2, 2}, {-2, -2, -1}};
	for(unsigned edge = 0; edge < 2; ++edge) {
		start(&s); s.waveTimer = 60000; s.simFrame = 1;
		s.enemies[0] = entity(240, edge ? PLAY_BOTTOM - ENEMY_H : PLAY_TOP, 3);
		s.enemies[0].kind = ENEMY_GUNNER; s.enemies[0].age = 39;
		s.enemies[0].fireCountdown = 1;
		logicUpdate(&s, &idle);
		CHECK(hostileCount(&s) == 3);
		for(unsigned i = 0; i < 3; ++i) {
			CHECK(s.hostile[i].y == ys[edge][i] && s.hostile[i].x == xs[edge][i]);
			CHECK(s.hostile[i].vy == velocities[edge][i]);
		}
		checkSchedule(&s);
	}
}

static void testWholeFormationMotion(void) {
	tGameState s;
	/* Repeated waves cover all five kinds with six members.
	 * Exercise homing toward both edges, the center, and a moving hero. */
	for(unsigned wave = 0; wave < 15; ++wave) {
		for(unsigned path = 0; path < 4; ++path) {
			start(&s); s.wave = wave; s.waveTimer = 1;
			logicUpdate(&s, &idle);
			unsigned ticks = 0, alive;
			do {
				alive = 0;
				for(unsigned i = 0; i < ENEMY_COUNT; ++i) {
					const tEntity *e = &s.enemies[i];
					if(!e->active) continue;
					++alive;
					CHECK(e->kind == (wave % 5 == 4 ? ENEMY_ASTEROID : wave % 5));
					CHECK(e->visible == (e->x >= 0));
					if(e->visible) CHECK(e->channel == 4);
					for(unsigned j = 0; j < i; ++j) if(s.enemies[j].active)
						CHECK(e->y >= s.enemies[j].y + ENEMY_H + 2 ||
							s.enemies[j].y >= e->y + ENEMY_H + 2);
				}
				CHECK(s.wave == wave + 1);
				CHECK(!(s.events & EVENT_BONUS_DROP) && !s.bonusCycle);
				checkSchedule(&s);
				if(!alive) break;
				s.y = path == 0 ? PLAY_TOP : path == 1 ? PLAY_BOTTOM - PLAYER_H :
					path == 2 ? 126 : ((ticks & 32) ? PLAY_TOP : PLAY_BOTTOM - PLAYER_H);
				s.invulnerable = 2;
				logicUpdate(&s, &idle);
			} while(++ticks < 600);
			CHECK(ticks < 600 && !alive && !s.waveTimer);
			logicUpdate(&s, &idle);
			CHECK(s.wave == wave + 2 && s.enemies[0].active);
		}
	}
}

static unsigned enemyCount(const tGameState *s) {
	unsigned count = 0;
	for(unsigned i = 0; i < ENEMY_COUNT; ++i) count += s->enemies[i].active;
	return count;
}

static void testExactCampaignQuotas(void) {
	/* First three triple the reference; sector four adds three harder waves. */
	const unsigned quotas[] = {18, 21, 24, 27};
	unsigned elapsed[2][LEVEL_COUNT];
	for(unsigned fast = 0; fast < 2; ++fast) {
		for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
			tGameState s;
			unsigned spawns = 0, drops = 0, tick;
			start(&s); s.level = level;
			CHECK(g_stageWaveQuota[level] == quotas[level]);
			for(tick = 0; tick < 15000 && s.phase == PLAY; ++tick) {
				unsigned previous = s.wave, alive = enemyCount(&s);
				if(fast) {
					/* Real collision retirement, all six lanes, without changing cadence. */
					for(unsigned i = 0; i < FORMATION_SIZE; ++i) {
						tEntity *e = &s.enemies[i];
						if(e->active) s.shots[i] = entity(e->x - 2, e->y + 4, 6);
					}
				}
				s.invulnerable = 2; logicUpdate(&s, &idle);
				if(s.wave != previous) {
					++spawns;
					CHECK(!alive && s.wave == previous + 1);
					CHECK(enemyCount(&s) == 6 && s.waves[0].remaining == 6);
				}
				drops += !!(s.events & EVENT_BONUS_DROP);
				CHECK(s.wave <= quotas[level]);
				if(previous == quotas[level] && alive) CHECK(s.phase == PLAY);
				if(s.phase == BOSS_INTRO) CHECK(previous == quotas[level] && !alive);
				checkSchedule(&s);
			}
			CHECK(tick < 15000 && s.phase == BOSS_INTRO);
			CHECK(spawns == quotas[level] && s.wave == quotas[level]);
			CHECK(drops == (fast ? quotas[level] : 0));
			CHECK(fast || (!s.score && !s.bonusCycle));
			elapsed[fast][level] = tick;
		}
	}
	for(unsigned level = 0; level < LEVEL_COUNT; ++level)
		CHECK(elapsed[1][level] < elapsed[0][level]);
}

static void testQuotaTimerAndTrackerGuards(void) {
	tGameState s;
	start(&s); s.stageFrame = UINT16_MAX; s.frame = UINT32_MAX;
	s.waveTimer = 0;
	logicUpdate(&s, &idle);
	CHECK(!s.stageFrame && !s.frame && s.phase == PLAY && s.wave == 1);
	/* Even after the final spawn, a timer cutoff cannot erase survivors. */
	s.wave = g_stageWaveQuota[0]; s.stageFrame = g_stageFrames[0] - 1;
	logicUpdate(&s, &idle);
	CHECK(s.phase == PLAY && enemyCount(&s) == 6 && s.waves[0].remaining == 6);
	for(unsigned i = 0; i < FORMATION_SIZE; ++i) s.enemies[i].x = -ENEMY_W;
	logicUpdate(&s, &idle);
	CHECK(s.phase == PLAY && !enemyCount(&s) && !s.waves[0].remaining);
	CHECK(s.waves[0].failed && !(s.events & EVENT_BONUS_DROP));
	waitBossIntro(&s);
	CHECK(s.phase == BOSS_INTRO && s.wave == g_stageWaveQuota[0]);
	/* Busy trackers cannot be overwritten, even with an empty entity pool. */
	start(&s); s.waveTimer = 0;
	for(unsigned i = 0; i < WAVE_TRACK_COUNT; ++i) s.waves[i].remaining = 1;
	logicUpdate(&s, &idle);
	CHECK(!s.wave && !s.waveTimer && !enemyCount(&s));
	for(unsigned i = 0; i < WAVE_TRACK_COUNT; ++i) CHECK(s.waves[i].remaining == 1);
	s.wave = g_stageWaveQuota[0]; logicUpdate(&s, &idle);
	CHECK(s.phase == PLAY);
	/* Retry after pool pressure releases: no partial formation or consumed quota. */
	for(unsigned free = 0; free < FORMATION_SIZE; ++free) {
		start(&s); s.waveTimer = 0;
		for(unsigned i = free; i < ENEMY_COUNT; ++i)
			s.enemies[i] = entity(-ENEMY_W, 100, 1);
		logicUpdate(&s, &idle);
		CHECK(!s.wave && !s.waves[0].planned && !enemyCount(&s));
		logicUpdate(&s, &idle);
		CHECK(s.wave == 1 && enemyCount(&s) == 6);
		CHECK(s.waves[0].spawned == 6 && s.waves[0].remaining == 6 && !s.waves[0].failed);
	}
}

static void testFixedLanesWithMissingMembers(void) {
	for(unsigned kind = 0; kind < 5; ++kind) {
		for(unsigned lost = 0; lost < FORMATION_SIZE; ++lost) {
			for(unsigned path = 0; path < 4; ++path) {
				tGameState s;
				unsigned tick;
				start(&s); s.wave = kind; s.waveTimer = 0;
				logicUpdate(&s, &idle);
				for(tick = 0; tick < 600 && enemyCount(&s); ++tick) {
					/* Remove each lane in turn, including middle lanes, via combat. */
					if(tick == 16) {
						tEntity *e = &s.enemies[lost];
						s.shots[0] = entity(e->x - 2, e->y + 4, 6);
					}
					s.y = path == 0 ? PLAY_TOP : path == 1 ? PLAY_BOTTOM - PLAYER_H :
						path == 2 ? 126 : ((tick & 16) ? PLAY_TOP : PLAY_BOTTOM - PLAYER_H);
					s.invulnerable = 2; logicUpdate(&s, &idle);
					CHECK(s.wave == kind + 1 && s.phase == PLAY);
					if(tick >= 16) CHECK(!s.enemies[lost].active);
					for(unsigned i = 0; i < FORMATION_SIZE; ++i) {
						const tEntity *e = &s.enemies[i];
						if(!e->active) continue;
						CHECK(e->waveMember == i && e->waveId == 1);
						CHECK(e->y >= 56 + (int)i * 27 && e->y <= 65 + (int)i * 27);
						CHECK(e->visible == (e->x >= 0));
					}
					if(kind == 4) CHECK(!hostileCount(&s));
					CHECK(!(s.events & EVENT_BONUS_DROP));
					checkSchedule(&s);
				}
				CHECK(tick < 600 && !enemyCount(&s) && !s.waves[0].remaining);
				CHECK(s.waves[0].killed == 1 && s.waves[0].failed);
			}
		}
	}
}

static void testSeparateBudgetsAndPickupPressure(void) {
	tGameState s;
	start(&s); s.waveTimer = 60000;
	CHECK(ENEMY_SPRITE_CAPACITY == 6 && BULLET_SPRITE_CAPACITY == 16);
	for(unsigned i = 0; i < 8; ++i) s.enemies[i] = entity(280, PLAY_TOP + i * 18, 1);
	/* Fourteen 11px rows per channel fill the corridor; a 29th is refused. */
	for(unsigned i = 0; i < 29; ++i) s.hostile[i] = entity(220, PLAY_TOP + (i % 14) * 11, 1);
	for(unsigned i = 0; i < SHOT_COUNT; ++i) s.shots[i] = entity(100, PLAY_TOP + i * 6, 1);
	for(unsigned i = 0; i < BONUS_COUNT; ++i) s.pickups[i] = entity(280, 100, 1);
	logicUpdate(&s, &idle);
	unsigned enemies = 0, shots = 0, bullets[2] = {0};
	for(unsigned i = 0; i < ENEMY_COUNT; ++i) enemies += s.enemies[i].visible;
	for(unsigned i = 0; i < HOSTILE_COUNT; ++i) if(s.hostile[i].visible) ++bullets[s.hostile[i].channel - 6];
	for(unsigned i = 0; i < SHOT_COUNT; ++i) shots += s.shots[i].visible && !s.shots[i].channel;
	CHECK(enemies == 6 && bullets[0] == 14 && bullets[1] == 14 && shots == SHOT_COUNT);
	CHECK(!s.hostile[28].active);
	for(unsigned i = 0; i < BONUS_COUNT; ++i) CHECK(s.pickups[i].visible && !s.pickups[i].channel);
	checkSchedule(&s);
	/* Collection still uses the body, even while every sprite pool is busy. */
	s.pickups[0].x = s.x + PLAYER_W - 1; s.pickups[0].y = s.y;
	logicUpdate(&s, &idle);
	CHECK(s.weaponLevel == 1 && (s.events & EVENT_BONUS_PICKUP));

	/* An edge kill must spawn inside the BOB save guard, before any movement. */
	start(&s); s.waveTimer = 1; logicUpdate(&s, &idle);
	for(unsigned i = 0; i < FORMATION_SIZE - 1; ++i) shootMember(&s, i);
	s.enemies[5].x = 304; s.enemies[5].vx = 0;
	s.shots[0] = entity(BOB_MAX_X - 3, s.enemies[5].y, 6);
	logicUpdate(&s, &idle);
	CHECK((s.events & EVENT_BONUS_DROP) && s.pickups[0].x == 303);
	CHECK(s.pickups[0].visible && !s.pickups[0].channel);
}

static void testNormalPatternsAndDamage(void) {
	const int offsets[3][3] = {{0, 0, 0}, {-6, 6, 0}, {-8, 0, 8}};
	for(unsigned pattern = 0; pattern < 3; ++pattern)
		for(unsigned power = 0; power < 3; ++power)
			for(unsigned edge = 0; edge < 2; ++edge) {
				tGameState s;
				start(&s); s.waveTimer = 60000;
				s.shotLevel = pattern; s.weaponLevel = power;
				s.y = edge ? PLAY_BOTTOM - PLAYER_H : PLAY_TOP;
				logicUpdate(&s, &fire);
				CHECK(!(s.events & EVENT_SHOT));
				logicUpdate(&s, &idle);
				CHECK((s.events & EVENT_SHOT) && !(s.events & EVENT_LANCE));
				for(unsigned i = 0; i < SHOT_COUNT; ++i) {
					const tEntity *e = &s.shots[i];
					CHECK(e->active == (i <= pattern));
					if(!e->active) continue;
					CHECK(e->kind == SHOT_NORMAL && e->hp == power + 1);
					CHECK(e->vx == 6 && e->vy == 0 && e->visible && !e->channel);
					CHECK(e->x == s.x + PLAYER_W + 6);
					CHECK(e->y == s.y + (PLAYER_H - SHOT_H) / 2 + offsets[pattern][i]);
					CHECK(e->y >= s.y && e->y + SHOT_H <= s.y + PLAYER_H);
				}
				checkSchedule(&s);
				/* Damage is verified by real collision, one lane at a time. */
				for(unsigned i = 0; i <= pattern; ++i) {
					tGameState hit = s;
					for(unsigned j = 0; j <= pattern; ++j)
						if(j != i) hit.shots[j].active = 0;
					int y = hit.shots[i].y;
					if(y > PLAY_BOTTOM - ENEMY_H) y = PLAY_BOTTOM - ENEMY_H;
					hit.enemies[0] = entity(hit.shots[i].x + 6, y, 10);
					logicUpdate(&hit, &idle);
					CHECK(hit.enemies[0].hp == 9 - power && !hit.shots[i].active);
				}
			}
}

static void testVolleyPoolPressure(void) {
	CHECK(SHOT_COUNT == 12);
	for(unsigned pattern = 0; pattern < 3; ++pattern)
		for(unsigned charged = 0; charged < 2; ++charged)
			for(unsigned freeSlots = 0; freeSlots <= SHOT_COUNT; ++freeSlots) {
				tGameState s;
				unsigned needed = charged ? 1 : pattern + 1, created = 0;
				start(&s); s.waveTimer = 60000; s.shotLevel = pattern;
				/* Fragmented slots exercise allocation across the whole pool. */
				for(unsigned i = freeSlots; i < SHOT_COUNT; ++i)
					s.shots[(i * 5) % SHOT_COUNT] = entity(200, 80, 7);
				s.charge = charged ? CHARGE_FRAMES : 1;
				logicUpdate(&s, &idle);
				CHECK(!s.charge);
				CHECK(!!(s.events & EVENT_SHOT) == (freeSlots >= needed));
				CHECK(!!(s.events & EVENT_LANCE) == (charged && freeSlots >= needed));
				for(unsigned i = 0; i < SHOT_COUNT; ++i)
					if(s.shots[i].active && s.shots[i].hp != 7) {
						++created;
						CHECK(s.shots[i].hp == (charged ? 6 : 1));
						CHECK(s.shots[i].kind == charged);
					}
				CHECK(created == (freeSlots >= needed ? needed : 0));
				for(unsigned i = freeSlots; i < SHOT_COUNT; ++i)
					CHECK(s.shots[(i * 5) % SHOT_COUNT].hp == 7);
				checkSchedule(&s);
				memset(s.shots, 0, sizeof(s.shots));
				logicUpdate(&s, &idle);
				CHECK(!(s.events & (EVENT_SHOT | EVENT_LANCE)));
			}
}

static void testReleaseThresholdsAndCooldown(void) {
	CHECK(CHARGE_FRAMES == 50 && FIRE_INTERVAL == 8);
	for(unsigned held = 0; held <= 51; ++held) {
		tGameState s;
		start(&s); s.waveTimer = 60000;
		for(unsigned tick = 1; tick <= held; ++tick) {
			logicUpdate(&s, &fire);
			CHECK(!(s.events & (EVENT_SHOT | EVENT_LANCE)));
			CHECK(!!(s.events & EVENT_CHARGE) == (tick == 50));
		}
		logicUpdate(&s, NULL);
		CHECK(!!(s.events & EVENT_SHOT) == (held > 0));
		CHECK(!!(s.events & EVENT_LANCE) == (held >= 50));
		CHECK(!s.charge);
		logicUpdate(&s, &idle);
		CHECK(!(s.events & (EVENT_SHOT | EVENT_LANCE | EVENT_CHARGE)));
	}
	for(unsigned period = 2; period <= 10; ++period) {
		tGameState s;
		start(&s); s.waveTimer = 60000;
		logicUpdate(&s, &fire); logicUpdate(&s, &idle);
		CHECK(s.events & EVENT_SHOT);
		for(unsigned tick = 1; tick <= period; ++tick) {
			logicUpdate(&s, tick == period ? &idle : &fire);
			CHECK(!!(s.events & EVENT_SHOT) == (tick == period && period >= 8));
		}
		CHECK(!s.charge);
		/* Rejected releases cannot turn into a deferred shot while held. */
		for(unsigned tick = 0; tick < 12; ++tick) {
			logicUpdate(&s, &fire); CHECK(!(s.events & EVENT_SHOT));
		}
		logicUpdate(&s, &idle); CHECK(s.events & EVENT_SHOT);
	}
	/* Sustained taps emit precisely at eight-tick intervals. */
	tGameState s;
	start(&s); s.waveTimer = 60000;
	for(unsigned tick = 1; tick <= 40; ++tick) {
		logicUpdate(&s, tick & 1 ? &fire : &idle);
		CHECK(!!(s.events & EVENT_SHOT) == (tick % 8 == 2));
	}
}

static void testChargeCancellationAndUpgradeLifecycle(void) {
	for(unsigned bossMode = 0; bossMode < 2; ++bossMode)
		for(unsigned shotLevel = 0; shotLevel < 3; ++shotLevel) {
			tGameState s;
			start(&s); s.waveTimer = 60000;
			if(bossMode) { s.wave = g_stageWaveQuota[0]; arriveBoss(&s); }
			s.shotLevel = shotLevel; s.weaponLevel = 2;
			for(unsigned tick = 0; tick < 49; ++tick) logicUpdate(&s, &fire);
			s.invulnerable = 0;
			s.hostile[0] = entity(s.x + PLAYER_HIT_X, s.y + PLAYER_HIT_Y, 1);
			logicUpdate(&s, &fire);
			CHECK(s.phase == HERO_DYING && !s.charge && !s.fireCooldown);
			CHECK(s.shotLevel == (shotLevel ? shotLevel - 1 : 0) && s.weaponLevel == 1);
			finishDeath(&s); logicUpdate(&s, &idle);
			CHECK(!(s.events & (EVENT_SHOT | EVENT_LANCE)));
			for(unsigned i = 0; i < SHOT_COUNT; ++i) CHECK(!s.shots[i].active);
		}
	tGameState s;
	start(&s); s.waveTimer = 60000; s.shotLevel = 2;
	for(unsigned tick = 0; tick < 50; ++tick) logicUpdate(&s, &fire);
	s.wave = g_stageWaveQuota[0]; logicUpdate(&s, &idle);
	CHECK(s.phase == PLAY && !s.charge && (s.events & EVENT_LANCE));
	waitBossIntro(&s);
	CHECK(!s.charge && !(s.events & EVENT_SHOT));
	finishScene(&s); logicUpdate(&s, &idle);
	CHECK(s.shotLevel == 2 && !(s.events & EVENT_SHOT));
	/* Boss death also discards a held charge before the defeat scene. */
	s.boss.hp = 1;
	s.shots[0] = entity(s.boss.x + 8, s.boss.y + 8, 1);
	s.charge = 49; logicUpdate(&s, &fire);
	CHECK(s.phase == BOSS_DYING && !s.charge);
	finishDeath(&s); finishScene(&s); finishScene(&s);
	logicUpdate(&s, &idle);
	CHECK(s.phase == PLAY && s.level == 1 && s.shotLevel == 2 && !(s.events & EVENT_SHOT));
	/* A title/scene click alone never becomes a combat release shot. */
	logicInit(&s); logicUpdate(&s, &fire); logicScenePresented(&s, s.sceneEpoch);
	for(unsigned tick = 1; tick < SCENE_SKIP_FRAMES; ++tick) logicUpdate(&s, &idle);
	logicUpdate(&s, &fire); CHECK(s.phase == PLAY);
	logicUpdate(&s, &idle); CHECK(!s.charge && !(s.events & EVENT_SHOT));
}

static void testIndividualBulletChannelsAndDrops(void) {
	tGameState s;
	for(unsigned channel = 6; channel <= 7; ++channel) {
		start(&s); s.x = 100; s.y = 100; s.invulnerable = 0;
		s.hostile[0] = entity(112, 108, 1);
		s.hostile[0].visible = 0; s.hostile[0].channel = channel;
		logicUpdate(&s, &idle);
		CHECK(s.lives == 3 && s.hostile[0].visible && s.hostile[0].channel == channel);
		logicUpdate(&s, &idle);
		CHECK(s.lives == 2 && (s.events & EVENT_HIT));
		/* Each player bullet channel also collides against channel-4 enemies. */
		start(&s); s.enemies[0] = entity(200, 100, 1);
		s.shots[0] = entity(200, 100, 1);
		s.shots[0].visible = 0; s.shots[0].channel = channel;
		logicUpdate(&s, &idle);
		CHECK(s.shots[0].visible && !s.shots[0].channel && s.enemies[0].channel == 4);
		logicUpdate(&s, &idle);
		CHECK(s.score == 100 && !s.enemies[0].active && !s.shots[0].active);
	}
	/* A refused bullet crossing the core is discarded, never an invisible hit. */
	start(&s); s.x = 100; s.y = 100; s.invulnerable = 0;
	for(unsigned i = 0; i < 3; ++i) {
		s.hostile[i] = entity(i == 2 ? 112 : 240, 108, 1);
		s.hostile[i].visible = 0;
	}
	s.frame = HOSTILE_COUNT - 1;
	logicUpdate(&s, &idle);
	CHECK(s.hostile[0].visible && s.hostile[1].visible && !s.hostile[2].visible);
	CHECK(!s.hostile[2].active);
	CHECK(s.hostile[0].channel == 6 && s.hostile[1].channel == 7);
	logicUpdate(&s, &idle);
	CHECK(s.lives == 3 && !(s.events & EVENT_HIT));
	/* Shots never compete with hostile bullets: all twelve stay visible
	 * while only two bullets on one row can be shown, and the rest are refused. */
	start(&s);
	for(unsigned i = 0; i < SHOT_COUNT; ++i) s.shots[i] = entity(100, 100, 1);
	for(unsigned i = 0; i < HOSTILE_COUNT; ++i) s.hostile[i] = entity(240, 100, 1);
	logicUpdate(&s, &idle);
	unsigned shots = 0, hostile = 0;
	for(unsigned i = 0; i < SHOT_COUNT; ++i) shots += s.shots[i].visible;
	for(unsigned i = 0; i < HOSTILE_COUNT; ++i) hostile += s.hostile[i].active;
	CHECK(shots == SHOT_COUNT && hostile == 2);
	checkSchedule(&s);
}

/* Compare every simulation byte, including pool membership, cooldowns, wave
 * trackers, fractional motion, upgrades and retained death coordinates. */
static void checkFrozen(const tGameState *before, const tGameState *after) {
	tGameState normalized = *after;
	normalized.frame = before->frame;
	normalized.phaseFrame = before->phaseFrame;
	normalized.events = before->events;
	normalized.fireWasDown = before->fireWasDown;
	normalized.sceneReady = before->sceneReady;
	normalized.sceneArmed = before->sceneArmed;
	normalized.boss.flashTicks = before->boss.flashTicks;
	memcpy(normalized.effects, before->effects, sizeof(normalized.effects));
	CHECK(memcmp(before, &normalized, sizeof(normalized)) == 0);
}

static void testSceneHandshakeAndSkip(void) {
	tGameState s, snapshot;
	const tPhase scenes[] = {SECTOR_INTRO, BOSS_INTRO, CLEAR, WIN};
	CHECK(TITLE == 0 && PLAY == 1 && BOSS == 2 && CLEAR == 3 && GAMEOVER == 4 && WIN == 5);
	logicScenePresented(NULL, 0);
	CHECK(!logicCombatActive(NULL) && !logicWorldScrolling(NULL) && !logicHostileChannelMask(NULL));
	for(unsigned scene = 0; scene < 4; ++scene) {
		start(&s); s.phase = scenes[scene]; s.phaseFrame = 0;
		s.sceneReady = 0; s.sceneArmed = 0; s.sceneEpoch = 42;
		s.enemies[0] = entity(200, 100, 3); s.pickups[0] = entity(160, 180, 1);
		s.shots[0] = entity(100, 90, 1); s.hostile[0] = entity(180, 140, 1);
		s.boss.cooldown = 7; s.charge = 18; s.fireCooldown = 6;
		snapshot = s;
		for(unsigned tick = 0; tick < 200; ++tick) {
			logicScenePresented(&s, 41);
			logicUpdate(&s, tick & 1 ? &fire : &idle);
			checkFrozen(&snapshot, &s);
			CHECK(!s.phaseFrame && !s.sceneReady && !s.sceneArmed);
		}
		logicScenePresented(&s, 42);
		for(unsigned tick = 1; tick <= SCENE_SKIP_FRAMES; ++tick) {
			logicUpdate(&s, &fire); logicScenePresented(&s, 42);
			CHECK(s.phase == scenes[scene] && s.phaseFrame == tick && !s.sceneArmed);
		}
		logicUpdate(&s, &idle); CHECK(s.sceneArmed);
		logicUpdate(&s, &fire);
		CHECK(s.phase == (scene == 0 ? PLAY : scene == 1 ? BOSS : SECTOR_INTRO));
	}
	/* A press before tick 25 is consumed, never queued; release is required again. */
	logicInit(&s); logicUpdate(&s, &fire); logicScenePresented(&s, s.sceneEpoch);
	for(unsigned tick = 1; tick < 24; ++tick) logicUpdate(&s, &idle);
	logicUpdate(&s, &fire); CHECK(s.phase == SECTOR_INTRO && s.phaseFrame == 24);
	logicUpdate(&s, &fire); CHECK(s.phase == SECTOR_INTRO);
	logicUpdate(&s, &idle); logicUpdate(&s, &fire); CHECK(s.phase == PLAY);
	/* Exact earliest eligible edge. */
	logicInit(&s); logicUpdate(&s, &fire); logicScenePresented(&s, s.sceneEpoch);
	for(unsigned tick = 1; tick < SCENE_SKIP_FRAMES; ++tick) logicUpdate(&s, &idle);
	logicUpdate(&s, &fire); CHECK(s.phase == PLAY && !s.simFrame);
	/* Automatic dwell is 150 acknowledged ticks; holding fire never skips. */
	logicInit(&s); logicUpdate(&s, &fire); logicScenePresented(&s, s.sceneEpoch);
	for(unsigned tick = 1; tick < SCENE_FRAMES; ++tick) {
		logicUpdate(&s, &fire); CHECK(s.phase == SECTOR_INTRO && s.phaseFrame == tick);
	}
	logicUpdate(&s, &fire); CHECK(s.phase == PLAY && !s.simFrame && !s.charge);
	/* Restart preserves epoch and video time; stale completion cannot unlock it. */
	uint16_t oldEpoch = s.sceneEpoch;
	s.phase = GAMEOVER; s.phaseFrame = 0; returnToTitle(&s);
	uint32_t oldFrame = s.frame;
	logicUpdate(&s, &fire);
	CHECK(s.sceneEpoch == (uint16_t)(oldEpoch + 1) && s.frame == oldFrame + 1);
	logicScenePresented(&s, oldEpoch); CHECK(!s.sceneReady);
	s.phase = GAMEOVER; s.phaseFrame = 0; s.sceneEpoch = UINT16_MAX;
	returnToTitle(&s); logicUpdate(&s, &fire);
	CHECK(s.sceneEpoch == 0);
	logicScenePresented(&s, UINT16_MAX); CHECK(!s.sceneReady);
	logicScenePresented(&s, 0); CHECK(s.sceneReady);
}

static void testLiveOpeningAndFrozenLaterStories(void) {
	tGameState s, snapshot;
	const tInput flying = {1, 1, 1};
	logicInit(&s); logicUpdate(&s, &fire);
	logicSetPresentationBusy(&s, 1);
	logicScenePresented(&s, s.sceneEpoch);
	snapshot = s;
	for(unsigned tick = 0; tick < 20; ++tick) logicUpdate(&s, &flying);
	checkFrozen(&snapshot, &s);
	logicSetPresentationBusy(&s, 0);
	for(unsigned tick = 0; tick < 6; ++tick) logicUpdate(&s, &flying);
	CHECK(s.phase == SECTOR_INTRO && s.x == 41 && s.y == 135 && s.charge == 6);
	CHECK(!s.stageFrame && !s.simFrame && !s.wave && s.waveTimer == 25);
	CHECK(!enemyCount(&s) && !hostileCount(&s));
	logicUpdate(&s, &idle);
	CHECK((s.events & EVENT_SHOT) && s.shots[0].active);
	int16_t x = s.shots[0].x;
	logicUpdate(&s, &idle);
	CHECK(s.shots[0].x == x + 6 && !s.bossQuietTicks);
	/* Enemy spawning stays closed for the full acknowledged opening dwell. */
	while(s.phase == SECTOR_INTRO) {
		logicUpdate(&s, &idle);
		CHECK(!enemyCount(&s) && !hostileCount(&s) && s.waveTimer == 25);
	}
	for(unsigned tick = 1; tick < 25; ++tick) {
		logicUpdate(&s, &idle); CHECK(!enemyCount(&s));
	}
	logicUpdate(&s, &idle); CHECK(enemyCount(&s) == FORMATION_SIZE);
	const tPhase blocked[] = {CLEAR, WIN};
	for(unsigned i = 0; i < 2; ++i) {
		start(&s); s.phase = blocked[i]; s.sceneReady = 1; s.sceneArmed = 0;
		s.phaseFrame = 0; s.shots[0] = entity(100, 80, 1); s.shots[0].vx = 6;
		snapshot = s;
		for(unsigned tick = 0; tick < 40; ++tick) {
			logicUpdate(&s, &flying); checkFrozen(&snapshot, &s);
		}
	}
}

static void testLiveBossArrival(void) {
	const tInput flying = {-1, 1, 1}, right = {1, 0, 0};
	for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
		tGameState s, before;
		start(&s); s.level = level; s.x = 250; s.moveRemainderX = 1;
		s.wave = g_stageWaveQuota[level]; waitBossIntro(&s);
		CHECK(s.x == 120 && !s.moveRemainderX && !logicHostileChannelMask(&s));
		before = s;
		for(unsigned tick = 0; tick < 30; ++tick) logicUpdate(&s, &flying);
		checkFrozen(&before, &s);
		logicScenePresented(&s, s.sceneEpoch);
		logicSetPresentationBusy(&s, 1); before = s;
		for(unsigned tick = 0; tick < 30; ++tick) logicUpdate(&s, &flying);
		checkFrozen(&before, &s);
		logicSetPresentationBusy(&s, 0); before = s;
		for(unsigned tick = 0; tick < 6; ++tick) logicUpdate(&s, &flying);
		CHECK(s.x == 111 && s.y == before.y + 9 && s.charge == 6);
		logicUpdate(&s, &idle);
		CHECK((s.events & EVENT_SHOT) && s.shots[0].active);
		int16_t shotX = s.shots[0].x;
		logicUpdate(&s, &idle); CHECK(s.shots[0].x == shotX + 6);
		/* Even visible overlapping hostile/boss fixtures cannot collide here. */
		s.hostile[0] = entity(s.x, s.y, 1); s.hostile[0].vx = -4;
		tEntity hostile = s.hostile[0];
		for(unsigned tick = 0; tick < 20; ++tick) logicUpdate(&s, &right);
		CHECK(s.x == 120 && !s.moveRemainderX);
		CHECK(!memcmp(&s.hostile[0], &hostile, sizeof(hostile)));
		CHECK(!memcmp(&s.boss, &before.boss, sizeof(s.boss)));
		CHECK(s.simFrame == before.simFrame && s.stageFrame == before.stageFrame);
		CHECK(s.enemyMotionFrame == before.enemyMotionFrame && s.enemyAccumulator == before.enemyAccumulator);
		CHECK(s.invulnerable == before.invulnerable && s.lives == before.lives);
		CHECK(s.waveTimer == before.waveTimer && s.bossQuietTicks == before.bossQuietTicks);
		logicTogglePause(&s); before = s;
		for(unsigned tick = 0; tick < 60; ++tick) logicUpdate(&s, &flying);
		checkFrozen(&before, &s); CHECK(s.phaseFrame == before.phaseFrame);
		logicTogglePause(&s); logicUpdate(&s, &fire);
		CHECK(s.phase == BOSS_INTRO && !s.charge);
		logicUpdate(&s, &idle); CHECK(!(s.events & EVENT_SHOT));
		logicUpdate(&s, &fire);
		CHECK(s.phase == BOSS && !s.charge && logicHostileChannelMask(&s) == 0xf0);
		logicSetPresentationBusy(&s, 1); before = s;
		for(unsigned tick = 0; tick < 40; ++tick) logicUpdate(&s, &flying);
		checkFrozen(&before, &s);
		/* Natural dwell also clears charge without advancing the boss clock. */
		start(&s); s.level = level; s.wave = g_stageWaveQuota[level]; waitBossIntro(&s);
		logicScenePresented(&s, s.sceneEpoch); before = s;
		for(unsigned tick = 1; tick < SCENE_FRAMES; ++tick) {
			logicUpdate(&s, &fire); CHECK(s.phase == BOSS_INTRO && s.phaseFrame == tick);
		}
		logicUpdate(&s, &fire);
		CHECK(s.phase == BOSS && !s.charge && s.simFrame == before.simFrame);
		CHECK(!memcmp(&s.boss, &before.boss, sizeof(s.boss)));
	}
}

static void testThirteenStoryBeats(void) {
	tGameState s;
	logicInit(&s); logicUpdate(&s, &fire);
	unsigned seen = 0;
	for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
		CHECK(s.phase == SECTOR_INTRO && s.level == level && s.sceneId == seen++);
		CHECK(!s.sceneReady && !s.phaseFrame); finishScene(&s);
		s.wave = g_stageWaveQuota[level]; waitBossIntro(&s);
		CHECK(s.phase == BOSS_INTRO && s.sceneId == seen++);
		CHECK(!s.sceneReady && !s.phaseFrame); finishScene(&s);
		logicUpdate(&s, &idle); logicUpdate(&s, &idle);
		s.boss.hp = 1; s.shots[0] = entity(s.boss.x + 8, s.boss.y + 8, 1);
		logicUpdate(&s, &idle); CHECK(s.phase == BOSS_DYING);
		finishDeath(&s);
		CHECK(s.phase == CLEAR && s.sceneId == seen++);
		CHECK(!s.sceneReady && !s.phaseFrame); finishScene(&s);
	}
	CHECK(s.phase == WIN && s.sceneId == seen++ && seen == 13);
	CHECK(s.sceneEpoch == 13 && !s.sceneReady);
	finishScene(&s);
	for(unsigned tick = 0; tick < 200; ++tick) logicUpdate(&s, &idle);
	CHECK(s.phase == WIN && s.phaseFrame == SCENE_FRAMES);
}

static void testDeathSnapshotsAndMotionParity(void) {
	for(unsigned bossMode = 0; bossMode < 2; ++bossMode) {
		for(unsigned lastLife = 0; lastLife < 2; ++lastLife) {
			tGameState s, snapshot;
			start(&s);
			if(bossMode) { s.wave = g_stageWaveQuota[0]; arriveBoss(&s); logicUpdate(&s, &idle); }
			s.enemies[4] = entity(200, 180, 3); s.enemies[4].vx = -3;
			s.pickups[0] = entity(200, 160, 1); s.pickups[0].vx = -1;
			s.x = 80; s.y = 100; s.lives = lastLife ? 1 : 3; s.invulnerable = 0;
			s.weaponLevel = 2; s.speedLevel = 2;
			s.hostile[0] = entity(92, 108, 1);
			logicUpdate(&s, &idle);
			CHECK(s.phase == HERO_DYING && s.resumePhase == (bossMode ? BOSS : PLAY));
			CHECK(s.x == 80 && s.y == 100 && s.lives == (lastLife ? 0 : 2));
			CHECK(s.weaponLevel == 1 && s.speedLevel == 1 && !hostileCount(&s));
			CHECK(s.effects[6].kind == FX_HERO && s.effects[6].lifetime == 40);
			CHECK(s.effects[6].x == 80 && s.effects[6].y == 100 && !s.effects[6].age);
			snapshot = s;
			for(unsigned tick = 1; tick < HERO_DEATH_FRAMES; ++tick) {
				logicUpdate(&s, tick & 1 ? &fire : &idle); checkFrozen(&snapshot, &s);
				CHECK(s.effects[6].active && s.effects[6].age == tick);
				CHECK(!s.events && logicHostileChannelMask(&s) == (bossMode ? 0xf0 : 0xc0));
			}
			logicUpdate(&s, &fire);
			CHECK(!s.effects[6].active && s.simFrame == snapshot.simFrame);
			CHECK(s.phase == (lastLife ? GAMEOVER : bossMode ? BOSS : PLAY));
			if(!lastLife) {
				CHECK(s.x == 32 && s.y == 126 && s.invulnerable == RESPAWN_FRAMES);
				CHECK(!memcmp(s.enemies, snapshot.enemies, sizeof(s.enemies)));
				CHECK(!memcmp(s.pickups, snapshot.pickups, sizeof(s.pickups)));
			}
		}
	}
	/* Odd video pause must not flip the next half-step of any moving pool. */
	for(unsigned parity = 0; parity < 2; ++parity) {
		tGameState s, control;
		start(&s); s.waveTimer = 60000; s.simFrame = parity;
		s.enemies[0] = entity(240, 80, 2); s.enemies[0].vx = -3;
		s.hostile[0] = entity(240, 130, 1); s.hostile[0].vx = -3; s.hostile[0].vy = 1;
		s.pickups[0] = entity(240, 180, 1); s.pickups[0].vx = -1;
		control = s;
		s.phase = BOSS_INTRO; s.sceneReady = 0;
		for(unsigned tick = 0; tick < 51; ++tick) logicUpdate(&s, &idle);
		s.phase = PLAY;
		logicUpdate(&s, &idle); logicUpdate(&control, &idle);
		CHECK(!memcmp(s.enemies, control.enemies, sizeof(s.enemies)));
		CHECK(!memcmp(s.hostile, control.hostile, sizeof(s.hostile)));
		CHECK(!memcmp(s.pickups, control.pickups, sizeof(s.pickups)));
		CHECK(s.simFrame == control.simFrame && s.frame == control.frame + 51);
	}
}

static void testBossDamageVisibilityAndDeath(void) {
	for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
		tGameState s, snapshot;
		start(&s); s.level = level; s.wave = g_stageWaveQuota[level]; arriveBoss(&s);
		logicUpdate(&s, &idle);
		uint16_t hp = s.boss.hp;
		/* A hidden boss, then a hidden lance: neither may hit. */
		s.boss.visible = 0;
		s.shots[0] = entity(s.boss.x + 8, s.boss.y + 8, 6);
		logicUpdate(&s, &idle); CHECK(s.boss.hp == hp && !s.boss.flashTicks);
		s.shots[0].visible = 0;
		logicUpdate(&s, &idle); CHECK(s.boss.hp == hp && !s.boss.flashTicks);
		s.shots[0].visible = 1;
		logicUpdate(&s, &idle);
		CHECK(s.boss.hp == hp - 6 && s.boss.flashTicks == 6 && !s.shots[0].active);
		/* Flash never grants damage immunity, even to multiple shots in one tick. */
		for(unsigned i = 0; i < 2; ++i) s.shots[i] = entity(s.boss.x + 8, s.boss.y + 8, 1);
		logicUpdate(&s, &idle); CHECK(s.boss.hp == hp - 8 && s.boss.flashTicks == 6);
		for(unsigned tick = 1; tick <= 6; ++tick) {
			logicUpdate(&s, &idle); CHECK(s.boss.flashTicks == 6 - tick && s.boss.hp == hp - 8);
		}
		/* Lethal boss hit wins over simultaneous lethal hostile/core contact. */
		s.boss.hp = 1; s.invulnerable = 0; s.lives = 1;
		s.x = s.boss.x - 4; s.y = s.boss.y;
		s.shots[0] = entity(s.boss.x + 8, s.boss.y + 8, 6);
		s.hostile[0] = entity(s.x + PLAYER_HIT_X, s.y + PLAYER_HIT_Y, 1);
		s.pickups[0] = entity(100, 180, 1); s.pickups[0].vx = -1;
		logicUpdate(&s, &idle);
		CHECK(s.phase == BOSS_DYING && s.lives == 1 && !s.boss.active && !s.boss.visible);
		CHECK(s.effects[7].active && s.effects[7].kind == FX_BOSS && s.effects[7].lifetime == 75);
		CHECK(s.effects[7].x == s.boss.x && s.effects[7].y == s.boss.y);
		CHECK(s.score == 2000 + 1000 * level && !hostileCount(&s));
		snapshot = s;
		for(unsigned tick = 1; tick < BOSS_DEATH_FRAMES; ++tick) {
			logicUpdate(&s, tick & 1 ? &fire : &idle); checkFrozen(&snapshot, &s);
			CHECK(s.effects[7].active && s.effects[7].age == tick && !s.events);
		}
		logicUpdate(&s, &fire);
		CHECK(s.phase == CLEAR && !s.effects[7].active && !s.sceneReady && !s.phaseFrame);
		CHECK(s.score == snapshot.score && s.simFrame == snapshot.simFrame);
	}
}

static void testBossGeometryEdges(void) {
	/* Predict just one movement tick to position exact rectangle-edge probes. */
	for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
		/* BOB visibility gates body contact as well as shot damage. */
		tGameState hidden;
		start(&hidden); hidden.level = level; hidden.wave = g_stageWaveQuota[level]; arriveBoss(&hidden);
		logicUpdate(&hidden, &idle);
		hidden.x = hidden.boss.x - 4; hidden.y = hidden.boss.y;
		hidden.invulnerable = 0; hidden.boss.visible = 0;
		logicUpdate(&hidden, &idle); CHECK(hidden.lives == 3 && hidden.boss.visible);
		logicUpdate(&hidden, &idle); CHECK(hidden.lives == 2 && hidden.phase == HERO_DYING);
		for(unsigned edge = 0; edge < 8; ++edge) {
			for(unsigned hero = 0; hero < 2; ++hero) {
				tGameState s, next;
				start(&s); s.level = level; s.wave = g_stageWaveQuota[level]; arriveBoss(&s);
				/* Interior patrol positions make all eight core probes legal. */
				s.boss.tick = level == 2 ? 100 : 400; s.boss.x = 200;
				logicUpdate(&s, &idle); next = s; logicUpdate(&next, &idle);
				int w = hero ? PLAYER_HIT_W : SHOT_W, h = hero ? PLAYER_HIT_H : SHOT_H;
				int x = next.boss.x + 8, y = next.boss.y + 8;
				if(edge < 2) x = next.boss.x - w + edge;
				else if(edge < 4) x = next.boss.x + BOSS_W - (edge == 3);
				else if(edge < 6) y = next.boss.y - h + (edge == 5);
				else y = next.boss.y + BOSS_H - (edge == 7);
				/* Top-edge shots outside the play corridor are intentionally invalid. */
				unsigned hit = edge & 1;
				if(hero) {
					s.x = x - PLAYER_HIT_X; s.y = y - PLAYER_HIT_Y; s.invulnerable = 0;
					CHECK(s.x >= 0 && s.x <= WORLD_W - PLAYER_W && s.y >= PLAY_TOP && s.y <= PLAY_BOTTOM - PLAYER_H);
				}
				else {
					s.shots[0] = entity(x, y, 1);
					if(y < PLAY_TOP || y + h > PLAY_BOTTOM) hit = 0;
				}
				uint16_t hp = s.boss.hp;
				logicUpdate(&s, &idle);
				if(hero) CHECK(s.lives == 3 - hit);
				else CHECK(s.boss.hp == hp - hit);
			}
		}
	}
}

static void testEffectCapacityAndExpiry(void) {
	tGameState s;
	start(&s); s.waveTimer = 60000;
	for(unsigned i = 0; i < 6; ++i) {
		s.enemies[i] = entity(200, 60 + i * 27, 1);
		s.enemies[i].kind = i & 1 ? ENEMY_ASTEROID : ENEMY_SCOUT;
		s.shots[i] = entity(200, 60 + i * 27, 6);
	}
	logicUpdate(&s, &idle);
	for(unsigned i = 0; i < 6; ++i) {
		CHECK(s.effects[i].active && !s.effects[i].age && s.effects[i].lifetime == 16);
		CHECK(s.effects[i].kind == (i & 1 ? FX_ASTEROID : FX_ENEMY));
		CHECK(s.effects[i].x == 200 && s.effects[i].y == 60 + (int)i * 27);
	}
	CHECK(!s.effects[6].active && !s.effects[7].active);
	/* Replace oldest small effect only; reserved effects cannot be displaced. */
	s.effects[3].age = 5;
	s.effects[6] = (tEffect){80, 100, 1, FX_HERO, 0, 40};
	s.effects[7] = (tEffect){200, 80, 1, FX_BOSS, 0, 75};
	s.enemies[0] = entity(180, 100, 1); s.shots[0] = entity(180, 100, 1);
	logicUpdate(&s, &idle);
	CHECK(s.effects[3].x == 180 && !s.effects[3].age);
	CHECK(s.effects[6].x == 80 && s.effects[7].x == 200);
	s.phase = BOSS_INTRO; s.sceneReady = 0;
	for(unsigned tick = 1; tick <= 16; ++tick) {
		logicUpdate(&s, &idle);
		CHECK(s.effects[3].active == (tick < 16));
		CHECK(s.effects[6].active && s.effects[7].active);
	}
	for(unsigned i = 0; i < 6; ++i) CHECK(!s.effects[i].active);
}

static void testFourHostileChannels(void) {
	tGameState s;
	for(unsigned phase = TITLE; phase <= HERO_DYING; ++phase) {
		for(unsigned resume = PLAY; resume <= BOSS; ++resume) {
			start(&s); s.phase = (tPhase)phase; s.resumePhase = (tPhase)resume;
			unsigned owner = phase == HERO_DYING ? resume : phase;
			CHECK(logicHostileChannelMask(&s) == (owner == PLAY ? 0xc0 : owner == BOSS ? 0xf0 : 0));
			CHECK(logicCombatActive(&s) == (phase == PLAY || phase == BOSS));
			CHECK(logicWorldScrolling(&s) == (phase == PLAY));
		}
	}
	for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
		start(&s); s.level = level; s.wave = g_stageWaveQuota[level]; arriveBoss(&s);
		for(unsigned i = 0; i < 5; ++i) {
			s.hostile[i] = entity(200, 130, 1); s.hostile[i].kind = level;
		}
		logicUpdate(&s, &idle);
		for(unsigned i = 0; i < 4; ++i) CHECK(s.hostile[i].active && s.hostile[i].channel == 4 + i);
		CHECK(!s.hostile[4].active && !s.hostile[4].visible); checkSchedule(&s);
		/* The same four rays retain ownership for their entire trajectory. */
		for(unsigned i = 0; i < 4; ++i) s.hostile[i].vx = HOSTILE_VX;
		for(unsigned tick = 0; tick < 140; ++tick) {
			s.boss.cooldown = 2; s.invulnerable = 2; logicUpdate(&s, &idle); checkSchedule(&s);
			for(unsigned i = 0; i < 4; ++i) if(s.hostile[i].active) CHECK(s.hostile[i].channel == 4 + i);
		}
		/* Full 32-bit pool, eight disjoint rows on each channel. */
		memset(s.hostile, 0, sizeof(s.hostile));
		for(unsigned i = 0; i < HOSTILE_COUNT; ++i) s.hostile[i] = entity(200, 60 + (i / 4) * 18, 1);
		logicUpdate(&s, &idle); CHECK(hostileCount(&s) == 32); checkSchedule(&s);
		uint32_t membership[4] = {0};
		for(unsigned i = 0; i < HOSTILE_COUNT; ++i) membership[s.hostile[i].channel - 4] |= UINT32_C(1) << i;
		CHECK((membership[0] | membership[1] | membership[2] | membership[3]) == UINT32_MAX);
		for(unsigned i = 0; i < 4; ++i) for(unsigned j = i + 1; j < 4; ++j) CHECK(!(membership[i] & membership[j]));
	}
	/* Exhaust vertical admission boundaries across all four channels. */
	for(int y = PLAY_TOP; y <= PLAY_BOTTOM - HOSTILE_H; ++y) {
		start(&s); s.wave = g_stageWaveQuota[0]; arriveBoss(&s);
		for(unsigned i = 0; i < 4; ++i) {
			s.hostile[i] = entity(240, 120, 1); s.hostile[i].channel = 4 + i;
		}
		s.hostile[4] = entity(200, y, 1); logicUpdate(&s, &idle);
		unsigned fits = y >= 120 + HOSTILE_H + HOSTILE_GAP || y + HOSTILE_H + HOSTILE_GAP <= 120;
		CHECK(s.hostile[4].active == fits); checkSchedule(&s);
	}
	/* Converging rays cannot borrow any occupied channel, in either parity. */
	for(unsigned parity = 0; parity < 2; ++parity) {
		start(&s); s.wave = g_stageWaveQuota[0]; arriveBoss(&s); s.simFrame = parity;
		for(unsigned i = 0; i < 4; ++i) {
			s.hostile[i] = entity(240, 100, 1); s.hostile[i].channel = 4 + i;
		}
		s.hostile[4] = entity(240, 160, 1); s.hostile[4].vy = -2;
		logicUpdate(&s, &idle); CHECK(!s.hostile[4].active);
	}
	/* Repeated real volleys exercise admission against surviving earlier fans. */
	for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
		unsigned used = 0;
		start(&s); s.level = level; s.wave = g_stageWaveQuota[level]; arriveBoss(&s);
		for(unsigned tick = 0; tick < 2048; ++tick) {
			s.invulnerable = 2; logicUpdate(&s, &idle); checkSchedule(&s);
			for(unsigned i = 0; i < HOSTILE_COUNT; ++i)
				if(s.hostile[i].active) used |= 1u << s.hostile[i].channel;
		}
		CHECK(used == 0xf0);
	}
	/* Palette/kind is irrelevant to collision: each borrowed channel honors
	 * renderer visibility, then damages exactly once when actually shown. */
	for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
		for(unsigned channel = 4; channel <= 7; ++channel) {
			start(&s); s.level = level; s.wave = g_stageWaveQuota[level]; arriveBoss(&s);
			s.invulnerable = 0; s.hostile[0] = entity(s.x + PLAYER_HIT_X, s.y + PLAYER_HIT_Y, 1);
			s.hostile[0].kind = level; s.hostile[0].channel = channel; s.hostile[0].visible = 0;
			logicUpdate(&s, &idle); CHECK(s.lives == 3 && s.hostile[0].visible);
			CHECK(s.hostile[0].channel == channel);
			logicUpdate(&s, &idle); CHECK(s.phase == HERO_DYING && s.lives == 2 && !hostileCount(&s));
			CHECK(logicHostileChannelMask(&s) == 0xf0);
		}
	}
}

static void testGameoverReadyTimeoutAndHeldInput(void) {
	tGameState s, snapshot;
	tInput held = {1, 0, 1};
	start(&s); s.level = 3; s.lives = 1; s.invulnerable = 0;
	s.score = 1234; s.weaponLevel = s.shotLevel = s.speedLevel = 2;
	s.hostile[0] = entity(s.x + PLAYER_HIT_X, s.y + PLAYER_HIT_Y, 1);
	logicUpdate(&s, &held);
	CHECK(s.phase == HERO_DYING && !s.lives);
	snapshot = s;
	for(unsigned tick = 1; tick < HERO_DEATH_FRAMES; ++tick) {
		logicUpdate(&s, &held); CHECK(s.phase == HERO_DYING);
		checkFrozen(&snapshot, &s);
	}
	logicUpdate(&s, &held);
	CHECK(s.phase == GAMEOVER && s.presentationBusy && !s.phaseFrame);
	snapshot = s;
	for(unsigned tick = 0; tick < 200; ++tick) {
		logicUpdate(&s, tick & 1 ? &held : &idle);
		checkFrozen(&snapshot, &s);
		CHECK(!s.phaseFrame && !s.sceneArmed);
	}
	logicSetPresentationBusy(&s, 0);
	for(unsigned tick = 1; tick < GAMEOVER_FRAMES; ++tick) {
		logicUpdate(&s, &held);
		CHECK(s.phase == GAMEOVER && s.phaseFrame == tick);
	}
	logicUpdate(&s, &held);
	CHECK(s.phase == TITLE && s.titleInputBlocked && s.presentationBusy);
	CHECK(!s.level && s.lives == 3 && !s.score && !s.weaponLevel && !s.shotLevel);
	CHECK(!s.speedLevel && !s.shield && !s.bonusCycle && !s.charge && !s.wave);
	CHECK(!enemyCount(&s) && !hostileCount(&s) && !s.boss.active);
	for(unsigned i = 0; i < SHOT_COUNT; ++i) CHECK(!s.shots[i].active);
	for(unsigned i = 0; i < BONUS_COUNT; ++i) CHECK(!s.pickups[i].active);
	for(unsigned i = 0; i < EFFECT_COUNT; ++i) CHECK(!s.effects[i].active);
	CHECK(s.frame == snapshot.frame + 200 + GAMEOVER_FRAMES);
	CHECK(s.simFrame == snapshot.simFrame && s.sceneEpoch == snapshot.sceneEpoch);
	CHECK(s.enemyMotionFrame == snapshot.enemyMotionFrame && s.enemyAccumulator == snapshot.enemyAccumulator);
	/* An idle tick during composition does not arm the returned title. */
	logicUpdate(&s, &idle); CHECK(s.titleInputBlocked);
	for(unsigned tick = 0; tick < 200; ++tick) logicUpdate(&s, &held);
	logicSetPresentationBusy(&s, 0);
	for(unsigned tick = 0; tick < 200; ++tick) logicUpdate(&s, &held);
	CHECK(s.phase == TITLE && s.titleInputBlocked && !s.level);
	tInput directionOnly = {1, 0, 0};
	logicUpdate(&s, &directionOnly);
	CHECK(!s.titleInputBlocked && !s.level);
	logicUpdate(&s, &held);
	CHECK(s.phase == SECTOR_INTRO && !s.level && !s.charge);
	CHECK(s.sceneEpoch == (uint16_t)(snapshot.sceneEpoch + 1));
	CHECK(s.enemyMotionFrame == snapshot.enemyMotionFrame && s.enemyAccumulator == snapshot.enemyAccumulator);
}

static void testGameoverSkipBoundary(void) {
	for(unsigned pressTick = 24; pressTick <= 25; ++pressTick) {
		tGameState s;
		logicInit(&s); s.phase = GAMEOVER; s.lives = 0;
		for(unsigned tick = 1; tick < pressTick; ++tick) logicUpdate(&s, &idle);
		logicUpdate(&s, &fire);
		CHECK(s.phase == (pressTick == 25 ? TITLE : GAMEOVER));
		if(pressTick == 24) {
			logicUpdate(&s, &fire); CHECK(s.phase == GAMEOVER);
			logicUpdate(&s, &idle); logicUpdate(&s, &fire);
			CHECK(s.phase == TITLE && s.titleInputBlocked);
		}
	}
	/* Ordinary initial title/sector selection can still start during composition. */
	tGameState s;
	tInput right = {1, 0, 0};
	logicInit(&s); logicSetPresentationBusy(&s, 1);
	logicUpdate(&s, &right); logicUpdate(&s, &fire);
	CHECK(s.phase == SECTOR_INTRO && s.level == 1);
}

static void testExactEnemyClockAndUnchangedProjectiles(void) {
	const unsigned rates[] = {16, 17, 18, 20};
	for(unsigned level = 0; level < LEVEL_COUNT; ++level)
	for(unsigned accumulator = 0; accumulator < 20; ++accumulator)
		for(unsigned parity = 0; parity < 2; ++parity) {
			tGameState s;
			start(&s); s.level = level; s.waveTimer = 60000;
			s.enemyAccumulator = accumulator; s.enemyMotionFrame = parity;
			s.simFrame = parity; s.invulnerable = 60000;
			s.enemies[0] = entity(300, 80, 1); s.enemies[0].vx = -2;
			s.enemies[1] = entity(300, 130, 1); s.enemies[1].vx = -3;
			s.enemies[1].kind = ENEMY_DART;
			s.enemies[2] = entity(300, 180, 1); s.enemies[2].vx = -2;
			s.enemies[2].kind = ENEMY_ASTEROID;
			for(unsigned tick = 1; tick <= 200; ++tick) {
				logicUpdate(&s, &idle);
				unsigned steps = (accumulator + rates[level] * tick) / 20;
				int oddSteps = (steps + (parity == 0)) / 2;
				CHECK(s.enemyMotionFrame == parity + steps && s.simFrame == parity + tick);
				CHECK(s.enemies[0].age == steps && s.enemies[1].age == steps);
				CHECK(s.enemies[0].x == 300 - (int)steps);
				CHECK(s.enemies[1].x == 300 - (int)steps - oddSteps);
				CHECK(s.enemies[2].x == s.enemies[0].x);
				if(tick % 40 == 0) {
					CHECK(s.enemies[0].x == 300 - (int)(tick * rates[level] / 20));
					CHECK(s.enemies[1].x == 300 - (int)(tick * rates[level] * 3 / 40));
				}
			}
		}
	for(int sign = -1; sign <= 1; sign += 2) {
		tGameState s;
		tInput move = {1, 0, 1};
		start(&s); s.waveTimer = 60000; s.simFrame = 0;
		s.enemyAccumulator = 0; s.enemyMotionFrame = 0;
		s.enemies[0] = entity(280, 100, 1); s.enemies[0].kind = ENEMY_WEAVER;
		s.enemies[0].age = sign < 0 ? 32 : 0;
		s.hostile[0] = entity(240, 170, 1); s.hostile[0].vx = -3; s.hostile[0].vy = sign;
		s.shots[0] = entity(60, 60, 1); s.shots[0].vx = 6;
		s.shots[1] = entity(60, 80, 6); s.shots[1].kind = SHOT_CHARGED; s.shots[1].vx = 4;
		s.pickups[0] = entity(240, 200, 1); s.pickups[0].vx = -1;
		for(unsigned tick = 1; tick <= 10; ++tick) {
			logicUpdate(&s, &move);
			CHECK(s.x == 32 + (int)(tick * 3 / 2) && s.charge == tick);
			CHECK(s.shots[0].x == 60 + (int)tick * 6 && s.shots[1].x == 60 + (int)tick * 4);
			CHECK(s.hostile[0].x == 240 - (int)((tick * 3 + 1) / 2));
			CHECK(s.hostile[0].y == 170 + sign * (int)((tick + 1) / 2));
			CHECK(s.pickups[0].x == 240 - (int)((tick + 1) / 2) && s.pickups[0].age == tick);
			if(tick == 5 || tick == 10) CHECK(s.enemies[0].y == 100 + sign * (int)(tick * 2 / 5));
		}
	}
}

static void testSectorEnemyCadences(void) {
	const unsigned intervals[] = {96, 76, 64, 52};
	const unsigned rays[] = {3, 5, 5, 7};
	for(unsigned level = 0; level < LEVEL_COUNT; ++level)
		for(unsigned member = 0; member < FORMATION_SIZE; ++member) {
			tGameState s;
			start(&s); s.level = level; s.waveTimer = 60000;
			s.enemyAccumulator = 0; s.enemyMotionFrame = 0;
			s.enemies[0] = entity(240, 120, 1); s.enemies[0].waveMember = member;
			s.enemies[0].fireCountdown = 50 + 10 * member;
			unsigned volleys = 0;
			for(unsigned tick = 1; tick <= 800; ++tick) {
				unsigned first = 50 + 10 * member;
				memset(s.hostile, 0, sizeof(s.hostile));
				logicUpdate(&s, &idle);
				unsigned due = tick >= first && (tick - first) % intervals[level] == 0;
				CHECK(hostileCount(&s) == (due ? rays[level] : 0));
				volleys += !!hostileCount(&s);
			}
			CHECK(volleys == 1 + (800 - 50 - member * 10) / intervals[level]);
		}
}

static void testEnemyClockPreparingFreeze(void) {
	for(unsigned mode = 0; mode < 2; ++mode) {
		tGameState s, snapshot;
		start(&s); s.waveTimer = 60000;
		if(mode) { s.wave = g_stageWaveQuota[0]; arriveBoss(&s); }
		else s.enemies[0] = entity(240, 120, 1);
		s.enemyMotionFrame = 123; s.enemyAccumulator = 12;
		logicSetPresentationBusy(&s, 1); snapshot = s;
		for(unsigned tick = 0; tick < 51; ++tick) {
			logicUpdate(&s, &fire); checkFrozen(&snapshot, &s);
		}
		logicSetPresentationBusy(&s, 0); logicUpdate(&s, &idle);
		CHECK(s.enemyMotionFrame == 124 && s.enemyAccumulator == 8);
		CHECK(s.simFrame == snapshot.simFrame + 1);
	}
}

static void testIndependentFireAndSectorFans(void) {
	const unsigned rays[4][2] = {{3, 5}, {5, 5}, {5, 7}, {7, 7}};
	const unsigned intervals[] = {96, 76, 64, 52};
	for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
		for(unsigned gunner = 0; gunner < 2; ++gunner)
			for(int y = PLAY_TOP; y <= PLAY_BOTTOM - ENEMY_H; y += 12) {
				tGameState s;
				start(&s); s.level = level; s.waveTimer = 60000;
				s.enemyAccumulator = 0; s.enemyMotionFrame = 0;
				s.enemies[0] = entity(240, y, gunner ? 3 : 1);
				s.enemies[0].kind = gunner ? ENEMY_GUNNER : ENEMY_SCOUT;
				s.enemies[0].fireCountdown = 1;
				logicUpdate(&s, &idle);
				CHECK(s.enemyMotionFrame == (level == 3));
				CHECK(s.enemies[0].fireCountdown == intervals[level]);
				int delta = s.y + PLAYER_H / 2 - y;
				checkEmptyFan(&s, 240, y + 4, rays[level][gunner], delta < 0 ? -1 : delta > 0);
				CHECK(hostileCount(&s) > 0); checkSchedule(&s);
				/* No backlog when visibility rejects a scheduled volley. */
				memset(s.hostile, 0, sizeof(s.hostile));
				s.enemies[0].visible = 0; s.enemies[0].fireCountdown = 1;
				logicUpdate(&s, &idle); CHECK(!hostileCount(&s));
				CHECK(s.enemies[0].fireCountdown == intervals[level]);
				logicUpdate(&s, &idle); CHECK(!hostileCount(&s));
			}
		/* Boss fire is also due on a skipped motion tick, with no repeat. */
		tGameState s;
		start(&s); s.level = level; s.wave = g_stageWaveQuota[level]; arriveBoss(&s);
		s.enemyAccumulator = 0; s.boss.cooldown = 1; s.boss.tick = 70;
		logicUpdate(&s, &idle); CHECK(hostileCount(&s) > 0);
		CHECK(s.boss.tick == 70 + (level == 3));
		memset(s.hostile, 0, sizeof(s.hostile));
		logicUpdate(&s, &idle); CHECK(!hostileCount(&s));
	}
}

static void testOrdinaryHealthAndSpawnDelays(void) {
	for(unsigned level = 0; level < LEVEL_COUNT; ++level)
		for(unsigned wave = 0; wave < 5; ++wave) {
			tGameState s;
			start(&s); s.level = level; s.wave = wave; s.waveTimer = 1;
			logicUpdate(&s, &idle);
			for(unsigned member = 0; member < FORMATION_SIZE; ++member) {
				const tEntity *e = &s.enemies[member];
				CHECK(e->hp == (e->kind == ENEMY_GUNNER || e->kind == ENEMY_ASTEROID ? 3 : 1));
				/* Spawn update is the first combat tick of the initial delay. */
				CHECK(e->fireCountdown == 49 + 10 * member);
			}
		}
}

static void testBossQuietBoundaryAndRelease(void) {
	tGameState s;
	start(&s); s.wave = g_stageWaveQuota[0];
	uint32_t sim = s.simFrame;
	uint16_t stage = s.stageFrame;
	const tInput right = {1, 0, 0};
	for(unsigned tick = 1; tick < BOSS_QUIET_FRAMES; ++tick) {
		logicUpdate(&s, &right);
		CHECK(s.phase == PLAY && s.bossQuietTicks == tick);
		CHECK(!enemyCount(&s) && s.wave == g_stageWaveQuota[0]);
	}
	CHECK(s.x > 32 && s.simFrame == sim + 49 && s.stageFrame == stage + 49);
	/* A fresh release on the boundary wins over boss entry, even when its
	 * muzzle is offscreen and the projectile retires in the same update. */
	s.x = WORLD_W - PLAYER_W; s.charge = 1;
	logicUpdate(&s, &idle);
	CHECK(s.phase == PLAY && !s.bossQuietTicks && (s.events & EVENT_SHOT));
	for(unsigned tick = 1; tick < BOSS_QUIET_FRAMES; ++tick) {
		logicUpdate(&s, &idle);
		CHECK(s.phase == PLAY && s.bossQuietTicks == tick);
	}
	logicUpdate(&s, &idle);
	CHECK(s.phase == BOSS_INTRO && s.boss.hp == 216);
}

static void testBossProjectileDrainAndPause(void) {
	for(unsigned hostile = 0; hostile < 2; ++hostile) {
		tGameState s;
		start(&s); s.wave = g_stageWaveQuota[0]; s.bossQuietTicks = 23;
		tEntity *projectile = hostile ? &s.hostile[HOSTILE_COUNT - 1] : &s.shots[SHOT_COUNT - 1];
		*projectile = entity(200, 70, 1); projectile->visible = 0;
		for(unsigned tick = 0; tick < 60; ++tick) {
			logicUpdate(&s, &idle);
			CHECK(s.phase == PLAY && !s.bossQuietTicks && projectile->active);
		}
		projectile->x = hostile ? -HOSTILE_W : WORLD_W;
		logicUpdate(&s, &idle);
		CHECK(!projectile->active && !s.bossQuietTicks && s.phase == PLAY);
		for(unsigned tick = 0; tick < 17; ++tick) logicUpdate(&s, &idle);
		CHECK(s.bossQuietTicks == 17);
		logicSetPresentationBusy(&s, 1);
		uint32_t sim = s.simFrame;
		for(unsigned tick = 0; tick < 60; ++tick) logicUpdate(&s, &fire);
		CHECK(s.bossQuietTicks == 17 && s.simFrame == sim && !s.charge);
		logicSetPresentationBusy(&s, 0);
		/* Lethal collision takes precedence, then all 40 death ticks freeze. */
		s.invulnerable = 0;
		s.hostile[0] = entity(s.x + PLAYER_HIT_X, s.y + PLAYER_HIT_Y, 1);
		logicUpdate(&s, &idle);
		CHECK(s.phase == HERO_DYING && s.bossQuietTicks == 17);
		finishDeath(&s);
		CHECK(s.phase == PLAY && s.bossQuietTicks == 17);
		for(unsigned tick = 18; tick < BOSS_QUIET_FRAMES; ++tick) {
			logicUpdate(&s, &idle);
			CHECK(s.phase == PLAY && s.bossQuietTicks == tick);
		}
		logicUpdate(&s, &idle); CHECK(s.phase == BOSS_INTRO);
	}
}

static void testBossFinalRetirementStartsQuietInterval(void) {
	for(unsigned kill = 0; kill < 2; ++kill) {
		tGameState s;
		start(&s); s.wave = g_stageWaveQuota[0];
		s.enemies[0] = entity(kill ? 200 : -ENEMY_W, 80, 1);
		s.enemies[0].waveId = 1;
		s.waves[0].planned = s.waves[0].spawned = FORMATION_SIZE;
		s.waves[0].remaining = 1; s.waves[0].killed = FORMATION_SIZE - 1;
		if(kill) s.shots[0] = entity(200, 80, 1);
		logicUpdate(&s, &idle);
		CHECK(s.phase == PLAY && !enemyCount(&s) && !s.bossQuietTicks);
		CHECK(!s.waves[0].remaining && s.waves[0].failed == !kill);
		CHECK(!!(s.events & EVENT_BONUS_DROP) == kill);
		for(unsigned tick = 1; tick < BOSS_QUIET_FRAMES; ++tick) {
			logicUpdate(&s, &idle);
			CHECK(s.phase == PLAY && s.bossQuietTicks == tick);
		}
		logicUpdate(&s, &idle); CHECK(s.phase == BOSS_INTRO);
	}
}

static void testPreferredSpritePairs(void) {
	tGameState s;
	start(&s); s.waveTimer = 60000;
	s.hostile[0] = entity(240, 100, 1); s.hostile[0].channel = 6;
	s.hostile[1] = entity(240, 120, 1); s.hostile[1].channel = 7;
	for(unsigned tick = 0; tick < HOSTILE_COUNT; ++tick) {
		logicUpdate(&s, &idle);
		CHECK(s.hostile[0].visible && s.hostile[0].channel == 6);
		CHECK(s.hostile[1].visible && s.hostile[1].channel == 7);
		checkSchedule(&s);
	}
}
static void testManualPauseAllPhases(void) {
	const tPhase phases[] = {PLAY, BOSS, SECTOR_INTRO, BOSS_INTRO, BOSS_DYING, CLEAR, WIN, HERO_DYING};
	const tInput flying = {1, 1, 1};
	for(unsigned i = 0; i < sizeof(phases) / sizeof(*phases); ++i) {
		tGameState s, before, actual;
		start(&s); s.phase = phases[i]; s.sceneReady = 1; s.phaseFrame = 10;
		s.charge = 49; s.fireCooldown = 5; s.bossQuietTicks = 17;
		s.enemies[0] = entity(200, 80, 2); s.hostile[0] = entity(200, 140, 1);
		s.shots[0] = entity(100, 90, 1); s.pickups[0] = entity(200, 180, 1);
		s.effects[0] = (tEffect){80, 80, 1, FX_ENEMY, 0, SMALL_EFFECT_FRAMES};
		s.boss.flashTicks = 6;
		logicTogglePause(&s);
		CHECK(s.manualPause && !s.charge && s.pauseFireBlocked && !logicWorldScrolling(&s));
		before = s;
		for(unsigned tick = 0; tick < 101; ++tick) {
			logicUpdate(&s, tick & 1 ? &idle : &flying);
			actual = s;
			actual.frame = before.frame; actual.events = before.events;
			actual.fireWasDown = before.fireWasDown;
			actual.boss.flashTicks = before.boss.flashTicks;
			memcpy(actual.effects, before.effects, sizeof(actual.effects));
			CHECK(!memcmp(&actual, &before, sizeof(actual)));
			CHECK(heroPresentationVisible(&s) == (phases[i] != HERO_DYING && phases[i] != WIN));
		}
		CHECK(s.frame == before.frame + 101 && !s.effects[0].active && !s.boss.flashTicks);
		logicTogglePause(&s); CHECK(!s.manualPause);
		logicUpdate(&s, &fire);
		CHECK(!s.charge && !(s.events & (EVENT_SHOT | EVENT_LANCE)));
		CHECK(s.phase == phases[i]);
		logicUpdate(&s, &idle); CHECK(!s.pauseFireBlocked);
	}
	tGameState s;
	logicInit(&s); logicTogglePause(&s); CHECK(!s.manualPause);
	s.phase = GAMEOVER; logicTogglePause(&s); CHECK(!s.manualPause);
	s.phase = PLAY; logicTogglePause(&s); logicInit(&s);
	CHECK(!s.manualPause && !s.pauseFireBlocked);
	logicTogglePause(NULL);
}

static void testPauseChargeAndHeroContinuity(void) {
	tGameState s;
	start(&s); s.waveTimer = 60000;
	for(unsigned i = 0; i < 50; ++i) logicUpdate(&s, &fire);
	logicTogglePause(&s); logicUpdate(&s, &idle); logicTogglePause(&s);
	for(unsigned i = 0; i < 60; ++i) logicUpdate(&s, &fire);
	CHECK(!s.charge && !s.shots[0].active);
	logicUpdate(&s, &idle); logicUpdate(&s, &fire); logicUpdate(&s, &idle);
	CHECK(s.events & EVENT_SHOT);
	logicInit(&s); logicUpdate(&s, &fire);
	s.presentationBusy = 1;
	CHECK(!s.sceneReady && heroPresentationVisible(&s));
	CHECK(!s.heroBlink && s.invulnerable == RESPAWN_FRAMES);
	s.presentationBusy = 0; logicScenePresented(&s, s.sceneEpoch);
	s.x = 119;
	const tInput right = {1, 0, 0};
	logicUpdate(&s, &right); CHECK(s.x == 120 && heroPresentationX(&s) == 120);
	s.phaseFrame = SCENE_FRAMES - 1;
	logicUpdate(&s, &idle); CHECK(s.phase == PLAY);
	s.presentationBusy = 1;
	for(unsigned i = 0; i < 35; ++i) {
		logicUpdate(&s, &right);
		CHECK(s.x == 120 && heroPresentationVisible(&s));
	}
	s.presentationBusy = 0;
	for(unsigned i = 0; i < RESPAWN_FRAMES; ++i) {
		logicUpdate(&s, &idle); CHECK(heroPresentationVisible(&s));
	}
	s.heroBlink = 1; s.invulnerable = 4; CHECK(!heroPresentationVisible(&s));
	const tPhase stories[] = {BOSS_INTRO, BOSS_DYING, CLEAR, WIN};
	for(unsigned i = 0; i < 4; ++i) {
		s.phase = stories[i]; s.phaseFrame = 0; s.sceneReady = 0; s.x = 200;
		logicUpdate(&s, &right);
		CHECK(s.x == 200 && heroPresentationVisible(&s) == (stories[i] != WIN));
		CHECK(heroPresentationX(&s) == (stories[i] == BOSS_DYING || stories[i] == WIN ? 200 : 120));
	}
	s.phase = HERO_DYING; CHECK(!heroPresentationVisible(&s));
	s.phase = GAMEOVER; CHECK(!heroPresentationVisible(&s));
}

static void testPublicReturnToTitle(void) {
	const tPhase phases[] = {PLAY, BOSS, SECTOR_INTRO, BOSS_INTRO, CLEAR, WIN,
		HERO_DYING, BOSS_DYING, GAMEOVER};
	const tInput held = {1, 1, 1}, right = {1, 0, 0};
	for(unsigned i = 0; i < sizeof(phases) / sizeof(*phases); ++i) {
		for(unsigned paused = 0; paused < 2; ++paused) {
			tGameState s, expected;
			memset(&s, 0x01, sizeof(s));
			s.phase = phases[i]; s.manualPause = paused;
			s.frame = 1234; s.simFrame = 567; s.sceneEpoch = 42;
			s.enemyMotionFrame = 453; s.enemyAccumulator = 12;
			logicInit(&expected);
			expected.frame = 1234; expected.simFrame = 567; expected.sceneEpoch = 42;
			expected.enemyMotionFrame = 453; expected.enemyAccumulator = 12;
			expected.titleInputBlocked = expected.presentationBusy = expected.fireWasDown = 1;
			expected.titleDirection = 1; expected.events = EVENT_LEVEL;
			logicReturnToTitle(&s, &held);
			CHECK(!memcmp(&s, &expected, sizeof(s)));
			for(unsigned tick = 0; tick < 300; ++tick) logicUpdate(&s, &held);
			CHECK(s.phase == TITLE && s.level == 0 && s.titleInputBlocked);
			logicSetPresentationBusy(&s, 0);
			logicUpdate(&s, &held); CHECK(s.titleInputBlocked);
			logicUpdate(&s, &right); CHECK(!s.titleInputBlocked && s.level == 0);
			logicUpdate(&s, &right); CHECK(s.level == 0);
			logicUpdate(&s, &idle); logicUpdate(&s, &right); CHECK(s.level == 1);
			logicUpdate(&s, &fire); CHECK(s.phase == SECTOR_INTRO && s.sceneEpoch == 43);
			logicScenePresented(&s, 42); CHECK(!s.sceneReady);
		}
	}
	logicReturnToTitle(NULL, NULL);
	tGameState s; logicInit(&s); logicReturnToTitle(&s, NULL);
	CHECK(s.phase == TITLE && !s.fireWasDown && !s.titleDirection);
}

int main(void) {
	testPublicReturnToTitle();
	testManualPauseAllPhases(); testPauseChargeAndHeroContinuity();
	testLiveOpeningAndFrozenLaterStories();
	testLiveBossArrival();
	testBossQuietBoundaryAndRelease(); testBossProjectileDrainAndPause();
	testBossFinalRetirementStartsQuietInterval();
	testGameoverReadyTimeoutAndHeldInput(); testGameoverSkipBoundary();
	testExactEnemyClockAndUnchangedProjectiles(); testSectorEnemyCadences(); testEnemyClockPreparingFreeze();
	testIndependentFireAndSectorFans(); testOrdinaryHealthAndSpawnDelays();
	testSceneHandshakeAndSkip(); testThirteenStoryBeats(); testDeathSnapshotsAndMotionParity();
	testBossDamageVisibilityAndDeath(); testBossGeometryEdges(); testEffectCapacityAndExpiry();
	testFourHostileChannels();
	testLongerBossFights();
	testExactCampaignQuotas(); testQuotaTimerAndTrackerGuards(); testFixedLanesWithMissingMembers();
	testWholeFormationMotion(); testSeparateBudgetsAndPickupPressure();
	testNormalPatternsAndDamage(); testVolleyPoolPressure(); testReleaseThresholdsAndCooldown();
	testChargeCancellationAndUpgradeLifecycle(); testSectorWaveCycles(); testFiveBonusCycle();
	testIndividualBulletChannelsAndDrops();
	testFanCorridorEdges(); testPreferredSpritePairs();
	testSchedulingScanlineBoundaries();
	testHalfSpeedMovement(); testHeroCoreAndCurtainGeometry();
	testRepeatedDenseVolleys(); testBossHalfPhaseAndCadence();
	testFormationFireAndChargePriority(); testSameTickFansFillLowestFreeSlots();
	testWaveRewards(); testBonusesAndPersistence(); testFairShootingAndBossBounds();
	testChargedGeometry(); testHostileAdmission(); testWaveCadenceAndFormations();
	testSectorSelection();
	testInitAndBounds(); testHoldAndCharge(); testHitsAndDeath();
	testCollisionEdgesAndDrops(); testStagesAndBosses(); testDeterminismAndSaturation();
	testWavesDamageAndExpiry(); testDistinctBossPatternsAndHostileLimit();
	if(failures) fprintf(stderr, "%d failed checks\n", failures);
	else puts("All shooter rules tests passed");
	return failures ? 1 : 0;
}
