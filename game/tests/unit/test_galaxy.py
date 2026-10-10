"""Exercise the real portable decoder against independently quantized PNGs."""
import ctypes
import subprocess
import sys
import tempfile
import unittest
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from galaxy_oracle import background, stars, indices


class GalaxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        library = Path(cls.temp.name)/"galaxy.so"
        subprocess.run(["cc", "-shared", "-fPIC", "-O2", str(ROOT/"game/src/galaxy_rows.c"), str(ROOT/"game/src/galaxy_data.c"), "-o", str(library)], check=True)
        cls.lib = ctypes.CDLL(str(library))
        cls.lib.galaxyStep.restype = ctypes.c_ushort
        cls.lib.galaxyStep.argtypes = [ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)), ctypes.c_ushort, ctypes.c_ubyte] + [ctypes.c_ushort]*5 + [ctypes.c_ubyte]
        offsets = (ctypes.c_ushort*640).in_dll(cls.lib,"galaxyOffsets")
        data = ctypes.cast(ctypes.addressof(ctypes.c_ubyte.in_dll(cls.lib,"galaxyBytes")),ctypes.POINTER(ctypes.c_ubyte))
        cls.operations=[]
        for row in range(640):
            pos=offsets[row]; spans=data[pos]; written=data[pos+1]; pos+=2
            decoded=0; touched=set()
            for _ in range(spans):
                location=data[pos]; token=data[pos+1]; count=token&127; pos+=2
                plane,byte=location>>6,location&63
                assert plane<2 and count and byte+count<=40
                for column in range(byte,byte+count):
                    assert (plane,column) not in touched
                    touched.add((plane,column))
                values=[data[pos+i] for i in range(1 if token&128 else count)]
                assert all(values), "zero bytes must not be painted"
                pos+=len(values); decoded+=count
            assert decoded==written
            cls.operations.append(spans+1)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def target(self, value):
        planes = [(ctypes.c_ubyte*(40*256))(*([value]*(40*256))) for _ in range(4)]
        ptrs = (ctypes.POINTER(ctypes.c_ubyte)*4)(*planes)
        return planes, ptrs

    def check_rect(self, level, rect):
        x, y, w, h = rect
        # Two physical histories progress at different rates, never borrowing pixels.
        targets = [self.target(0xa5), self.target(0x5a)]
        expected = background(level)
        for planes, ptrs in targets:
            for yy in range(y,y+h):
                for xx in range(x,x+w):
                    mask = 128 >> (xx & 7)
                    for plane in planes:
                        plane[yy*40+xx//8] &= ~mask
        cursors = [0,0]
        calls = 0
        while min(cursors) < h:
            for i in (0,0,1):
                if cursors[i] == h:
                    continue
                after = self.lib.galaxyStep(targets[i][1],40,level,x,y,w,h,cursors[i],1)
                self.assertGreater(after, cursors[i])
                self.assertLessEqual(after-cursors[i],8)
                emitted = sum(1 for yy in range(y+cursors[i],y+after) if 56<=yy<216
                              for p in range(4) for column in range(40)
                              if any(ink & (1<<p) for ink in expected[yy-56][column*8:column*8+8]))
                self.assertLessEqual(emitted,320)
                ops=sum(self.operations[level*160+yy-56] if 56<=yy<216 else 1
                        for yy in range(y+cursors[i],y+after))
                self.assertLessEqual(ops,64)
                cursors[i] = after
            calls += 1
            self.assertLess(calls, h+1)
        for i, (planes, _) in enumerate(targets):
            initial = (0xa5,0x5a)[i]
            for yy in range(256):
                for xx in range(320):
                    value = sum(bool(planes[p][yy*40+xx//8] & (128>>(xx&7))) << p for p in range(4))
                    wanted = expected[yy-56][xx] if x <= xx < x+w and y <= yy < y+h and 56 <= yy <216 else (0 if x <= xx < x+w and y <= yy <y+h else (15 if initial & (128>>(xx&7)) else 0))
                    self.assertEqual(value,wanted,(level,rect,i,xx,yy))

    def test_all_sectors_full_and_unaligned_patches(self):
        for level in range(4):
            for rect in ((0,56,320,160),(153,57,158,9),(319,215,1,1),(0,54,9,5)):
                with self.subTest(level=level,rect=rect):
                    self.check_rect(level,rect)

    def test_uncleared_base_refused_without_writes(self):
        planes,ptrs=self.target(0xa5)
        for level in range(4):
            self.assertEqual(self.lib.galaxyStep(ptrs,40,level,153,57,158,9,0,0),0)
            self.assertTrue(all(value==0xa5 for plane in planes for value in plane))

    def test_exact_retained_seed_and_xor_restore(self):
        seed = 0xace1
        old = []
        for i in range(48):
            seed = (seed//2) ^ (0xb400 if seed & 1 else 0)
            if i%4:
                old.append((seed%316,56+i*159//47,1 if i%4==1 else 2))
        self.assertEqual(stars(0),old)
        self.assertEqual(len(old),36)
        for level in range(4):
            rows = [r[:] for r in background(level)]
            for tick in (0,1,8,255,256,1024):
                for x,y,w in stars(tick):
                    for dx in range(w):
                        rows[y-56][x+dx] ^= 4
                for x,y,w in stars(tick):
                    for dx in range(w):
                        rows[y-56][x+dx] ^= 4
                self.assertEqual(rows,background(level))

    def test_actual_world_two_buffer_star_catchup_and_wrap(self):
        source = (ROOT/"game/src/render_world.c").read_text()
        def extract(name):
            match = re.search(r"^.*\b"+name+r"\([^;{}]*\)\s*\{",source,re.M)
            start = match.start(); end = source.index("{",start)+1; depth=1
            while depth:
                depth += (source[end]=="{")-(source[end]=="}"); end+=1
            return source[start:end]
        constants=source[source.index("#define STAR_LAYER_SHIFT"):source.index("#define DECOR_HEIGHT")]
        functions="\n".join(extract(name) for name in ("starsReset","starToggle","starsProcess","starCatchUp","starsCatchUpLayer","renderWorldAnimate"))
        prelude=r'''
#include <stdint.h>
#include <string.h>
typedef uint8_t UBYTE; typedef uint16_t UWORD;
typedef struct { UBYTE *Planes[4]; } tBitMap;
typedef struct { UBYTE phase, paused; } tGameState;
#define PLAY_TOP 56
#define PLAY_BOTTOM 216
'''
        state=r'''
static UBYTE pixels[2][40960], s_buffer, s_ubDecorTick, s_topScroll, s_bottomScroll, s_starsDirty[2];
static UWORD s_pStarX[STAR_COUNT],s_pStarRow[STAR_COUNT];
static struct {UWORD stars[STAR_COUNT]; UBYTE starTick;} history[2];
#define HISTORY history[s_buffer]
static tBitMap screen, *s_pScreen=&screen;
static UBYTE renderWorldReady(void) {return 1;}
static UBYTE combatBackground(UBYTE phase) {return phase==1;}
static UBYTE logicWorldScrolling(const tGameState *s) {return !s->paused;}
static void blitWait(void) {}
static void bind(UBYTE b) {s_buffer=b;for(UBYTE p=0;p<4;++p)screen.Planes[p]=pixels[b]+p*40;}
'''
        wrappers=r'''
void initialize(const UBYTE *base) {
    starsReset();memset(history,0,sizeof(history));
    for(UBYTE b=0;b<2;++b) {
        memcpy(pixels[b],base,40960);bind(b);
        for(UBYTE i=0;i<STAR_COUNT;++i) {starToggle(i,s_pStarX[i]);HISTORY.stars[i]=s_pStarX[i];}
    }
}
UBYTE *advance(UBYTE b,UBYTE paused) {
    bind(b);tGameState state={1,paused};renderWorldAnimate(&state);return pixels[b];
}
'''
        with tempfile.TemporaryDirectory() as folder:
            c=Path(folder)/"stars.c"; lib=Path(folder)/"stars.so"
            c.write_text(prelude+constants+state+functions+wrappers)
            subprocess.run(["cc","-shared","-fPIC","-O2",str(c),"-o",str(lib)],check=True)
            code=ctypes.CDLL(str(lib));code.advance.restype=ctypes.POINTER(ctypes.c_ubyte)
            base=(ctypes.c_ubyte*40960)()
            for y,row in enumerate(background(1),56):
                for x,ink in enumerate(row):
                    for p in range(4):
                        if ink & (1<<p): base[y*160+p*40+x//8] |= 128>>(x&7)
            code.initialize(base)
            tick=0
            for frame in range(300):
                paused=20<=frame<27
                result=code.advance(frame%2,paused)
                tick+=not paused
                if frame not in (0,1,2,19,20,21,22,26,27,28,260,261,262,263,264,299): continue
                wanted=indices(1,tick)
                for y,row in enumerate(wanted,56):
                    for x,ink in enumerate(row):
                        actual=sum(bool(result[y*160+p*40+x//8] & (128>>(x&7)))<<p for p in range(4))
                        self.assertEqual(actual,ink,(frame,tick,x,y))
