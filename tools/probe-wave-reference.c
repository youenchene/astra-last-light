/* Freeze the time-based campaign's wave counts before quota-based progression.
 * cc -std=c99 -Wall -Wextra -Werror -Igame/src tools/probe-wave-reference.c \
 *    game/src/logic.c -o game/build/probe-wave-reference
 * Run with the SHA256 of the original logic.c as the only argument.
 * Test-only invulnerability lets a stationary, non-firing pilot observe all
 * spawns; no enemies, timers, movement or progression counters are injected.
 * After progression changes this is historical tooling, not a regression test.
 */
#include "logic.h"
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
	const tInput idle = {0, 0, 0}, right = {1, 0, 0}, fire = {0, 0, 1};
	unsigned counts[LEVEL_COUNT], ticks[LEVEL_COUNT][64];
	if(argc != 2 || strlen(argv[1]) != 64 ||
		strspn(argv[1], "0123456789abcdef") != 64) {
		fputs("usage: probe-wave-reference ORIGINAL_LOGIC_C_SHA256\n", stderr);
		return 1;
	}
	for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
		tGameState state;
		logicInit(&state);
		for(unsigned i = 0; i < level; ++i) {
			logicUpdate(&state, &right);
			logicUpdate(&state, &idle);
		}
		logicUpdate(&state, &fire);
		unsigned count = 0;
		while(state.phase == PLAY && state.stageFrame <= g_stageFrames[level]) {
			unsigned before = state.wave;
			state.invulnerable = 2; /* Fixture only: observe the entire old stage. */
			logicUpdate(&state, &idle);
			if(state.wave == before) continue;
			if(state.wave != before + 1 || count == 64) return 1;
			ticks[level][count++] = state.stageFrame;
		}
		if(state.phase != BOSS || state.stageFrame != g_stageFrames[level]) {
			fputs("Reference requires the original time-based progression\n", stderr);
			return 1;
		}
		counts[level] = count;
	}
	printf("{\n  \"original_logic_c_sha256\": \"%s\",\n", argv[1]);
	puts("  \"policy\": \"Stationary no-fire pilot after start; fixture invulnerability only; includes every spawn before original boss cutoff\",");
	puts("  \"one_live_formation\": true,\n  \"sectors\": [");
	for(unsigned level = 0; level < LEVEL_COUNT; ++level) {
		printf("    {\"sector\":%u,\"original_duration_ticks\":%u,\"waves\":%u,\"quota\":%u,\"spawn_ticks\":[",
			level + 1, g_stageFrames[level], counts[level], counts[level] * 3);
		for(unsigned i = 0; i < counts[level]; ++i)
			printf("%s%u", i ? "," : "", ticks[level][i]);
		printf("]}%s\n", level + 1 == LEVEL_COUNT ? "" : ",");
	}
	puts("  ]\n}");
	return 0;
}
