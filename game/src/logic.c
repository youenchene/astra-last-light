#include "logic.h"
#include <string.h>

/* Entity/state objects contain words and are even-aligned on every target.
 * GCC otherwise expands their small memset calls into byte writes on 68000. */
static inline __attribute__((always_inline)) void clearAligned(void *buffer, uint16_t bytes) {
#if defined(__GNUC__)
	buffer = __builtin_assume_aligned(buffer, 2);
#endif
	memset(buffer, 0, bytes);
}

const char *const g_stageNames[LEVEL_COUNT] = {
	"Orbital Graveyard", "Veil Nebula", "Imperial Foundry", "Stellar Citadel"
};
const uint16_t g_stageFrames[LEVEL_COUNT] = {1800, 2000, 2200, 2400};
const uint16_t g_stageWaveQuota[LEVEL_COUNT] = {18, 21, 24, 27};
static const uint8_t s_enemyFireInterval[LEVEL_COUNT] = {96, 76, 64, 52};
static const uint8_t s_bossFireInterval[LEVEL_COUNT] = {64, 52, 44, 36};
static const uint8_t s_motionSteps[LEVEL_COUNT] = {16, 17, 18, 20};
static const uint8_t s_enemyRays[LEVEL_COUNT][2] = {{3, 5}, {5, 5}, {5, 7}, {7, 7}};
static const uint8_t s_bossRays[LEVEL_COUNT] = {5, 7, 7, 9};
/* Top-left ranges [low, low+9]: adjacent bodies retain two blank lines. */
static const int16_t s_laneLow[FORMATION_SIZE] = {56, 83, 110, 137, 164, 191};
static const uint16_t s_bossHealth[LEVEL_COUNT] = {216, 336, 432, 480};
static const uint16_t s_waveDelay[LEVEL_COUNT] = {150, 140, 130, 120};
const uint8_t g_stageWaveKinds[LEVEL_COUNT][5] = {
	{ENEMY_SCOUT, ENEMY_WEAVER, ENEMY_GUNNER, ENEMY_DART, ENEMY_ASTEROID},
	{ENEMY_WEAVER, ENEMY_DART, ENEMY_WEAVER, ENEMY_GUNNER, ENEMY_ASTEROID},
	{ENEMY_GUNNER, ENEMY_SCOUT, ENEMY_GUNNER, ENEMY_DART, ENEMY_ASTEROID},
	{ENEMY_DART, ENEMY_GUNNER, ENEMY_WEAVER, ENEMY_DART, ENEMY_ASTEROID}
};

static int16_t halfStep(int8_t velocity, uint32_t frame) {
	return velocity / 2 + ((frame & 1) ? velocity % 2 : 0);
}

static uint8_t shotWidth(const tEntity *e) {
	return e->kind == SHOT_CHARGED ? CHARGED_SHOT_W : SHOT_W;
}

static uint8_t shotHeight(const tEntity *e) {
	return e->kind == SHOT_CHARGED ? CHARGED_SHOT_H : SHOT_H;
}

static uint8_t onScreen(const tEntity *e, uint8_t height) {
	return e->x >= 0 && e->x < WORLD_W &&
		e->y >= PLAY_TOP && e->y + height <= PLAY_BOTTOM;
}

static int16_t clamp(int16_t value, int16_t low, int16_t high) {
	return value < low ? low : (value > high ? high : value);
}

static int8_t direction(int16_t value) {
	return value < 0 ? -1 : (value > 0 ? 1 : 0);
}

static uint8_t overlap(int16_t x, int16_t y, uint8_t w, uint8_t h,
	int16_t otherX, int16_t otherY, uint8_t otherW, uint8_t otherH) {
	return x < otherX + otherW && x + w > otherX &&
		y < otherY + otherH && y + h > otherY;
}

static void addScore(tGameState *s, uint16_t points) {
	s->score = UINT32_MAX - s->score < points ? UINT32_MAX : s->score + points;
}

static void clearPools(tGameState *s) {
	clearAligned(s->enemies, sizeof(s->enemies));
	clearAligned(s->shots, sizeof(s->shots));
	clearAligned(s->hostile, sizeof(s->hostile));
	clearAligned(s->pickups, sizeof(s->pickups));
	memset(s->waves, 0, sizeof(s->waves));
}

static uint8_t isScene(tPhase phase) {
	return phase == SECTOR_INTRO || phase == BOSS_INTRO || phase == CLEAR || phase == WIN;
}

static void enterScene(tGameState *s, tPhase phase, uint8_t id) {
	s->phase = phase; s->phaseFrame = 0;
	s->sceneId = id; ++s->sceneEpoch;
	s->sceneReady = 0; s->sceneArmed = 0;
	if((phase == SECTOR_INTRO || phase == BOSS_INTRO) && s->x > 152 - PLAYER_W) {
		s->x = 152 - PLAYER_W; s->moveRemainderX = 0;
	}
	s->charge = 0; s->fireCooldown = 0;
	s->events |= EVENT_LEVEL;
}

void logicScenePresented(tGameState *s, uint16_t epoch) {
	if(s && isScene(s->phase) && epoch == s->sceneEpoch && !s->sceneReady)
		s->sceneReady = 1;
}

static void addEffect(tGameState *s, uint8_t kind, int16_t x, int16_t y) {
	uint8_t slot = 0;
	if(kind == FX_HERO) slot = HERO_EFFECT_SLOT;
	else if(kind == FX_BOSS) slot = BOSS_EFFECT_SLOT;
	else for(uint8_t i = 0; i < SMALL_EFFECT_COUNT; ++i) {
		if(!s->effects[i].active) { slot = i; break; }
		if(s->effects[i].age > s->effects[slot].age) slot = i;
	}
	tEffect *e = &s->effects[slot];
	e->x = x; e->y = y; e->kind = kind; e->active = 1; e->age = 0;
	e->lifetime = kind == FX_HERO ? HERO_DEATH_FRAMES :
		kind == FX_BOSS ? BOSS_DEATH_FRAMES : SMALL_EFFECT_FRAMES;
}

static void updateEffects(tGameState *s) {
	for(uint8_t i = 0; i < EFFECT_COUNT; ++i) {
		tEffect *e = &s->effects[i];
		if(e->active && ++e->age >= e->lifetime) e->active = 0;
	}
	if(s->boss.flashTicks) --s->boss.flashTicks;
}

void logicInit(tGameState *s) {
	if(!s) return;
	clearAligned(s, sizeof(*s));
	s->x = 32; s->y = 126;
	s->lives = 3;
	s->phase = TITLE;
}

static void startStage(tGameState *s) {
	clearPools(s);
	clearAligned(s->effects, sizeof(s->effects));
	clearAligned(&s->boss, sizeof(s->boss));
	enterScene(s, SECTOR_INTRO, 3 * s->level);
	s->stageFrame = 0; s->phaseFrame = 0;
	s->waveTimer = 25; s->wave = 0;
	s->bossQuietTicks = 0;
	s->x = 32; s->y = 126;
	s->charge = 0; s->fireCooldown = 0;
	s->moveRemainderX = 0; s->moveRemainderY = 0;
	s->invulnerable = RESPAWN_FRAMES;
	s->heroBlink = 0; /* Entry grace is not damage feedback. */
	s->events |= EVENT_LEVEL;
}

static tEntity *spawn(tEntity *pool, uint8_t count, int16_t x, int16_t y,
	uint8_t kind, uint8_t hp, int8_t vx, int8_t vy) {
	uint8_t i;
	for(i = 0; i < count; ++i) {
		tEntity *e = &pool[i];
		if(e->active) continue;
		clearAligned(e, sizeof(*e));
		e->x = x; e->y = y; e->kind = kind; e->hp = hp;
		e->vx = vx; e->vy = vy;
		/* A new object must be scheduled and shown before it can collide. */
		e->active = 1;
		return e;
	}
	return 0;
}

static uint8_t fireShot(tGameState *s, uint8_t charged) {
	static const int8_t offsets[3][3] = {{0, 0, 0}, {-6, 6, 0}, {-8, 0, 8}};
	uint8_t count = charged ? 1 : s->shotLevel + 1, freeSlots = 0;
	uint8_t height = charged ? CHARGED_SHOT_H : SHOT_H;
	int16_t y = s->y + (PLAYER_H - height) / 2;
	/* No partial patterns or fire events under pool pressure. */
	for(uint8_t i = 0; i < SHOT_COUNT; ++i)
		if(!s->shots[i].active) ++freeSlots;
	if(freeSlots < count) return 0;
	for(uint8_t i = 0; i < count; ++i)
		spawn(s->shots, SHOT_COUNT, s->x + PLAYER_W,
			y + (charged ? 0 : offsets[s->shotLevel][i]), charged,
			charged ? 6 : 1 + s->weaponLevel, charged ? 4 : 6, 0);
	s->events |= EVENT_SHOT;
	if(charged) s->events |= EVENT_LANCE;
	return 1;
}

static int16_t moveHeroAxis(int16_t position, int8_t input, uint8_t speed,
	int8_t *remainder, int16_t low, int16_t high) {
	int16_t delta = direction(input) * speed + *remainder;
	position = clamp(position + delta / 2, low, high);
	*remainder = position == low || position == high ? 0 : delta % 2;
	return position;
}

static void updateHero(tGameState *s, const tInput *input) {
	uint8_t speed = PLAYER_SPEED + s->speedLevel;
	s->x = moveHeroAxis(s->x, input->dx, speed, &s->moveRemainderX, 0, WORLD_W - PLAYER_W);
	s->y = moveHeroAxis(s->y, input->dy, speed, &s->moveRemainderY, PLAY_TOP, PLAY_BOTTOM - PLAYER_H);
	/* Safe opening flight lane keeps the entire ship outside the opaque story. */
	if((s->phase == SECTOR_INTRO || s->phase == BOSS_INTRO) && s->x > 152 - PLAYER_W) {
		s->x = 152 - PLAYER_W; s->moveRemainderX = 0;
	}
	if(s->invulnerable) --s->invulnerable;
	if(s->fireCooldown) --s->fireCooldown;
	if(input->fire) {
		if(s->charge < CHARGE_FRAMES) {
			++s->charge;
			if(s->charge == CHARGE_FRAMES) s->events |= EVENT_CHARGE;
		}
	}
	else {
		if(s->charge >= CHARGE_FRAMES) fireShot(s, SHOT_CHARGED);
		else if(s->charge && !s->fireCooldown && fireShot(s, SHOT_NORMAL))
			s->fireCooldown = FIRE_INTERVAL;
		s->charge = 0;
	}
}

static void spawnWave(tGameState *s) {
	uint8_t member, slot, freeSlots = 0;
	uint8_t kind = g_stageWaveKinds[s->level][s->wave % 5];
	tWaveTrack *track = 0;
	/* Preflight before mutating either pool or counter: allocation cannot
	 * partially succeed, and a refused attempt remains due for retry. */
	for(slot = 0; slot < ENEMY_COUNT; ++slot)
		if(!s->enemies[slot].active) ++freeSlots;
	if(freeSlots < FORMATION_SIZE) return;
	for(slot = 0; slot < WAVE_TRACK_COUNT; ++slot) {
		if(s->waves[slot].remaining) continue;
		track = &s->waves[slot]; break;
	}
	if(!track) return;
	memset(track, 0, sizeof(*track));
	track->planned = FORMATION_SIZE;
	for(member = 0; member < FORMATION_SIZE; ++member) {
		tEntity *e = spawn(s->enemies, ENEMY_COUNT, member & 1 ? 280 : 304,
			s_laneLow[member] + 4, kind,
			kind == ENEMY_GUNNER || kind == ENEMY_ASTEROID ? 3 : 1,
			kind == ENEMY_DART ? -3 : -2, 0);
		e->waveMember = member;
		e->fireCountdown = 50 + 10 * member;
		e->waveId = slot + 1; ++track->spawned; ++track->remaining;
	}
	++s->wave;
	s->waveTimer = s_waveDelay[s->level];
}

static uint8_t enemiesAlive(const tGameState *s) {
	for(uint8_t i = 0; i < ENEMY_COUNT; ++i)
		if(s->enemies[i].active) return 1;
	for(uint8_t i = 0; i < WAVE_TRACK_COUNT; ++i)
		if(s->waves[i].remaining) return 1;
	return 0;
}

static void retireEnemy(tGameState *s, tEntity *e, uint8_t killed) {
	static const uint8_t bonusKinds[BONUS_KIND_COUNT] = {
		BONUS_POWER, BONUS_FIRE, BONUS_SPEED, BONUS_SHIELD, BONUS_LIFE
	};
	tWaveTrack *track;
	uint8_t i, oldest = 0;
	e->active = 0;
	if(killed) addEffect(s, e->kind == ENEMY_ASTEROID ? FX_ASTEROID : FX_ENEMY, e->x, e->y);
	if(!e->waveId || e->waveId > WAVE_TRACK_COUNT) return;
	track = &s->waves[e->waveId - 1]; e->waveId = 0;
	if(!track->remaining) return;
	--track->remaining;
	if(killed) ++track->killed; else track->failed = 1;
	if(track->remaining || track->failed || !track->planned ||
		track->spawned != track->planned || track->killed != track->planned) return;
	for(i = 0; i < BONUS_COUNT; ++i) {
		if(!s->pickups[i].active) { oldest = i; break; }
		if(s->pickups[i].age > s->pickups[oldest].age) oldest = i;
	}
	s->pickups[oldest].active = 0;
	/* BOB background save needs an extra aligned word at the right edge. */
	spawn(s->pickups, BONUS_COUNT, clamp(e->x, 0, WORLD_W - 17), e->y,
		bonusKinds[s->bonusCycle], 1, -1, 0);
	s->bonusCycle = (s->bonusCycle + 1) % BONUS_KIND_COUNT;
	s->events |= EVENT_BONUS_DROP;
}

static void updatePickups(tGameState *s) {
	uint8_t i;
	for(i = 0; i < BONUS_COUNT; ++i) {
		tEntity *e = &s->pickups[i];
		if(!e->active) continue;
		e->x += halfStep(e->vx, s->simFrame);
		if(++e->age >= BONUS_LIFETIME || e->x < 0) { e->active = 0; continue; }
		if(!e->visible || !onScreen(e, 16) || !overlap(s->x, s->y, PLAYER_W, PLAYER_H,
			e->x, e->y, 16, 16)) continue;
		switch(e->kind) {
		case BONUS_POWER: if(s->weaponLevel < 2) ++s->weaponLevel; break;
		case BONUS_FIRE: if(s->shotLevel < 2) ++s->shotLevel; break;
		case BONUS_SPEED: if(s->speedLevel < 2) ++s->speedLevel; break;
		case BONUS_SHIELD: if(s->shield < 2) ++s->shield; break;
		case BONUS_LIFE: if(s->lives < 5) ++s->lives; break;
		}
		e->active = 0; s->events |= EVENT_BONUS_PICKUP;
	}
}

/* Upper bound on remaining ticks: 1.5px/tick left (683/1024 > 2/3) and
 * |vy|/2 px/tick toward the corridor edge. No division on the 68000. */
static uint16_t hostileLife(const tEntity *e) {
#define LIFE_AT(x) ((((x) + HOSTILE_W) * 683UL) >> 10) + 2
#define LIFE_ROW(x) LIFE_AT(x), LIFE_AT(x+1), LIFE_AT(x+2), LIFE_AT(x+3), \
	LIFE_AT(x+4), LIFE_AT(x+5), LIFE_AT(x+6), LIFE_AT(x+7), \
	LIFE_AT(x+8), LIFE_AT(x+9), LIFE_AT(x+10), LIFE_AT(x+11), \
	LIFE_AT(x+12), LIFE_AT(x+13), LIFE_AT(x+14), LIFE_AT(x+15)
	/* Identical rounded bounds for ordinary origins; all arithmetic below is
	 * retained for legacy/injected coordinates outside the corridor. */
	static const uint16_t horizontal[WORLD_W] = {
		LIFE_ROW(0), LIFE_ROW(16), LIFE_ROW(32), LIFE_ROW(48),
		LIFE_ROW(64), LIFE_ROW(80), LIFE_ROW(96), LIFE_ROW(112),
		LIFE_ROW(128), LIFE_ROW(144), LIFE_ROW(160), LIFE_ROW(176),
		LIFE_ROW(192), LIFE_ROW(208), LIFE_ROW(224), LIFE_ROW(240),
		LIFE_ROW(256), LIFE_ROW(272), LIFE_ROW(288), LIFE_ROW(304)
	};
#undef LIFE_ROW
#undef LIFE_AT
	uint16_t life = (uint16_t)e->x < WORLD_W ? horizontal[(uint16_t)e->x] :
		(uint16_t)(((int32_t)(int16_t)(e->x + HOSTILE_W) * 683) >> 10) + 2;
	if(e->vy) {
		int16_t room = e->vy > 0 ? PLAY_BOTTOM - HOSTILE_H - e->y : e->y - PLAY_TOP;
		if(room < 0) room = 0;
		uint16_t t = (uint16_t)((e->vy == 1 || e->vy == -1 ? room * 2 : room) + 2);
		if(t < life) life = t;
	}
	return life;
}

/* Straight paths in doubled pixels: 2y(t) = 2y + vy*t. Linear distance is
 * extremal at the ends of the shared lifetime, so two samples suffice.
 * The candidate's fields arrive in registers; |2dy| < 2*apart is |dy| < apart. */
static uint8_t staysApart(const tEntity *o, int16_t y, int8_t vy, uint16_t age) {
	const int16_t apart = HOSTILE_H + HOSTILE_GAP;
	int16_t dy = (int16_t)(y - o->y);
	int8_t otherVy = o->vy;
	/* Already-overlapping paths fail immediately; parallel/diverging paths
	 * need no lifetime multiplication on the 68000. */
	if(dy >= 0) {
		if(dy < apart) return 0;
		if(vy >= otherVy) return 1;
	}
	else {
		if(dy > -apart) return 0;
		if(vy <= otherVy) return 1;
	}
	int16_t t = (int16_t)(o->age < age ? o->age : age);
	int16_t velocity = (int16_t)(vy - otherVy), travel;
	/* Most converging rays differ by one/two half-pixels per tick. Word
	 * additions avoid a 68000 MULS without changing endpoint wrap semantics. */
	if(velocity == 1) travel = t;
	else if(velocity == -1) travel = (int16_t)-t;
	else if(velocity == 2) travel = (int16_t)(t + t);
	else if(velocity == -2) travel = (int16_t)(-t - t);
	else travel = (int16_t)(velocity * t);
	int16_t d1 = (int16_t)(dy * 2 + travel);
	return dy >= 0 ? d1 >= 2 * apart : d1 <= -2 * apart;
}

/* PLAY owns only two channels. Keep its common admission path to two counters
 * and constant channel bits; boss/legacy ownership retains the general path. */
static uint8_t admitPlayHostile(tGameState *s, tEntity *e) {
	uint8_t fits = 0xc0, count6 = 0, count7 = 0;
	const int16_t y = e->y;
	const int8_t vy = e->vy;
	const uint16_t age = hostileLife(e);
	e->age = age; e->channel = 0;
	tEntity *o = s->hostile;
	for(uint8_t i = HOSTILE_COUNT; i; --i, ++o) {
		uint8_t bit;
		if(!o->active) continue;
		if(o->channel == 6) { ++count6; bit = 0x40; }
		else if(o->channel == 7) { ++count7; bit = 0x80; }
		else continue;
		if(!(fits & bit)) continue;
		if(!o->age) o->age = hostileLife(o);
		if(!staysApart(o, y, vy, age)) { fits &= (uint8_t)~bit; if(!fits) break; }
	}
	if((fits & 0x40) && count6 < BULLET_SPRITE_CAPACITY) e->channel = 6;
	if((fits & 0x80) && count7 < (e->channel ? count6 : BULLET_SPRITE_CAPACITY)) e->channel = 7;
	if(!e->channel) { e->active = 0; e->visible = 0; return 0; }
	return 1;
}

/* One pass over the pool, with explicit scalar counters for the four DMA
 * owners. Least-occupied choice and low-channel tie breaking stay unchanged. */
static uint8_t admitHostile(tGameState *s, tEntity *e) {
	if(s->phase == PLAY) return admitPlayHostile(s, e);
	uint8_t fits = logicHostileChannelMask(s), bestCount = BULLET_SPRITE_CAPACITY;
	uint8_t count4 = 0, count5 = 0, count6 = 0, count7 = 0;
	const int16_t y = e->y;
	const int8_t vy = e->vy;
	const uint16_t age = hostileLife(e);
	e->age = age;
	/* Channel zero also makes the pool scan skip the candidate itself. */
	e->channel = 0;
	tEntity *o = s->hostile;
	for(uint8_t i = HOSTILE_COUNT; i; --i, ++o) {
		uint8_t bit;
		if(!o->active) continue;
		switch(o->channel) {
		case 4: ++count4; bit = 0x10; break;
		case 5: ++count5; bit = 0x20; break;
		case 6: ++count6; bit = 0x40; break;
		case 7: ++count7; bit = 0x80; break;
		default: continue;
		}
		if(!(fits & bit)) continue;
		if(!o->age) o->age = hostileLife(o);
		if(!staysApart(o, y, vy, age)) {
			fits &= (uint8_t)~bit;
			/* Once every permitted channel conflicts, no later entity can
			 * make this ray admissible. Dense volleys take this path often. */
			if(!fits) break;
		}
	}
	if((fits & 0x10) && count4 < bestCount) { bestCount = count4; e->channel = 4; }
	if((fits & 0x20) && count5 < bestCount) { bestCount = count5; e->channel = 5; }
	if((fits & 0x40) && count6 < bestCount) { bestCount = count6; e->channel = 6; }
	if((fits & 0x80) && count7 < bestCount) e->channel = 7;
	if(!e->channel) { e->active = 0; e->visible = 0; return 0; }
	return 1;
}

typedef struct {
	tEntity *members[2][BULLET_SPRITE_CAPACITY];
	uint8_t count[2], checked[2], valid;
} tPlayAdmission;

static void playAdmissionBegin(tGameState *s, tPlayAdmission *cache) {
	cache->count[0] = cache->count[1] = 0; cache->valid = 1;
	for(uint8_t i = 0; i < HOSTILE_COUNT; ++i) {
		tEntity *e = &s->hostile[i];
		if(!e->active || e->channel < 6 || e->channel > 7) continue;
		uint8_t channel = e->channel - 6;
		if(cache->count[channel] == BULLET_SPRITE_CAPACITY) { cache->valid = 0; return; }
		cache->members[channel][cache->count[channel]++] = e;
	}
	cache->checked[0] = cache->count[0]; cache->checked[1] = cache->count[1];
}

static uint8_t admitVolleyHostile(tGameState *s, tEntity *e, tPlayAdmission *cache) {
	if(!cache || !cache->valid) return admitHostile(s, e);
	uint8_t bestCount = BULLET_SPRITE_CAPACITY;
	const int16_t y = e->y;
	const int8_t vy = e->vy;
	const uint16_t age = hostileLife(e);
	e->age = age; e->channel = 0;
	for(uint8_t channel = 0; channel < 2; ++channel) {
		uint8_t fits = 1;
		for(uint8_t i = 0; i < cache->checked[channel]; ++i) {
			tEntity *o = cache->members[channel][i];
			if(!o->age) o->age = hostileLife(o);
			if(!staysApart(o, y, vy, age)) { fits = 0; break; }
		}
		if(fits && cache->count[channel] < bestCount) {
			bestCount = cache->count[channel]; e->channel = channel + 6;
		}
	}
	if(!e->channel) { e->active = 0; e->visible = 0; return 0; }
	/* New rays in this one chevron start FAN_SPACING apart and have
	 * nondecreasing slopes, so they cannot conflict with one another. Their
	 * occupancy still participates in least-loaded channel selection. */
	++cache->count[e->channel - 6];
	return 1;
}

static void fireHostile(tGameState *s, int16_t x, int16_t y, int8_t vy, tPlayAdmission *cache) {
	tEntity *e = spawn(s->hostile, HOSTILE_COUNT, x, y, s->level, 1, HOSTILE_VX, vy);
	if(e) admitVolleyHostile(s, e, cache);
}

/* Chevron: the aimed centre ray leads, outer rays trail and diverge. Rays
 * start FAN_SPACING apart, so a 14px gap (wider than the 8px core) is always
 * open, and non-decreasing vy means neighbouring gaps never shrink. */
static void fireFan(tGameState *s, int16_t x, int16_t y, uint8_t rays, int8_t aim) {
	tPlayAdmission cache, *reserved = 0;
	if(s->phase == PLAY) { playAdmissionBegin(s, &cache); reserved = &cache; }
	int8_t ray, radius = rays / 2;
	for(ray = -radius; ray <= radius; ++ray) {
		int16_t rayY = y + ray * FAN_SPACING;
		int16_t rayX = x + (ray < 0 ? -ray : ray) * FAN_STAGGER;
		/* Clamping origins would stack distinct bullets on the corridor edge. */
		if(rayY < PLAY_TOP || rayY + HOSTILE_H > PLAY_BOTTOM) continue;
		fireHostile(s, rayX, rayY, (int8_t)clamp(aim + ray, -2, 2), reserved);
	}
}

static uint8_t updateEnemies(tGameState *s, uint8_t motionStep) {
	uint8_t i, lanes = 0, separated = 1;
	for(i = 0; i < ENEMY_COUNT; ++i) {
		tEntity *e = &s->enemies[i];
		if(!e->active) continue;
		if(e->kind == ENEMY_BOSS) { separated = 0; continue; }
		uint8_t tracked = e->waveId && e->waveId <= WAVE_TRACK_COUNT &&
			s->waves[e->waveId - 1].planned == FORMATION_SIZE && e->waveMember < FORMATION_SIZE;
		if(motionStep) {
			++e->age;
			e->x += halfStep(e->vx, s->enemyMotionFrame);
			if(e->kind == ENEMY_WEAVER) e->y += halfStep((e->age & 32) ? -1 : 1, s->enemyMotionFrame);
			if(e->kind == ENEMY_DART && e->age < 64) e->y += halfStep(direction(s->y - e->y), s->enemyMotionFrame);
			e->y = tracked ? clamp(e->y, s_laneLow[e->waveMember], s_laneLow[e->waveMember] + 9) :
				clamp(e->y, PLAY_TOP, PLAY_BOTTOM - ENEMY_H);
		}
		if(tracked && (motionStep || (e->y >= s_laneLow[e->waveMember] && e->y <= s_laneLow[e->waveMember] + 9))) {
			uint8_t bit = 1u << e->waveMember;
			if(lanes & bit) separated = 0;
			lanes |= bit;
		}
		else separated = 0;
		if(e->fireCountdown) --e->fireCountdown;
		if(e->kind != ENEMY_ASTEROID && !e->fireCountdown) {
			e->fireCountdown = s_enemyFireInterval[s->level];
			if(e->visible && e->x > 40 && e->x < 280)
				fireFan(s, e->x, e->y + (ENEMY_H - HOSTILE_H) / 2, s_enemyRays[s->level][e->kind == ENEMY_GUNNER],
					direction(s->y + PLAYER_H / 2 - e->y));
		}
		if(e->x <= -ENEMY_W) retireEnemy(s, e, 0);
	}
	return separated;
}

static void startBoss(tGameState *s) {
	clearPools(s);
	clearAligned(&s->boss, sizeof(s->boss));
	s->boss.x = 240; s->boss.y = 104;
	s->boss.hp = s_bossHealth[s->level]; s->boss.maxHp = s->boss.hp;
	s->boss.cooldown = 50; s->boss.kind = s->level; s->boss.active = 1;
	enterScene(s, BOSS_INTRO, 3 * s->level + 1);
}

static uint8_t bossCorridorQuiet(const tGameState *s) {
	if(s->wave < g_stageWaveQuota[s->level] || enemiesAlive(s)) return 0;
	for(uint8_t i = 0; i < SHOT_COUNT; ++i)
		if(s->shots[i].active) return 0;
	for(uint8_t i = 0; i < HOSTILE_COUNT; ++i)
		if(s->hostile[i].active) return 0;
	return 1;
}

static void updateBossGate(tGameState *s, uint8_t wasQuiet) {
	/* Count complete empty combat intervals, not the last projectile's exit or
	 * final enemy's retirement tick. A release at the screen edge still resets. */
	if(!wasQuiet || !bossCorridorQuiet(s) || (s->events & EVENT_SHOT)) {
		s->bossQuietTicks = 0;
		return;
	}
	if(++s->bossQuietTicks == BOSS_QUIET_FRAMES) startBoss(s);
}

static void bossVolley(tGameState *s) {
	int16_t y = s->boss.y + (BOSS_H - HOSTILE_H) / 2;
	int16_t x = s->boss.x - HOSTILE_W;
	int8_t aim = direction(s->y + PLAYER_H / 2 - y - HOSTILE_H / 2);
	switch(s->level) {
	case 0: /* Gravekeeper: aimed chevron, broad vertical patrol. */
		fireFan(s, x, y, s_bossRays[s->level], aim);
		break;
	case 1: /* Veil Wraith: level chevron while weaving. */
		fireFan(s, x, y, s_bossRays[s->level], 0);
		break;
	case 2: /* Forge Ram: aimed seven-ray chevron and periodic lunges. */
		fireFan(s, x, y, s_bossRays[s->level], aim);
		break;
	default: /* Citadel Heart: alternating aimed chevron and lane barrage. */
		if(s->boss.tick & 64) fireFan(s, x, y, s_bossRays[s->level], aim);
		else {
			/* 32px lanes leave 24px corridors; alternate volleys shift by 16. */
			for(int16_t laneY = PLAY_TOP + 4 + ((s->boss.tick & 32) ? 16 : 0);
				laneY + HOSTILE_H <= PLAY_BOTTOM; laneY += 32)
				fireHostile(s, x, laneY, 0, 0);
		}
		break;
	}
	s->boss.cooldown = s_bossFireInterval[s->level];
}

static void updateBoss(tGameState *s) {
	uint16_t cycle;
	++s->boss.tick;
	cycle = (s->boss.tick >> 1) & 255;
	switch(s->level) {
	case 0: s->boss.y = (int16_t)(48 + (cycle < 128 ? cycle : 255 - cycle)); break;
	case 1:
		s->boss.y = (int16_t)(56 + ((cycle < 128 ? cycle : 255 - cycle) >> 1));
		s->boss.x = (int16_t)(224 + (((s->boss.tick >> 1) & 63) >> 1));
		break;
	case 2:
		s->boss.y = (int16_t)(88 + ((cycle & 127) >> 2));
		s->boss.x = cycle < 64 ? (int16_t)(240 - cycle * 2) :
			(cycle < 128 ? (int16_t)(112 + (cycle - 64) * 2) : 240);
		break;
	default:
		s->boss.y = (int16_t)(48 + (cycle < 128 ? cycle : 255 - cycle));
		s->boss.x = (int16_t)(220 + (((s->boss.tick >> 1) & 63) >> 1));
		break;
	}
	s->boss.x = clamp(s->boss.x, 0, BOSS_MAX_X);
	s->boss.y = clamp(s->boss.y, PLAY_TOP, PLAY_BOTTOM - BOSS_H);
}

static void moveProjectiles(tEntity *pool, uint8_t count, uint8_t playerShots, uint32_t frame) {
	static const int8_t halfMotion[2][5] = {{-1, 0, 0, 0, 1}, {-1, -1, 0, 1, 1}};
	const int8_t *motion = halfMotion[frame & 1];
	const int16_t hostileStep = frame & 1 ? -2 : -1;
	uint8_t i;
	for(i = 0; i < count; ++i) {
		tEntity *e = &pool[i];
		if(!e->active) continue;
		uint8_t width = playerShots ? shotWidth(e) : HOSTILE_W;
		uint8_t height = playerShots ? shotHeight(e) : HOSTILE_H;
		if(playerShots) { e->x += e->vx; if(e->vy) e->y += e->vy; }
		else {
			e->x += e->vx == HOSTILE_VX ? hostileStep : halfStep(e->vx, frame);
			if(e->vy) e->y += e->vy >= -2 && e->vy <= 2 ? motion[e->vy + 2] : halfStep(e->vy, frame);
		}
		if(!playerShots && e->age) --e->age;
		/* Player shots are BOBs: beyond BOB_MAX_X they could not be drawn. */
		if(e->x > (playerShots ? BOB_MAX_X : WORLD_W - 1) || e->x <= -width ||
			e->y < PLAY_TOP || e->y + height > PLAY_BOTTOM)
			e->active = 0;
	}
}

static void killBoss(tGameState *s) {
	addScore(s, (uint16_t)(2000 + s->level * 1000));
	clearAligned(s->shots, sizeof(s->shots));
	clearAligned(s->hostile, sizeof(s->hostile));
	s->boss.active = 0; s->boss.visible = 0;
	addEffect(s, FX_BOSS, s->boss.x, s->boss.y);
	s->phase = BOSS_DYING; s->phaseFrame = 0;
	s->charge = 0; s->fireCooldown = 0;
	s->events |= EVENT_EXPLOSION | EVENT_LEVEL;
}

static void collideShots(tGameState *s) {
	uint8_t i, j;
	tEntity *targets[ENEMY_COUNT];
	uint8_t targetCount = 255;
	int16_t targetY = 0;
	uint8_t targetHeight = 0;
	for(i = 0; i < SHOT_COUNT; ++i) {
		tEntity *shot = &s->shots[i];
		if(!shot->active || !shot->visible || !onScreen(shot, shotHeight(shot))) continue;
		uint8_t width = shotWidth(shot), height = shotHeight(shot);
		if(s->phase == BOSS && s->boss.active && s->boss.visible &&
			overlap(shot->x, shot->y, width, height,
				s->boss.x, s->boss.y, BOSS_W, BOSS_H)) {
			shot->active = 0;
			if(shot->hp) {
				s->boss.hp = s->boss.hp > shot->hp ? s->boss.hp - shot->hp : 0;
				s->boss.flashTicks = BOSS_FLASH_FRAMES;
				if(!s->boss.hp) { killBoss(s); return; }
			}
			continue;
		}
		/* Boss mode has no ordinary enemy entities. */
		if(s->phase == BOSS) continue;
		/* Gather once, only when a shot needs it. Pool order preserves which
		 * overlapping enemy is hit first. A prior shot may retire a target. */
		if(targetCount == 255 || targetY != shot->y || targetHeight != height) {
			targetCount = 0;
			targetY = shot->y; targetHeight = height;
			for(j = 0; j < ENEMY_COUNT; ++j) {
				tEntity *e = &s->enemies[j];
				if(e->active && e->visible && e->y < targetY + height && e->y + ENEMY_H > targetY &&
					onScreen(e, ENEMY_H)) targets[targetCount++] = e;
			}
		}
		for(j = 0; j < targetCount; ++j) {
			tEntity *e = targets[j];
			if(!e->active || !overlap(shot->x, shot->y, width, height,
				e->x, e->y, ENEMY_W, ENEMY_H)) continue;
			shot->active = 0;
			if(e->hp <= shot->hp) {
				retireEnemy(s, e, 1);
				addScore(s, (uint16_t)(100 + e->kind * 50));
				s->events |= EVENT_EXPLOSION;
			}
			else e->hp -= shot->hp;
			break;
		}
	}
}

static void hurtHero(tGameState *s) {
	if(s->invulnerable || !s->lives) return;
	if(s->shield) {
		--s->shield; s->invulnerable = 30; s->heroBlink = 1; s->events |= EVENT_HIT; return;
	}
	--s->lives;
	if(s->weaponLevel) --s->weaponLevel;
	if(s->shotLevel) --s->shotLevel;
	if(s->speedLevel) --s->speedLevel;
	s->shield = 0;
	s->moveRemainderX = 0; s->moveRemainderY = 0;
	s->events |= EVENT_HIT | EVENT_EXPLOSION;
	s->charge = 0; s->fireCooldown = 0;
	clearAligned(s->hostile, sizeof(s->hostile));
	clearAligned(s->shots, sizeof(s->shots));
	addEffect(s, FX_HERO, s->x, s->y);
	s->resumePhase = s->phase;
	s->phase = HERO_DYING; s->phaseFrame = 0;
}

static void collideHero(tGameState *s) {
	uint8_t i;
	if(s->invulnerable) return;
	const int16_t x = s->x + PLAYER_HIT_X, y = s->y + PLAYER_HIT_Y;
	if(s->phase == BOSS && s->boss.active && s->boss.visible &&
		overlap(x, y, PLAYER_HIT_W, PLAYER_HIT_H,
			s->boss.x, s->boss.y, BOSS_W, BOSS_H)) { hurtHero(s); return; }
	for(i = 0; i < HOSTILE_COUNT; ++i) {
		tEntity *e = &s->hostile[i];
		if(!e->active || !e->visible) continue;
		/* Most visible projectiles are far from the hitbox. Bounds matter only
		 * for an actual overlap; keep them before committing any damage. */
		if(overlap(x, y, PLAYER_HIT_W, PLAYER_HIT_H,
			e->x, e->y, HOSTILE_W, HOSTILE_H) && onScreen(e, HOSTILE_H)) { hurtHero(s); return; }
	}
	if(s->phase == BOSS) return;
	for(i = 0; i < ENEMY_COUNT; ++i) {
		tEntity *e = &s->enemies[i];
		if(e->active && e->visible && overlap(x, y, PLAYER_HIT_W, PLAYER_HIT_H,
			e->x, e->y, ENEMY_W, ENEMY_H) && onScreen(e, ENEMY_H)) { hurtHero(s); return; }
	}
}

static void resetSchedule(tEntity *pool, uint8_t count) {
	for(uint8_t i = 0; i < count; ++i) { pool[i].visible = 0; pool[i].channel = 0; }
}

/* Hostiles keep the channel chosen at admission, so no per-tick calendar.
 * Entities injected without a channel (tests, legacy state) are admitted
 * here, or discarded if they could never be shown. */
static void scheduleBullets(tGameState *s) {
	uint8_t ownedChannels = logicHostileChannelMask(s);
	uint8_t firstChannel = ownedChannels == 0xc0 ? 6 : 4;
	for(uint8_t i = 0; i < HOSTILE_COUNT; ++i) {
		tEntity *e = &s->hostile[i];
		if(!e->active) { e->visible = 0; e->channel = 0; continue; }
		if((!ownedChannels || e->channel < firstChannel || e->channel > 7) && !admitHostile(s, e)) continue;
		e->visible = onScreen(e, HOSTILE_H);
	}
	for(uint8_t i = 0; i < SHOT_COUNT; ++i) {
		tEntity *e = &s->shots[i];
		e->channel = 0;
		e->visible = e->active && e->x <= BOB_MAX_X && onScreen(e, shotHeight(e));
	}
}

static void scheduleEnemies(tGameState *s, uint8_t separated) {
	/* The motion pass has already checked and clamped these distinct lanes.
	 * No public-state cache: the proof is valid only inside this update. */
	if(separated) {
		for(uint8_t i = 0; i < ENEMY_COUNT; ++i) {
			tEntity *e = &s->enemies[i];
			e->visible = e->active && e->x >= 0 && e->x < WORLD_W;
			e->channel = e->visible ? 4 : 0;
		}
		return;
	}
	/* Ordinary waves reserve six disjoint lanes. Validate their actual geometry
	 * before taking the linear path; arbitrary/injected overlaps retain rotating
	 * priority below. Off-screen entities never consume a DMA slot. */
	uint8_t lanes = 0, formation = 1;
	for(uint8_t i = 0; i < ENEMY_COUNT; ++i) {
		tEntity *e = &s->enemies[i];
		e->visible = e->channel = 0;
		if(!e->active || !onScreen(e, ENEMY_H)) continue;
		if(!e->waveId || e->waveId > WAVE_TRACK_COUNT ||
			s->waves[e->waveId - 1].planned != FORMATION_SIZE ||
			e->waveMember >= FORMATION_SIZE || e->y < s_laneLow[e->waveMember] ||
			e->y > s_laneLow[e->waveMember] + 9 || (lanes & (1u << e->waveMember))) {
			formation = 0; break;
		}
		lanes |= 1u << e->waveMember;
		e->visible = 1; e->channel = 4;
	}
	if(formation) return;
	uint8_t assigned = 0, start = (uint16_t)s->simFrame % ENEMY_COUNT;
	tEntity *accepted[ENEMY_SPRITE_CAPACITY];
	resetSchedule(s->enemies, ENEMY_COUNT);
	for(uint8_t i = 0; i < ENEMY_COUNT; ++i) {
		uint8_t index = start + i, fits = 1;
		if(index >= ENEMY_COUNT) index -= ENEMY_COUNT;
		tEntity *e = &s->enemies[index];
		if(!e->active || !onScreen(e, ENEMY_H) || assigned == ENEMY_SPRITE_CAPACITY) continue;
		for(uint8_t j = 0; j < assigned; ++j) {
			const tEntity *other = accepted[j];
			if(e->y < other->y + ENEMY_H + 2 &&
				e->y + ENEMY_H + 2 > other->y) { fits = 0; break; }
		}
		if(fits) { e->visible = 1; e->channel = 4; accepted[assigned++] = e; }
	}
}

static void scheduleSprites(tGameState *s, uint8_t separated) {
	s->boss.visible = s->phase == BOSS && s->boss.active;
	if(s->phase == PLAY) scheduleEnemies(s, separated);
	scheduleBullets(s);
	resetSchedule(s->pickups, BONUS_COUNT);
	for(uint8_t i = 0; i < BONUS_COUNT; ++i)
		s->pickups[i].visible = s->pickups[i].active && onScreen(&s->pickups[i], 16);
}

static void resetGame(tGameState *s) {
	/* Epochs and clocks survive restarts so delayed presentation acknowledgements
	 * cannot accidentally acknowledge a new game. */
	uint16_t epoch = s->sceneEpoch;
	uint32_t frame = s->frame, simFrame = s->simFrame;
	uint32_t enemyMotionFrame = s->enemyMotionFrame;
	uint8_t enemyAccumulator = s->enemyAccumulator;
	logicInit(s);
	s->sceneEpoch = epoch; s->frame = frame; s->simFrame = simFrame;
	s->enemyMotionFrame = enemyMotionFrame; s->enemyAccumulator = enemyAccumulator;
}

static void restart(tGameState *s, uint8_t level) {
	resetGame(s);
	s->level = level; s->fireWasDown = 1; startStage(s);
}

void logicReturnToTitle(tGameState *s, const tInput *input) {
	static const tInput neutral = {0, 0, 0};
	if(!s) return;
	if(!input) input = &neutral;
	resetGame(s);
	s->titleInputBlocked = 1;
	s->presentationBusy = 1;
	s->fireWasDown = input->fire != 0;
	s->titleDirection = direction(input->dx);
	s->events = EVENT_LEVEL;
}

static void updateGameover(tGameState *s, const tInput *input, uint8_t pressed) {
	if(s->presentationBusy) return;
	if(!input->fire) s->sceneArmed = 1;
	++s->phaseFrame;
	if(s->phaseFrame < GAMEOVER_FRAMES &&
		!(s->sceneArmed && pressed && s->phaseFrame >= SCENE_SKIP_FRAMES)) return;
	logicReturnToTitle(s, input);
}

static void updateScene(tGameState *s, const tInput *input, uint8_t pressed) {
	if(!s->sceneReady || s->presentationBusy) return;
	if(!input->fire) s->sceneArmed = 1;
	if(s->phaseFrame < SCENE_FRAMES) ++s->phaseFrame;
	uint8_t skip = s->sceneArmed && pressed && s->phaseFrame >= SCENE_SKIP_FRAMES;
	if(s->phase == WIN) {
		if(skip) restart(s, 0);
		return;
	}
	if(s->phaseFrame < SCENE_FRAMES && !skip) return;
	if(s->phase == SECTOR_INTRO || s->phase == BOSS_INTRO) {
		s->charge = 0;
		s->phase = s->phase == SECTOR_INTRO ? PLAY : BOSS;
		s->phaseFrame = 0; s->sceneReady = 0; s->sceneArmed = 0;
		s->events |= EVENT_LEVEL;
	}
	else if(s->level == LEVEL_COUNT - 1) enterScene(s, WIN, 12);
	else { ++s->level; startStage(s); }
}

static void updateDeath(tGameState *s) {
	uint16_t duration = s->phase == HERO_DYING ? HERO_DEATH_FRAMES : BOSS_DEATH_FRAMES;
	if(++s->phaseFrame < duration) return;
	if(s->phase == BOSS_DYING) enterScene(s, CLEAR, 3 * s->level + 2);
	else {
		s->phaseFrame = 0;
		if(!s->lives) {
			clearPools(s); s->boss.active = 0; s->boss.visible = 0;
			s->phase = GAMEOVER; s->presentationBusy = 1; s->sceneArmed = 0;
		}
		else {
			s->phase = s->resumePhase;
			s->x = 32; s->y = 126; s->invulnerable = RESPAWN_FRAMES;
			s->heroBlink = 1;
		}
		s->events |= EVENT_LEVEL;
	}
}

void logicSetPresentationBusy(tGameState *s, uint8_t busy) {
	if(s) s->presentationBusy = busy != 0;
}

void logicTogglePause(tGameState *s) {
	if(!s || s->phase == TITLE || s->phase == GAMEOVER) return;
	s->manualPause ^= 1;
	s->charge = 0;
	s->pauseFireBlocked = 1;
	s->sceneArmed = 0;
}

/* Optional portable callback; production has no hardware dependency or calls. */
#ifdef ASTRA_FRAME_BREAKDOWN
extern unsigned char galaxyTraceTarget;
extern void galaxyTraceMarkTarget(unsigned char mark);
#define logicTrace(mark) do { if(galaxyTraceTarget) galaxyTraceMarkTarget(mark); } while(0)
#else
#define logicTrace(mark) ((void)0)
#endif
uint8_t logicUpdate(tGameState *s, const tInput *input) {
	static const tInput neutral = {0, 0, 0};
	tInput filtered;
	uint8_t pressed;
	if(!s) return 0;
	if(!input) input = &neutral;
	pressed = input->fire && !s->fireWasDown;
	s->fireWasDown = input->fire != 0;
	s->events = 0;
	++s->frame;
	updateEffects(s);
	if(s->manualPause) return 1;
	if(s->pauseFireBlocked) {
		/* A held/released pause-era charge cannot become a shot or scene skip. */
		if(!input->fire) s->pauseFireBlocked = 0;
		filtered = *input; filtered.fire = 0; input = &filtered;
		pressed = 0;
	}
	if(s->phase == TITLE) {
		int8_t nextDirection = direction(input->dx);
		if(s->titleInputBlocked) {
			s->titleDirection = nextDirection;
			if(!s->presentationBusy && !input->fire) s->titleInputBlocked = 0;
			return 0;
		}
		if(nextDirection && !s->titleDirection)
			s->level = (uint8_t)((s->level + nextDirection + LEVEL_COUNT) & 3);
		s->titleDirection = nextDirection;
	}
	if(s->phase == GAMEOVER) { updateGameover(s, input, pressed); return 1; }
	if(s->phase == TITLE) {
		if(!pressed) return 0;
		restart(s, s->level);
		return 1;
	}
	if(isScene(s->phase)) {
		updateScene(s, input, pressed);
		if((s->phase == SECTOR_INTRO || s->phase == BOSS_INTRO) &&
			s->sceneReady && !s->presentationBusy) {
			/* Opening is a safe flight area, not combat: no wave, enemy or
			 * combat clock advances. Keep the respawn grace for actual combat. */
			uint16_t grace = s->invulnerable;
			updateHero(s, input);
			s->invulnerable = grace;
			moveProjectiles(s->shots, SHOT_COUNT, 1, s->frame);
		}
		return 1;
	}
	if(s->phase == HERO_DYING || s->phase == BOSS_DYING) { updateDeath(s); return 1; }
	if(!logicCombatActive(s)) return 0;
	if(s->presentationBusy) return 1;
	uint8_t wasQuiet = s->phase == PLAY && bossCorridorQuiet(s);
	++s->simFrame;
	s->enemyAccumulator += s_motionSteps[s->level];
	uint8_t enemyStep = s->enemyAccumulator >= 20;
	if(enemyStep) { s->enemyAccumulator -= 20; ++s->enemyMotionFrame; }
	updateHero(s, input);
	logicTrace(26);
	uint8_t separated = 0;
	if(s->phase == PLAY) {
		++s->stageFrame;
		if(s->waveTimer) --s->waveTimer;
		if(!s->waveTimer && s->wave < g_stageWaveQuota[s->level] && !enemiesAlive(s)) spawnWave(s);
		separated = updateEnemies(s, enemyStep);
	}
	else {
		if(enemyStep) updateBoss(s);
		if(s->boss.cooldown) --s->boss.cooldown;
		if(!s->boss.cooldown) bossVolley(s);
	}
	logicTrace(27);
	moveProjectiles(s->shots, SHOT_COUNT, 1, s->simFrame);
	moveProjectiles(s->hostile, HOSTILE_COUNT, 0, s->simFrame);
	logicTrace(28);
	updatePickups(s);
	logicTrace(29);
	/* Collide only entities shown on the preceding frame, before rescheduling.
	 * Thus mux drops (including extra renderer drops) are never lethal. */
	collideShots(s);
	if(s->phase == PLAY || s->phase == BOSS) collideHero(s);
	logicTrace(30);
	if(logicCombatActive(s)) scheduleSprites(s, separated);
	logicTrace(31);
	/* Collisions/death have precedence; a death tick cannot advance the gate. */
	if(s->phase == PLAY) updateBossGate(s, wasQuiet);
	logicTrace(32);
	return 1;
}
