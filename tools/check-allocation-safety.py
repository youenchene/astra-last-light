#!/usr/bin/env python3
"""Extract and fault-test actual generated sound and patched ACE functions.

Run after `bash tools/agk build`:
    python3 tools/check-allocation-safety.py [workspace]

Workspace defaults to this script's repository root. Requires cc with ASan/UBSan
and the pinned local ACE checkout. Only a private TemporaryDirectory is written;
its sources, executables and reconstructed vendor files are cleaned automatically.
Host stubs exercise allocation/cleanup, not Amiga hardware or interrupt behavior.
On macOS, LeakSanitizer is disabled because Apple ASan does not support it;
the allocator ledger independently asserts every allocation is freed exactly once.
"""
import argparse
import os
import pathlib
import re
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('workspace', nargs='?', type=pathlib.Path,
                    default=pathlib.Path(__file__).resolve().parents[1])
root = parser.parse_args().workspace.resolve()
ace = root / 'game/vendor/ACE'
sanitizer_env = os.environ.copy()
if sys.platform == 'darwin':
    sanitizer_env['ASAN_OPTIONS'] = (
        sanitizer_env.get('ASAN_OPTIONS', '') + ':detect_leaks=0'
    ).lstrip(':')
# Undefined behavior must fail the check, rather than merely print diagnostics.
sanitizer_env['UBSAN_OPTIONS'] = (
    sanitizer_env.get('UBSAN_OPTIONS', '') + ':halt_on_error=1'
).lstrip(':')


def function(source, name):
    match = re.search(r'^(?:static )?\w+[ *]+\b' + name + r'\([^;]*?\)\s*\{', source, re.M)
    assert match, name
    start = match.start()
    pos = match.end()
    depth = 1
    while depth:
        depth += (source[pos] == '{') - (source[pos] == '}')
        pos += 1
    return source[start:pos] + '\n'


sound = (root / 'game/build/sound/sound-safe.c').read_text()
original = (root / 'game/build/sound/sound.c').read_text()
data = r'static const UBYTE \w+\[\d+\][^=]*=\s*\{[^}]+\};'
assert re.findall(data, sound) == re.findall(data, original)
assert len(re.findall(data, original)) == 21  # eleven SFX, five MOD headers + PCM
print('PASS: all 21 generated SFX/MOD data arrays byte-for-byte unchanged', flush=True)

common = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
typedef UBYTE *PLANEPTR;
static int calls, fail_at, live, playing, uses;
static void *ptrs[64];
static size_t sizes[64];
static void *allocate(size_t n) {
    if(++calls == fail_at) return 0;
    void *p = calloc(1, n); assert(p);
    for(int i=0; i<64; ++i) if(!ptrs[i]) {
        ptrs[i]=p; sizes[i]=n; ++live; return p;
    }
    abort();
}
static void release(void *p, size_t n) {
    assert(!playing && p);
    for(int i=0; i<64; ++i) if(ptrs[i]==p) {
        assert(sizes[i]==n); free(p); ptrs[i]=0; --live; return;
    }
    abort();
}
#define memAllocChip(n) allocate(n)
#define memAllocFast(n) allocate(n)
#define memAllocFastClear(n) allocate(n)
#define memAlloc(n,f) allocate(n)
#define memFree(p,n) release(p,n)
#define systemUse() (++uses)
#define systemUnuse() (--uses)
#define logBlockBegin(...) ((void)0)
#define logBlockEnd(...) ((void)0)
#define logWrite(...) ((void)0)
#define blitWait() ((void)0)
'''
audio = common + r'''
#define SOUND_SFX_COUNT 11
#define SOUND_MUSIC_COUNT 5
#define PTPLAYER_MOD_SAMPLE_COUNT 31
#define systemIsPal() 1
#define ptplayerCreate(pal) (playing=1)
#define ptplayerSetMusicChannelMask(mask) assert((mask)==7)
#define ptplayerDestroy() (playing=0)
typedef struct { UWORD *pData; UWORD uwWordLength, uwPeriod; } tPtplayerSfx;
typedef struct {
    struct { UWORD uwLength; } pSampleHeaders[31];
    UBYTE padding[1084-62];
    UBYTE *pPatterns; ULONG ulPatternsSize; UBYTE isOwningSamples;
    UWORD *pSampleStarts[31];
} tPtplayerMod;
static struct { const UBYTE *pData; UWORD uwBytes; } s_pSfxDefs[SOUND_SFX_COUNT];
static struct { const UBYTE *pMod; ULONG ulHeadBytes; const UBYTE *pSamples; ULONG ulSampleBytes; } s_pMusicDefs[5];
static tPtplayerSfx s_pSfx[SOUND_SFX_COUNT];
static tPtplayerMod s_pMods[5];
static UBYTE *s_pChip[SOUND_SFX_COUNT + SOUND_MUSIC_COUNT];
static ULONG s_pChipSize[SOUND_SFX_COUNT + SOUND_MUSIC_COUNT];
void soundDestroy(void);
'''
audio += ''.join(function(sound, n) for n in ['copyToChip', 'astraSoundCreate', 'soundDestroy'])
audio += r'''
static void empty(void) {
    assert(!live && !playing && !uses);
    for(int i=0;i<SOUND_SFX_COUNT+SOUND_MUSIC_COUNT;++i) assert(!s_pChip[i] && !s_pChipSize[i]);
    for(int i=0;i<SOUND_SFX_COUNT;++i) assert(!s_pSfx[i].pData && !s_pSfx[i].uwWordLength);
    for(int i=0;i<5;++i) {
        assert(!s_pMods[i].pPatterns);
        for(int j=0;j<31;++j) assert(!s_pMods[i].pSampleStarts[j]);
    }
}
int main(void) {
    UBYTE samples[62]; memset(samples, 0x5a, sizeof(samples));
    tPtplayerMod header={0};
    for(int i=0;i<31;++i) header.pSampleHeaders[i].uwLength=1;
    for(int i=0;i<SOUND_SFX_COUNT;++i) s_pSfxDefs[i]=(typeof(s_pSfxDefs[0])){samples,62};
    for(int i=0;i<5;++i) s_pMusicDefs[i]=(typeof(s_pMusicDefs[0])){(UBYTE*)&header,1084,samples,62};
    for(fail_at=1;fail_at<=SOUND_SFX_COUNT+SOUND_MUSIC_COUNT;++fail_at) {
        calls=0; assert(!astraSoundCreate()); assert(calls==fail_at); empty();
        /* Retry after partial cleanup must succeed. */
        int saved=fail_at; fail_at=0; calls=0;
        assert(astraSoundCreate() && calls==16 && live==16);
        for(int i=0;i<16;++i) assert(!memcmp(s_pChip[i],samples,62));
        for(int i=0;i<5;++i) for(int j=0;j<31;++j)
            assert(s_pMods[i].pSampleStarts[j]==(UWORD*)(s_pChip[SOUND_SFX_COUNT+i]+j*2));
        soundDestroy(); empty(); fail_at=saved;
    }
    puts("PASS sound: 16 allocation failure positions, 16 successful retries, stop-before-free, exact sizes, empty partial state");
}
'''
bitmap = (ace / 'src/ace/utils/bitmap.c').read_text()
bob = (ace / 'src/ace/managers/bob.c').read_text()
graphics = common + r'''
#define AMIGA
#define BMF_INTERLEAVED 1
#define BMF_CONTIGUOUS 2
#define BMF_EXTERNAL 4
#define BMF_FASTMEM 8
#define BMF_CLEAR 16
#define MEMF_ANY 0
typedef struct { UWORD BytesPerRow, Rows; UBYTE Flags, Depth; PLANEPTR Planes[8]; } tBitMap;
typedef struct { int unused; } tBob;
typedef struct { tBob **pBobs; tBitMap *pDst, *pBg; UBYTE ubUndrawCount; } tBobQueue;
static tBobQueue s_pQueues[2];
static UBYTE s_ubMaxBobCount, s_ubBpp=4;
static UWORD s_uwBgBufferLength=32;
#define bitmapAllocChipAligned(n) allocate(n)
#define bitmapFreeChipAligned(p,n) release(p,n)
#define bitmapIsInterleaved(p) ((p)->Flags & BMF_INTERLEAVED)
#define bitmapIsChip(p) 1
'''
graphics += ''.join(function(bitmap, n) for n in ['bitmapCreate', 'bitmapDestroy'])
graphics += ''.join(function(bob, n) for n in ['bobDeallocBuffers', 'bobReallocateBuffers', 'bobBuffersReady', 'bobManagerDestroy'])
graphics += r'''
int main(void) {
    for(fail_at=1;fail_at<=6;++fail_at) {
        calls=0; s_ubMaxBobCount=32;
        bobReallocateBuffers(); assert(!bobBuffersReady());
        bobManagerDestroy(); assert(!live && !uses && !bobBuffersReady());
        bobManagerDestroy(); assert(!live && !uses);
    }
    fail_at=0; calls=0; s_ubMaxBobCount=32;
    bobReallocateBuffers(); assert(bobBuffersReady() && calls==6 && live==6);
    for(int i=0;i<2;++i) {
        UBYTE *saved=s_pQueues[i].pBg->Planes[0];
        s_pQueues[i].pBg->Planes[0]=0; assert(!bobBuffersReady());
        s_pQueues[i].pBg->Planes[0]=saved;
    }
    bobManagerDestroy(); assert(!live && !uses);
    puts("PASS BOB/bitmap: both queues, both descriptors, both chip planes OOM; readiness, partial cleanup, balanced system ownership");
}
'''
with tempfile.TemporaryDirectory(prefix='astra-oom-') as temp:
    temp = pathlib.Path(temp)
    for name, source in [('audio', audio), ('graphics', graphics)]:
        c = temp / (name + '.c')
        c.write_text(source)
        exe = temp / name
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined', str(c), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True, env=sanitizer_env)
    # Reconstruct only the three owned files from the pin; no changes to checkout.
    paths = ['include/ace/managers/bob.h', 'src/ace/managers/bob.c', 'src/ace/utils/bitmap.c']
    for path in paths:
        dest = temp / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(subprocess.check_output(['git', '-C', str(ace), 'show', '10ca68a321989738e9ac40f895bdd9f1d8e040fe:' + path]))
    # Run the exact bootstrap patch materializer, not a second implementation.
    bootstrap = (root / 'tools/bootstrap.sh').read_text()
    materializer = bootstrap.split("<<'PY'\n", 1)[1].split('\nPY\n', 1)[0]
    patch = str(temp / 'allocation.patch')
    subprocess.run([sys.executable, '-c', materializer,
                    str(root / 'tools/patches/ace-allocation-safety.patch'), patch], check=True)
    subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', '--check', patch], cwd=temp, check=True)
    subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', patch], cwd=temp, check=True)
    subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', '--reverse', '--check', patch], cwd=temp, check=True)
    for path in paths:
        assert (temp / path).read_bytes() == (ace / path).read_bytes(), path
    print('PASS vendor patch: clean pin forward apply, reverse check, exact match to local three files')
