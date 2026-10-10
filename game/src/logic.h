#ifndef ASTRA_LOGIC_H
#define ASTRA_LOGIC_H

#include <stdint.h>

#define WORLD_W 320
#define WORLD_H 256
#define PLAY_TOP 56
#define PLAY_BOTTOM 216
#define PLAYER_W 32
#define PLAYER_H 24
#define PLAYER_HIT_X 12
#define PLAYER_HIT_Y 8
#define PLAYER_HIT_W 8
#define PLAYER_HIT_H 8
#define PLAYER_SPEED 3
#define ENEMY_W 16
#define ENEMY_H 16
#define BOSS_W 64
#define BOSS_H 48
#define BOSS_MAX_X 255
#define EFFECT_COUNT 8
#define SMALL_EFFECT_COUNT 6
#define HERO_EFFECT_SLOT 6
#define BOSS_EFFECT_SLOT 7
#define SMALL_EFFECT_FRAMES 16
#define HERO_DEATH_FRAMES 40
#define BOSS_DEATH_FRAMES 75
#define BOSS_FLASH_FRAMES 6
#define BOSS_QUIET_FRAMES 50
#define SCENE_FRAMES 150
#define GAMEOVER_FRAMES 150
#define SCENE_SKIP_FRAMES 25
#define SHOT_W 8
#define SHOT_H 4
#define CHARGED_SHOT_W 16
#define CHARGED_SHOT_H 10
#define HOSTILE_W 6
#define HOSTILE_H 8
/* Minimum analytic vertical distance beyond HOSTILE_H between bullets that
 * share a sprite channel: one blank line, one spare, one for half-step rounding. */
#define HOSTILE_GAP 3
#define HOSTILE_VX -3
#define FAN_SPACING 22
#define FAN_STAGGER 6
/* Player shots and pickups are BOBs; ACE saves one extra aligned word. */
#define BOB_MAX_X (WORLD_W - 17)
#define ENEMY_COUNT 18
#define SHOT_COUNT 12
#define HOSTILE_COUNT 32
#define BONUS_COUNT 4
#define BONUS_KIND_COUNT 5
#define BONUS_LIFETIME 400
#define WAVE_TRACK_COUNT ENEMY_COUNT
#define ENEMY_SPRITE_CAPACITY 6
#define FORMATION_SIZE 6
#define BULLET_SPRITE_CAPACITY 16
#define LEVEL_COUNT 4
#define FIRE_INTERVAL 8
#define CHARGE_FRAMES 50
#define RESPAWN_FRAMES 100

typedef enum {
	TITLE, PLAY, BOSS, CLEAR, GAMEOVER, WIN,
	SECTOR_INTRO, BOSS_INTRO, BOSS_DYING, HERO_DYING
} tPhase;
enum { FX_ENEMY, FX_ASTEROID, FX_HERO, FX_BOSS };
enum {
	EVENT_SHOT = 1, EVENT_EXPLOSION = 2, EVENT_HIT = 4,
	EVENT_LEVEL = 8, EVENT_CHARGE = 16, EVENT_LANCE = 32,
	EVENT_BONUS_DROP = 64, EVENT_BONUS_PICKUP = 128
};
enum { ENEMY_SCOUT, ENEMY_WEAVER, ENEMY_GUNNER, ENEMY_DART, ENEMY_BOSS, ENEMY_ASTEROID };
enum { SHOT_NORMAL, SHOT_CHARGED };
enum { BONUS_POWER, BONUS_SPEED, BONUS_SHIELD, BONUS_LIFE, BONUS_FIRE };

typedef struct { int8_t dx, dy; uint8_t fire; } tInput;

typedef struct {
	int16_t x, y;
	uint8_t active, kind, hp;
	/* Enemies use attached pair 4/5 (rescheduled every tick). Hostile bullets
	 * own channel 6/7 in PLAY or 4..7 in BOSS for their whole life: a bullet is only thrown if its
	 * straight trajectory never comes within HOSTILE_H + HOSTILE_GAP lines of
	 * another bullet on that channel, so every thrown bullet stays displayable.
	 * Player shots and pickups are BOBs and always have channel zero.
	 * Renderer may clear visible on a hardware/BOB drop: this suppresses
	 * collisions on the next tick. For hostiles, age = remaining-life bound. */
	uint8_t visible, channel;
	int8_t vx, vy;
	uint16_t age;
	/* One-based tracking slot; zero means untracked. Never reused while live. */
	uint8_t waveId;
	uint8_t waveMember; /* Fixed lane 0..5 for the entire life; asteroids never fire. */
	uint8_t fireCountdown; /* Combat ticks, independent of movement/age. */
} tEntity;

typedef struct {
	uint8_t planned, spawned, remaining, killed, failed;
} tWaveTrack;

typedef struct {
	int16_t x, y;
	uint16_t hp, maxHp, tick;
	uint8_t active, visible, flashTicks, cooldown, kind;
} tBoss;

typedef struct {
	int16_t x, y;
	uint8_t active, kind, age, lifetime;
} tEffect;

typedef struct {
	int16_t x, y;
	uint32_t frame, score, simFrame;
	uint32_t enemyMotionFrame;
	uint8_t enemyAccumulator, titleInputBlocked;
	int8_t moveRemainderX, moveRemainderY;
	uint8_t level, lives;
	tPhase phase;
	tPhase resumePhase;
	uint8_t sceneId, sceneReady, sceneArmed;
	/* Renderer preparation stalls simulation, never the video/effect clock. */
	uint8_t presentationBusy;
	uint8_t manualPause, pauseFireBlocked, heroBlink;
	uint16_t sceneEpoch;
	tEntity enemies[ENEMY_COUNT], shots[SHOT_COUNT], hostile[HOSTILE_COUNT];
	tEntity pickups[BONUS_COUNT];
	uint8_t weaponLevel, shotLevel, speedLevel, shield, bonusCycle;
	tWaveTrack waves[WAVE_TRACK_COUNT];
	uint8_t events, fireCooldown, charge, fireWasDown;
	int8_t titleDirection;
	/* stageFrame is wrapping elapsed telemetry, never a boss gate.
	 * wave counts successful complete formations in this sector. */
	uint16_t stageFrame, phaseFrame, waveTimer, wave;
	uint8_t bossQuietTicks;
	uint16_t invulnerable;
	tBoss boss;
	tEffect effects[EFFECT_COUNT];
} tGameState;

extern const char *const g_stageNames[LEVEL_COUNT];
extern const uint16_t g_stageFrames[LEVEL_COUNT];
/* g_stageFrames retains historical timer cutoffs for probes, not boss gating. */
extern const uint16_t g_stageWaveQuota[LEVEL_COUNT];

/* One update = 1/50s; no allocations/hardware/randomness. Init enters TITLE.
 * Fresh fire press starts from TITLE via SECTOR_INTRO. GAMEOVER returns to
 * TITLE after 150 ready ticks (fresh-press skip after 25); held input is consumed.
 * WIN requires the acknowledged scene skip guard. Holding only charges; release
 * after 1..49 combat ticks fires a normal volley, after 50 a centered 6-damage
 * 16x10 lance at 4px/tick. Neutral with zero charge never fires.
 * shotLevel 0/1/2 selects normal offsets 0 / -6,+6 / -8,0,+8 (8x4, vx6, vy0).
 * Each normal shot deals 1+weaponLevel damage. Successful normal volleys are
 * separated by at least 8 combat ticks; early releases are discarded.
 * Allocation preflights the entire volley; only success emits EVENT_SHOT
 * (also EVENT_LANCE for charged fire). EVENT_CHARGE occurs once at tick 50.
 * First wave at tick 25, then due every 150/140/130/120 ticks by stage, waiting
 * for all enemies and their tracker to retire. Every formation has six
 * homogeneous members, including six passive asteroids every fifth wave.
 * Fixed lanes span y56..216 with at least two blank scanlines between bodies.
 * Boss entry waits for 18/21/24/27 complete spawns AND final retirement,
 * then 50 full combat ticks with both projectile pools empty. New shots reset
 * the quiet interval; preparation and death pause it. Combat continues in PLAY;
 * elapsed time cannot force entry. Allocation is preflighted atomically.
 * Partial/escaped waves cannot award bonuses. Pickups expire after 400 ticks or
 * leaving the screen; a full pool replaces the oldest. Upgrade caps are 2,
 * lives cap at 5; stages preserve upgrades, death reduces power/fire/speed.
 * Four pickup slots serve five kinds, explicitly cycling P,F,S,R,L.
 * Hero bounds x 0..288, y 56..192; speed = (3 + speedLevel)/2.
 * Central 8x8 hurtbox; pickups use the full body. Each hostile is one 6x8
 * bullet moving at half its stored velocity (vx -3, vy -2..2).
 * Enemy motion/age and boss tick use 16/17/18/20 steps per 20 combat ticks.
 * Independent firing countdowns use combat ticks: ships 96/76/64/52 after
 * 50 + member*10; bosses 64/52/44/36 after 50. Ship fans (other/gunner) are
 * 3/5,5/5,5/7,7/7; boss fans 5/7/7/9 with the final lane alternative retained.
 * Rays are FAN_SPACING apart vertically, outer rays FAN_STAGGER behind
 * per step, so 14px gaps always open. Asteroids are passive. Rays outside
 * the corridor, or that could not stay visible on owned channels, are not fired.
 * events reset every tick. Return 1 for refresh, 0 on unchanged GAMEOVER/TITLE
 * screens. NULL input = neutral; NULL state is safely ignored. */
void logicInit(tGameState *pState);
/* Reset gameplay, preserving lifetime clocks/epoch and consuming held title input.
 * Replaces this tick's update so EVENT_LEVEL survives through rendering/audio. */
void logicReturnToTitle(tGameState *pState, const tInput *pInput);
uint8_t logicUpdate(tGameState *pState, const tInput *pInput);

/* Acknowledge only after the scene for this epoch has actually been displayed.
 * Repeated/stale acknowledgements do not reset its timer. Scenes 3*level+0/1/2
 * are sector/arrival/defeat; WIN is scene 12. Dwell/skip count acknowledged
 * video ticks, with release then fresh press after SCENE_SKIP_FRAMES.
 * WIN remains on screen after its dwell until a fresh press starts a new game.
 * frame advances on every update; simFrame advances only on combat updates.
 * Death effects retain origins and freeze live pools for exactly 40/75 ticks.
 * Small effects use slots 0..5 (full pool replaces oldest); hero/boss reserve 6/7.
 * Renderers may clear boss.visible to suppress next-tick damage/contact. */
void logicScenePresented(tGameState *pState, uint16_t epoch);
void logicSetPresentationBusy(tGameState *pState, uint8_t busy);
/* Caller supplies a P key edge. Fire must be released after resume before reuse. */
void logicTogglePause(tGameState *pState);
uint8_t logicCombatActive(const tGameState *pState);
uint8_t logicWorldScrolling(const tGameState *pState);
/* Hardware channel bitmask, independent of bullet kind/palette. */
uint8_t logicHostileChannelMask(const tGameState *pState);

#endif
