#ifndef ASTRA_HUD_BOB_TRACE_H
#define ASTRA_HUD_BOB_TRACE_H

/* Diagnostic IDs only. No ACE or hardware dependency in an OFF build. */
enum {
    HB_DAMAGE_END = 33, HB_SPEED_END, HB_SHIELD_END, HB_FIRE_END,
    HB_SCORE_END, HB_LIVES_END, HB_LABELS_END, HB_CHARGE_END, HB_BOSS_HUD_END,
    HB_BOBS_BEGIN, HB_BOSS_QUEUE_END, HB_EFFECTS_QUEUE_END, HB_PICKUPS_END,
    HB_SHOTS_END, HB_FLUSH_END, HB_WAIT_END, HB_STAMP_COUNT
};
enum {
    HO_DAMAGE, HO_SPEED, HO_SHIELD, HO_FIRE, HO_SCORE_CALLS, HO_SCORE_CHANGED,
    HO_SCORE_GLYPHS, HO_SCORE_CLEARS, HO_LIVES, HO_LABEL_PAIRS, HO_CHARGE_CLEAR,
    HO_CHARGE_FILL, HO_BOSS_LABEL_CLEAR, HO_BOSS_LABEL_DRAW, HO_BOSS_BAR_CLEAR,
    HO_BOSS_BAR_FILL, HO_COUNT
};
enum { HB_BOSS, HB_SMALL_FX, HB_HERO_FX, HB_BOSS_FX, HB_PICKUP,
       HB_SHOT, HB_LANCE, HB_CATEGORY_COUNT };

#ifdef ASTRA_HUD_BOB_DETAIL
extern unsigned char galaxyTraceTarget;
extern unsigned short hudBobOperations[HO_COUNT];
extern unsigned short hudBobPushes[HB_CATEGORY_COUNT];
extern unsigned short hudBobUnaligned[HB_CATEGORY_COUNT];
void galaxyTraceMarkTarget(unsigned char mark);
#define hudBobMark(mark) do { if(galaxyTraceTarget) galaxyTraceMarkTarget(mark); } while(0)
#define hudBobOperation(op, amount) do { if(galaxyTraceTarget) hudBobOperations[op] += (amount); } while(0)
/* Called only AFTER bobPush has enqueued an eligible object. No clocks/waits. */
#define hudBobPushed(category, x) do { if(galaxyTraceTarget) { \
    ++hudBobPushes[category]; \
    if((x) & 15) ++hudBobUnaligned[category]; \
} } while(0)
#else
#define hudBobMark(mark) ((void)0)
#define hudBobOperation(op, amount) ((void)0)
#define hudBobPushed(category, x) ((void)0)
#endif
#endif
