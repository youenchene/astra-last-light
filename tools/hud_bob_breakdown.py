"""Strict bounded HUD/BOB partitions; queue time is not per-category draw time."""
import re
from frame_breakdown import parse as parse_outer, partition

HUD = [(3,'start'), (33,'damage'), (34,'speed'), (35,'shield'), (36,'fire'),
       (37,'score'), (38,'lives'), (39,'charge_labels'), (40,'charge_bar'),
       (41,'boss_label_bar'), (4,'history_return')]
BOB = [(4,'start'), (42,'call_setup'), (43,'boss_queue'), (44,'effects_queue'),
       (45,'pickups_queue'), (46,'shots_queue'), (47,'shared_flush'),
       (48,'terminal_wait'), (5,'close_return')]
OPS = ['damage','speed','shield','fire','score_calls','score_changed','score_glyphs',
       'score_clears','lives','label_pairs','charge_clear','charge_fill',
       'boss_label_clear','boss_label_draw','boss_bar_clear','boss_bar_fill']
# From actual bobInit widths/heights and four interleaved planes. No pixel masking.
GEOMETRY = [('boss',64,48,1), ('small_fx',16,16,6), ('hero_fx',32,32,1),
            ('boss_fx',64,48,1), ('pickup',16,16,4), ('shot',16,4,12), ('lance',16,10,4)]


def work_area(category, pushes, unaligned):
    name,w,h,capacity = GEOMETRY[category]
    if not 0 <= unaligned <= pushes <= capacity:
        raise ValueError('invalid successful-push counts')
    # ACE saves one extra word even when aligned. Masked draw width depends on X.
    save = pushes * ((w+15)//16+1) * h * 4
    masked = (pushes * (w//16) + unaligned) * h * 4
    return dict(category=name,pushes=pushes,unaligned=unaligned,
                save_word_area=save,masked_word_area=masked)


def parse(text, expected, detailed=True):
    rows = parse_outer(text,expected,False)
    valid = {f:{} for f in rows}
    operations = {f:{} for f in rows}
    bobs = {f:{} for f in rows}
    headers = {}
    for line in text.splitlines():
        d = {k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
        if 'stamp_frame' in d:
            if d['valid'] not in (0,1): raise ValueError('invalid stamp validity')
            valid[d['stamp_frame']][d['index']] = d['valid']
        elif 'hb_frame' in d:
            f = d['hb_frame']
            if f in headers: raise ValueError('duplicate HUD/BOB header')
            headers[f] = d
        elif 'hud_op_frame' in d:
            f,i = d['hud_op_frame'], d['index']
            if i in operations[f]: raise ValueError('duplicate HUD operation')
            operations[f][i] = d['count']
        elif 'bob_op_frame' in d:
            f,i = d['bob_op_frame'], d['category']
            if i in bobs[f]: raise ValueError('duplicate BOB category')
            if not 0 <= i < 7: raise ValueError('out-of-bounds BOB category')
            bobs[f][i] = work_area(i,d['pushes'],d['unaligned'])
    if set(headers)!=set(expected): raise ValueError('missing HUD/BOB headers')
    for f,row in rows.items():
        if headers[f]['faults'] or headers[f]['ops_valid']!=int(detailed):
            raise ValueError('invalid native instrumentation state')
        if set(valid[f])!=set(range(49)) or set(operations[f])!=set(range(16)) or set(bobs[f])!=set(range(7)):
            raise ValueError('incomplete or out-of-bounds vector')
        if any(n<0 for n in operations[f].values()): raise ValueError('negative operation count')
        required = {3,4,5}
        if detailed:
            required |= set(range(33,49))
            if operations[f][4]: required |= {7,8}
        if {i for i,v in valid[f].items() if v}!=required:
            raise ValueError('missing/unexpected executed timestamp')
        row['outer'] = partition(row['stamps'],[(-1,'start'),(3,'before_hud'),
                                  (4,'hud'),(5,'bobs'),(-2,'after_bobs')])
        if not detailed:
            row.update(hud=None,bobs=None,operations=None,bob_operations=None,score_format=None)
            continue
        row['hud'] = partition(row['stamps'],HUD)
        row['bobs'] = partition(row['stamps'],BOB)
        if sum(row['hud'].values())!=row['outer']['hud'] or sum(row['bobs'].values())!=row['outer']['bobs']:
            raise ValueError('parent/child identity failed')
        row['operations'] = {OPS[i]:operations[f][i] for i in range(16)}
        row['bob_operations'] = [bobs[f][i] for i in range(7)]
        if operations[f][4]:
            if operations[f][4]!=1: raise ValueError('repeated score formatting')
            score = partition(row['stamps'],[(36,'start'),(7,'setup'),(8,'format'),(37,'dirty_draw')])
            row['score_format'] = score
        else: row['score_format'] = None
    return rows
