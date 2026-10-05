/* Host-only public-API joystick search and deterministic replay.
 * cc -std=c99 -Wall -Wextra -Werror -Igame/src tools/plan-bonus-flight.c \
 *    game/src/logic.c -o game/build/plan-bonus-flight
 * Run from repository root; --write regenerates scenarios and checked-in evidence.
 * Optional: -g -fsanitize=address,undefined -fno-omit-frame-pointer.
 * Only public lifecycle APIs write game state. No emulator is launched.
 */
#include "../game/src/logic.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_TICKS 1700
typedef struct { int tolerance, aim, home, evade; } Policy;
typedef struct { int x, y, right, bottom; } Rect;
typedef struct {
	unsigned kill1, drop, capture, pickup, power, asteroid, count;
	unsigned lives, weapon, score;
	unsigned dropStage, pickupStage, asteroidStage, death, deathStage;
	Rect oldBob, dropBob;
	int asteroidX[6], asteroidY[6];
} Evidence;

static int8_t steer(int delta, int tolerance) {
	return delta < -tolerance ? -1 : (delta > tolerance ? 1 : 0);
}

static tInput control(const tGameState *s, Policy p) {
	const tEntity *target = NULL;
	tInput input = {0, 0, (s->simFrame & 7) == 0};
	for(int i = 0; i < BONUS_COUNT; ++i)
		if(s->pickups[i].active) { target = &s->pickups[i]; break; }
	if(target) input.dx = steer(target->x - s->x, p.tolerance);
	else {
		input.dx = steer(p.home - s->x, p.tolerance);
		for(int i = 0; i < ENEMY_COUNT; ++i) {
			const tEntity *e = &s->enemies[i];
			if(e->active && e->x > s->x && (!target || e->x < target->x)) target = e;
		}
	}
	if(target) input.dy = steer(target->y + p.aim - s->y, p.tolerance);
	return input;
}

static void start(tGameState *s) {
	const tInput fire = {0, 0, 1};
	logicInit(s);
	logicUpdate(s, &fire);
	if(s->phase != SECTOR_INTRO) { fputs("start did not enter sector intro\n", stderr); exit(EXIT_FAILURE); }
	logicScenePresented(s, s->sceneEpoch);
	for(unsigned tick = 0; tick < SCENE_FRAMES; ++tick) logicUpdate(s, NULL);
	if(s->phase != PLAY || s->simFrame || s->stageFrame) {
		fputs("start did not reach untouched combat\n", stderr); exit(EXIT_FAILURE);
	}
}

static int firstWaveCleared(const tGameState *s) {
	const tWaveTrack *w = &s->waves[0];
	return s->wave == 1 && w->planned == 6 && w->spawned == 6 &&
		w->killed == 6 && !w->remaining && !w->failed;
}

static unsigned visibleKind(const tEntity *entities, unsigned count, unsigned kind) {
	unsigned visible = 0;
	for(unsigned i = 0; i < count; ++i)
		if(entities[i].active && entities[i].visible && entities[i].kind == kind) ++visible;
	return visible;
}

static Rect rect(int x, int y, int w, int h) {
	return (Rect){x, y, x + w, y + h};
}

static void include(Rect *a, Rect b) {
	if(a->right == 0) { *a = b; return; }
	if(b.x < a->x) a->x = b.x;
	if(b.y < a->y) a->y = b.y;
	if(b.right > a->right) a->right = b.right;
	if(b.bottom > a->bottom) a->bottom = b.bottom;
}

static int overlaps(Rect a, Rect b) {
	return a.x < b.right && b.x < a.right && a.y < b.bottom && b.y < a.bottom;
}

static int clearPool(Rect roi, const tEntity *pool, unsigned count, int w, int h) {
	for(unsigned i = 0; i < count; ++i) {
		const tEntity *e = &pool[i];
		if(e->active && e->visible && overlaps(roi, rect(e->x, e->y, w, h))) return 0;
	}
	return 1;
}

static int clearRoi(const tGameState *s, Rect roi) {
	for(unsigned i = 0; i < EFFECT_COUNT; ++i) {
		const tEffect *fx = &s->effects[i];
		int w = fx->kind == FX_BOSS ? 64 : (fx->kind == FX_HERO ? 32 : 16);
		int h = fx->kind == FX_BOSS ? 48 : w;
		if(fx->active && overlaps(roi, rect(fx->x, fx->y, w, h))) return 0;
	}
	/* Conservative charged dimensions also cover normal shots. */
	return !overlaps(roi, rect(s->x, s->y, PLAYER_W, PLAYER_H)) &&
		clearPool(roi, s->enemies, ENEMY_COUNT, 16, 16) &&
		clearPool(roi, s->shots, SHOT_COUNT, 16, 10) &&
		clearPool(roi, s->hostile, HOSTILE_COUNT, HOSTILE_W, HOSTILE_H) &&
		clearPool(roi, s->pickups, BONUS_COUNT, 16, 16);
}

static void bobBounds(const tGameState *s, Evidence *e, unsigned tick) {
	for(int i = 0; i < BONUS_COUNT; ++i) {
		const tEntity *b = &s->pickups[i];
		if(!b->active || !b->visible || b->kind != BONUS_POWER) continue;
		/* ACE saves two aligned words for a 16px BOB, including spill word. */
		include(&e->oldBob, rect(b->x & ~15, b->y, 32, 16));
		/* BOBs are drawn before logic: capture at t uses state t-1. */
		if(tick + 1 == e->capture) e->dropBob = rect(b->x, b->y, 16, 16);
	}
}

static int observe(const tGameState *s, Evidence *e, unsigned tick) {
	if((s->phase != PLAY && s->phase != HERO_DYING) || !s->lives || s->stageFrame > tick) return 0;
	if(s->phase == HERO_DYING && !e->death) { e->death = tick; e->deathStage = s->stageFrame; }
	if(e->death && tick >= e->death && tick < e->death + HERO_DEATH_FRAMES &&
		(s->phase != HERO_DYING || s->phaseFrame != tick - e->death ||
		 s->stageFrame != e->deathStage || s->simFrame != e->deathStage)) return 0;
	if(e->death && tick == e->death + HERO_DEATH_FRAMES &&
		(s->phase != PLAY || s->phaseFrame || s->stageFrame != e->deathStage)) return 0;
	if(!e->drop && s->wave == 1 && s->waves[0].killed == 1 && !e->kill1) e->kill1 = tick;
	if(!e->drop && (s->events & EVENT_BONUS_DROP)) {
		if(!firstWaveCleared(s) || !e->kill1) return 0;
		/* The final member's blast shares the pickup origin for 16 ticks. */
		e->drop = tick; e->dropStage = s->stageFrame; e->capture = tick + 18;
	}
	if(!e->pickup && (s->events & EVENT_BONUS_PICKUP)) {
		if(!e->drop || tick <= e->capture || s->weaponLevel != 1) return 0;
		e->pickup = tick; e->pickupStage = s->stageFrame; e->power = tick + 2;
	}
	if(tick == e->capture && !visibleKind(s->pickups, BONUS_COUNT, BONUS_POWER)) return 0;
	if(!e->pickup) bobBounds(s, e, tick);
	if(e->capture && tick + 1 == e->capture) {
		Rect roi = e->dropBob;
		if(!clearPool(roi, s->shots, SHOT_COUNT, 16, 10) ||
			!clearPool(roi, s->enemies, ENEMY_COUNT, 16, 16) ||
			!clearPool(roi, s->hostile, HOSTILE_COUNT, HOSTILE_W, HOSTILE_H) ||
			overlaps(roi, rect(s->x, s->y, PLAYER_W, PLAYER_H))) return 0;
	}
	if(!e->drop && s->wave == 1 && s->waves[0].failed) return 0;
	return 1;
}

static unsigned plan(tInput *inputs, Policy policy, Evidence *e) {
	tGameState s;
	unsigned asteroidStart = 0;
	memset(e, 0, sizeof(*e));
	start(&s);
	for(unsigned tick = 1; tick <= MAX_TICKS; ++tick) {
		tInput in = control(&s, policy);
		/* Once P is collected, move behind the left-travelling formations. */
		if(e->pickup && tick > e->power)
			in = (tInput){steer(288 - s.x, 1), steer(policy.evade - s.y, 1), (s.simFrame & 7) == 0};
		if(e->drop && tick <= e->capture) in = (tInput){0, 0, (s.simFrame & 7) == 0};
		if(e->pickup && tick <= e->power) in = (tInput){0, 0, 0};
		inputs[tick - 1] = in;
		logicUpdate(&s, &in);
		if(!observe(&s, e, tick)) return 0;
		if(e->pickup && s.wave == 5 && visibleKind(s.enemies, ENEMY_COUNT, ENEMY_ASTEROID) == 6) {
			if(!asteroidStart) asteroidStart = tick;
			if(tick >= asteroidStart + 2) {
				e->asteroid = e->count = tick;
				e->asteroidStage = s.stageFrame;
				e->lives = s.lives; e->weapon = s.weaponLevel; e->score = s.score;
				unsigned member = 0;
				for(unsigned i = 0; i < ENEMY_COUNT; ++i) {
					const tEntity *a = &s.enemies[i];
					if(!a->active || !a->visible || a->kind != ENEMY_ASTEROID) continue;
					e->asteroidX[member] = a->x + 8;
					e->asteroidY[member++] = a->y + 8;
				}
				return tick;
			}
		} else asteroidStart = 0;
	}
	return 0;
}

/* Independent open-loop replay of every emitted tick; no controller feedback. */
static int replay(const tInput *inputs, const Evidence *expected) {
	tGameState s;
	Evidence e = {0};
	start(&s);
	for(unsigned tick = 1; tick <= expected->count; ++tick) {
		logicUpdate(&s, &inputs[tick - 1]);
		if(!observe(&s, &e, tick)) return 0;
	}
	return e.kill1 == expected->kill1 && e.drop == expected->drop &&
		e.dropStage == expected->dropStage && e.pickupStage == expected->pickupStage &&
		e.death == expected->death && e.deathStage == expected->deathStage &&
		s.stageFrame == expected->asteroidStage &&
		e.pickup == expected->pickup && e.capture == expected->capture &&
		s.wave == 5 && visibleKind(s.enemies, ENEMY_COUNT, ENEMY_ASTEROID) == 6 &&
		s.lives == expected->lives && s.weaponLevel == expected->weapon && s.score == expected->score;
}

static int replayRestore(const tInput *inputs, unsigned count, const Evidence *expected) {
	tGameState s;
	Evidence e = {0};
	unsigned clean = 0;
	start(&s);
	for(unsigned tick = 1; tick <= count; ++tick) {
		logicUpdate(&s, &inputs[tick - 1]);
		if(!observe(&s, &e, tick)) return 0;
		clean = clearRoi(&s, expected->oldBob) ? clean + 1 : 0;
	}
	return clean >= 3 && e.drop == expected->drop && e.pickup == expected->pickup &&
		e.oldBob.x == expected->oldBob.x && e.oldBob.right == expected->oldBob.right &&
		e.oldBob.y == expected->oldBob.y && e.oldBob.bottom == expected->oldBob.bottom;
}

static unsigned restorePlan(const tInput *inputs, tInput *restore, const Evidence *e) {
	tGameState s;
	unsigned clearTicks = 0;
	start(&s);
	for(unsigned tick = 1; tick <= e->pickup + 80; ++tick) {
		tInput in = tick <= e->power ? inputs[tick - 1] : (tInput){0, 1, 0};
		restore[tick - 1] = in;
		logicUpdate(&s, &in);
		if((s.phase != PLAY && s.phase != HERO_DYING) || !s.lives) return 0;
		clearTicks = clearRoi(&s, e->oldBob) ? clearTicks + 1 : 0;
		/* Three clean host states cover sprite/copper presentation latency. */
		if(tick >= e->power + 20 && clearTicks >= 3) return tick;
	}
	return 0;
}

static int sameInput(tInput a, tInput b) {
	return a.dx == b.dx && a.dy == b.dy && a.fire == b.fire;
}

static void emitInput(FILE *out, tInput input, unsigned count) {
	if(!input.dx && !input.dy && !input.fire) { fprintf(out, "wait %u\n", count); return; }
	const char *sep = "";
	fputs("press ", out);
	if(input.dy) { fputs(input.dy < 0 ? "up" : "down", out); sep = "+"; }
	if(input.dx) { fprintf(out, "%s%s", sep, input.dx < 0 ? "left" : "right"); sep = "+"; }
	if(input.fire) fprintf(out, "%sfire", sep);
	fprintf(out, " %u\n", count);
}

static void emit(FILE *out, const tInput *inputs, unsigned count, const Evidence *e, int restore) {
	fprintf(out, "# Generated by tools/plan-bonus-flight.c; public logic API only.\n"
		"# Host verified; emulator/pixel verification pending.\n"
		"# First-wave first kill=%u, final kill=%u (six members); drop capture=%u; pickup=%u; power capture=%u.\n",
		e->kill1, e->drop, e->capture, e->pickup, e->power);
	fprintf(out, "# Final combat-relative video tick=%u%s\n", count, restore ? "; restoration ROI in game/tests/bonus-flight.json" : "");
	fputs("wait-serial \"AGK title_ready\" 600\npress fire 1\nwait-serial \"AGK combat_ready\" 600\n", out);
	for(unsigned begin = 0; begin < count;) {
		unsigned end = begin + 1;
		while(end < count && sameInput(inputs[begin], inputs[end])) ++end;
		if(begin < e->capture && end > e->capture) end = e->capture;
		if(begin < e->power && end > e->power) end = e->power;
		if(e->death && begin < e->death + 10 && end > e->death + 10) end = e->death + 10;
		if(e->death && begin < e->death + 30 && end > e->death + 30) end = e->death + 30;
		emitInput(out, inputs[begin], end - begin);
		begin = end;
		if(end == e->capture) {
			fputs("screenshot bonus_drop\n", out);
			/* Interior runs remain the same color across one pixel of latency. */
			fprintf(out, "expect-color bonus_drop %d %d 0xFA6\n", e->dropBob.x + 8, e->dropBob.y + 2);
			fprintf(out, "expect-color bonus_drop %d %d 0xFFF\n", e->dropBob.x + 6, e->dropBob.y + 4);
		}
		if(end == e->power) fputs("screenshot bonus_power\n", out);
		if(e->death && end == e->death + 10) fputs("screenshot hero_dying\n", out);
		if(e->death && end == e->death + 30) fputs("screenshot hero_dying_late\n", out);
	}
	if(restore) fputs("screenshot bob_restored\n", out);
	else if(count == e->asteroid) {
		fputs("screenshot asteroids\n", out);
		/* Inspect each member's orange core, allowing sprite presentation latency. */
		for(unsigned i = 0; i < 6; ++i)
			fprintf(out, "expect-color asteroids %d %d 0xFA6 near 2\n", e->asteroidX[i], e->asteroidY[i]);
	}
	fputs("expect-serial \"AGK bonus_drop\"\nexpect-serial \"AGK bonus_pickup\"\n"
		"expect-serial \"weapon=1\"\nexpect-no-serial \"ERR|STACK SMASHED|allocation failure\"\n", out);
	fprintf(out, "expect-serial \"phase=1 .*weapon=1 .*stage=%u \"\n", e->pickupStage);
	fprintf(out, "expect-serial \"phase=1 .*score=600 .*wave=1 .*enemies=0 .*stage=%u \"\n", e->dropStage);
	fputs("expect-serial \"wave=1 .*enemies=6\"\n"
		"expect-no-serial \"bullet_hidden=[1-9]\"\n", out);
	if(!restore && count == e->asteroid)
		fprintf(out, "expect-serial \"phase=1 .*lives=%u .*wave=5 .*enemies=6\"\n", e->lives);
	if(e->death && count > e->death + 30)
		fprintf(out, "expect-serial \"phase=9 .*effects=[1-9] .*stage=%u sim=%u\"\n", e->deathStage, e->deathStage);
}

static void writeScenario(const char *path, const tInput *inputs, unsigned count, const Evidence *e, int restore) {
	FILE *out = fopen(path, "w");
	if(!out) { perror(path); exit(EXIT_FAILURE); }
	emit(out, inputs, count, e, restore);
	if(fclose(out)) { perror(path); exit(EXIT_FAILURE); }
}

/* Check the generated text itself, including fire-off waits and capture timing. */
static int checkScenario(const char *path, const tInput *inputs, unsigned count, const Evidence *e) {
	FILE *in = fopen(path, "r");
	char line[512], keys[64];
	unsigned ticks, elapsed = 0, prelude = 0, captures = 0;
	if(!in) return 0;
	while(fgets(line, sizeof(line), in)) {
		tInput input = {0, 0, 0};
		if(sscanf(line, "screenshot %63s", keys) == 1) {
			unsigned expected = !strcmp(keys, "bonus_drop") ? e->capture :
				(!strcmp(keys, "bonus_power") ? e->power :
				(!strcmp(keys, "hero_dying") ? e->death + 10 :
				(!strcmp(keys, "hero_dying_late") ? e->death + 30 : count)));
			if(elapsed != expected) { fclose(in); return 0; }
			++captures;
			continue;
		}
		if(prelude < 3) {
			const char *expected[] = {"wait-serial \"AGK title_ready\" 600\n", "press fire 1\n", "wait-serial \"AGK combat_ready\" 600\n"};
			if(line[0] == '#') continue;
			if(strcmp(line, expected[prelude++])) { fclose(in); return 0; }
			continue;
		}
		if(sscanf(line, "press %63s %u", keys, &ticks) == 2) {
			input.dx = strstr(keys, "left") ? -1 : (strstr(keys, "right") ? 1 : 0);
			input.dy = strstr(keys, "up") ? -1 : (strstr(keys, "down") ? 1 : 0);
			input.fire = strstr(keys, "fire") != NULL;
		} else if(sscanf(line, "wait %u", &ticks) != 1) continue;
		for(unsigned t = 0; t < ticks; ++t)
			if(elapsed >= count || !sameInput(input, inputs[elapsed++])) { fclose(in); return 0; }
	}
	fclose(in);
	return elapsed == count && captures == (count == e->power ? 2u : 3u) +
		(e->death && count > e->death + 30 ? 2u : 0u);
}

static void metadata(const Evidence *e, unsigned restored) {
	FILE *out = fopen("game/tests/bonus-flight.json", "w");
	if(!out) { perror("bonus-flight.json"); exit(EXIT_FAILURE); }
	fprintf(out, "{\"clock\":\"logic video ticks since combat_ready, not elapsed PAL vblanks\",\"death_capture_phase_frames\":[10,30],\"death_duration\":40,\"drop_stage\":%u,\"pickup_stage\":%u,\"asteroid_stage\":%u,\"death_tick\":%u,\"death_stage\":%u,\"kill1\":%u,\"drop\":%u,\"drop_capture\":%u,\"pickup\":%u,\"power_capture\":%u,"
		"\"restore_capture\":%u,\"asteroid_capture\":%u,\"roi\":[%d,%d,%d,%d],\"drop_bob\":[%d,%d,%d,%d]}\n",
		e->dropStage, e->pickupStage, e->asteroidStage, e->death, e->deathStage,
		e->kill1, e->drop, e->capture, e->pickup, e->power, restored, e->asteroid,
		e->oldBob.x, e->oldBob.y, e->oldBob.right, e->oldBob.bottom,
		e->dropBob.x, e->dropBob.y, e->dropBob.right, e->dropBob.bottom);
	if(fclose(out)) { perror("bonus-flight.json"); exit(EXIT_FAILURE); }
}

int main(int argc, char **argv) {
	tInput inputs[MAX_TICKS], restore[MAX_TICKS];
	Evidence e;
	if(argc > 2 || (argc == 2 && strcmp(argv[1], "--write"))) {
		fputs("usage: plan-bonus-flight [--write]\n", stderr); return EXIT_FAILURE;
	}
	for(int home = 16; home <= 208; home += 4)
	for(int aim = -16; aim <= 12; ++aim)
	for(int tolerance = 1; tolerance <= 8; ++tolerance)
	for(int evade = 56; evade <= 192; evade += 8) {
		Policy p = {tolerance, aim, home, evade};
		if(!plan(inputs, p, &e)) continue;
		unsigned restored = restorePlan(inputs, restore, &e);
		if(!restored) continue;
		if(!replay(inputs, &e) || !replayRestore(restore, restored, &e)) {
			fputs("UNEXPECTED FAILURE: recorded input replay differs\n", stderr); return EXIT_FAILURE;
		}
		printf("# policy home=%d aim=%d tolerance=%d evade=%d\n", home, aim, tolerance, evade);
		printf("# VERIFIED first_kill=%u final_kill=%u drop=%u pickup=%u power=%u restore=%u asteroids=%u lives=%u weapon=%u score=%u\n",
			e.kill1, e.drop, e.capture, e.pickup, e.power, restored, e.asteroid, e.lives, e.weapon, e.score);
		printf("# RESTORE ROI [%d,%d,%d,%d) DROP BOB [%d,%d,%d,%d)\n",
			e.oldBob.x, e.oldBob.y, e.oldBob.right, e.oldBob.bottom,
			e.dropBob.x, e.dropBob.y, e.dropBob.right, e.dropBob.bottom);
		if(argc == 2) {
			writeScenario("game/tests/bonus.agk", inputs, e.power, &e, 0);
			writeScenario("game/tests/asteroids.agk", inputs, e.count, &e, 0);
			writeScenario("game/demo/showcase.agk", inputs, e.count, &e, 0);
			writeScenario("game/demo/asteroids.agk", inputs, e.count, &e, 0);
			writeScenario("game/tests/bob_restore.agk", restore, restored, &e, 1);
			metadata(&e, restored);
			if(!checkScenario("game/tests/bonus.agk", inputs, e.power, &e) ||
				!checkScenario("game/tests/asteroids.agk", inputs, e.count, &e) ||
				!checkScenario("game/demo/showcase.agk", inputs, e.count, &e) ||
				!checkScenario("game/demo/asteroids.agk", inputs, e.count, &e) ||
				!checkScenario("game/tests/bob_restore.agk", restore, restored, &e)) {
				fputs("UNEXPECTED FAILURE: emitted scenario differs from verified inputs\n", stderr);
				return EXIT_FAILURE;
			}
			puts("# REPLAY PASS: all five emitted input files and capture ticks match; restoration replay clean");
		} else emit(stdout, inputs, e.count, &e, 0);
		return EXIT_SUCCESS;
	}
	fputs("No policy met first-wave, pickup, restoration and live-asteroid requirements\n", stderr);
	return EXIT_FAILURE;
}
