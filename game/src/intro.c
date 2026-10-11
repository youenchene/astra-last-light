/* ACE portions: MPL-2.0, https://mozilla.org/MPL/2.0/ . Adapted from
 * SuperRugbyV ace_splash.c / Last Minute Creations GermzSurvivor splash.c.
 * Micrix portions: Youen CHENE (1996-2022), CC BY-NC-SA 4.0, adapted
 * from SuperRugbyV intro.c / Blower .Intro. See art/intro/README.md.
 * Changes: shared OCS framebuffer, palette-banked gradient, frame state
 * machine and shared sound API instead of private takeover/player;
 * startup Micrix cache and DMA clears/copy for original intro transitions. */
#include "intro.h"
#include "sound.h"
#include <string.h>
#include <ace/managers/blit.h>
#include <ace/managers/memory.h>
#include <ace/managers/ptplayer.h>
#include <ace/utils/custom.h>
#include <agk/debug.h>
#include "../art/intro/ace-logo.h"
#include "../art/intro/ace-sound.h"
#include "../art/intro/micrix.h"

enum { INTRO_DONE, INTRO_ACE, INTRO_MICRIX };
enum { ACE_TICKS = 150, MICRIX_TICKS = 100 };
enum { MICRIX_CACHE_BYTES = 320 / 8 * 64 * 4, MICRIX_ORIGIN_Y = 96 };
static tSimpleBufferManager *s_pBuffer;
static tVPort *s_pVPort;
static UWORD s_uwTick;
static UBYTE s_ubStage, s_ubArmed, s_ubSpark[2], s_loaded[2];
static WORD s_wOldGlint[2];
static tBitMap *s_firstBuffer;
static UBYTE s_pMicrixMask[35][22];
/* Descriptor lives in ordinary BSS; only the 10 KiB pixel data needs chip RAM. */
static tBitMap s_sMicrixCache;
static UBYTE *s_pAceSample;
static tPtplayerSfx s_sAceSound;
static const UWORD s_uwAceBands[5] = {0xc00,0xfb2,0xcc2,0x099,0x055};
typedef char tAceLogoSizeCheck[(sizeof(aceLogoPlanes) == 2360) ? 1 : -1];

static void clearBitmap(tBitMap *pBitmap) {
  blitWait();
  if ((pBitmap->Flags & BMF_INTERLEAVED) && pBitmap->Depth == 4 &&
      pBitmap->BytesPerRow == 160 && pBitmap->Rows == 256) {
    /* Constant zero needs D only, not ACE Rect's C read-modify-write.
     * OCS height field zero encodes 1024 planar rows (256 screen rows). */
    g_pCustom->bltcon0 = USED;
    g_pCustom->bltcon1 = 0;
    if(s_ubStage == INTRO_MICRIX) {
      /* Both logos, including the moving glint and spark, fit this region.
       * The rest was cleared at startup and is never touched by the intro.
       * Clear 64 screen rows (256 interleaved plane rows), not the whole view. */
      g_pCustom->bltdmod = 40 - 26;
      g_pCustom->bltdpt = pBitmap->Planes[0] + 96 * 160 + 8;
      g_pCustom->bltsize = (256 << 6) | 13;
    }
    else {
      g_pCustom->bltdmod = 0;
      g_pCustom->bltdpt = pBitmap->Planes[0];
      g_pCustom->bltsize = 20;
    }
  }
  else blitRect(pBitmap, 0, 0, 320, 256, 0);
  blitWait();
}

static void clearBuffers(void) {
  clearBitmap(s_pBuffer->pBack);
  if (s_ubStage == INTRO_ACE && s_pBuffer->pFront != s_pBuffer->pBack) {
    clearBitmap(s_pBuffer->pFront);
  }
  memset(s_pVPort->pPalette, 0, 16 * sizeof(UWORD));
}

static void dot(tBitMap *pBitmap, UWORD uwX, UWORD uwY, UBYTE ubColor) {
  UWORD uwOffset = uwY * pBitmap->BytesPerRow + (uwX >> 3);
  UBYTE ubBit = 0x80 >> (uwX & 7), ubPlane;
  for (ubPlane = 0; ubPlane < 4; ++ubPlane) {
    UBYTE *pByte = &pBitmap->Planes[ubPlane][uwOffset];
    if (ubColor & (1 << ubPlane)) *pByte |= ubBit;
    else *pByte &= (UBYTE)~ubBit;
  }
}

static UWORD blend(UWORD uwFrom, UWORD uwTo, UWORD uwRatio) {
  WORD wR = (uwFrom >> 8) & 15;
  WORD wG = (uwFrom >> 4) & 15;
  WORD wB = uwFrom & 15;
  wR += (((WORD)((uwTo >> 8) & 15) - wR) * (WORD)uwRatio) / 15;
  wG += (((WORD)((uwTo >> 4) & 15) - wG) * (WORD)uwRatio) / 15;
  wB += (((WORD)(uwTo & 15) - wB) * (WORD)uwRatio) / 15;
  return (wR << 8) | (wG << 4) | wB;
}

static UWORD flash(UWORD uwStart, UWORD uwColor) {
  UWORD uwAge;
  if (s_uwTick < uwStart) return 0;
  uwAge = s_uwTick - uwStart;
  if (s_uwTick >= ACE_TICKS - 15) {
    return blend(0, uwColor, ACE_TICKS - s_uwTick);
  }
  return blend(0xfff, uwColor, uwAge < 15 ? uwAge : 15);
}

static void acePalette(void) {
  UBYTE ubBand;
  for (ubBand = 0; ubBand < 5; ++ubBand) {
    s_pVPort->pPalette[1 + ubBand] = flash(0, s_uwAceBands[ubBand]);
    s_pVPort->pPalette[6 + ubBand] = flash(9, s_uwAceBands[ubBand]);
    if (ubBand) {
      s_pVPort->pPalette[10 + ubBand] = flash(29, s_uwAceBands[ubBand]);
    }
  }
  s_pVPort->pPalette[15] = flash(49, 0x343);
}

static void aceDraw(tBitMap *pBitmap) {
  UWORD uwY, uwByte, uwOffset = 0;
  UWORD uwDestination = 98 * pBitmap->BytesPerRow + 10;
  /* Bank colors by source index: independent A/C/E flashes without
   * raster copper blocks. POWERED has its own delayed grey-green bank. */
  for (uwY = 0; uwY < 59; ++uwY) {
    UBYTE ubBand = uwY < 18 ? 0 : 1 + (uwY - 18) / 10;
    if (ubBand > 4) ubBand = 4;
    for (uwByte = 0; uwByte < 20; ++uwByte) {
      UBYTE ubLow = aceLogoPlanes[uwOffset + uwByte];
      UBYTE ubHigh = aceLogoPlanes[1180 + uwOffset + uwByte];
      UBYTE ubA = ubLow & (UBYTE)~ubHigh;
      UBYTE ubC = ubHigh & (UBYTE)~ubLow;
      UBYTE ubE = ubHigh & ubLow;
      UBYTE ubEColor = uwY < 18 ? 15 : 10 + ubBand;
      UBYTE ubPlane;
      for (ubPlane = 0; ubPlane < 4; ++ubPlane) {
        UBYTE ubBit = 1 << ubPlane;
        pBitmap->Planes[ubPlane][uwDestination + uwByte] =
          ((1 + ubBand) & ubBit ? ubA : 0) |
          ((6 + ubBand) & ubBit ? ubC : 0) |
          (ubEColor & ubBit ? ubE : 0);
      }
    }
    uwOffset += 20;
    uwDestination += pBitmap->BytesPerRow;
  }
}

static void wordDraw(tBitMap *pBitmap, const UBYTE *pLetters,
  UBYTE ubCount, UWORD uwX, UWORD uwY, UBYTE ubScale, UBYTE ubColor) {
  UBYTE ubLetter, ubRow, ubCol, ubDy, ubDx;
  for (ubLetter = 0; ubLetter < ubCount; ++ubLetter) {
    for (ubRow = 0; ubRow < 7; ++ubRow) {
      for (ubCol = 0; ubCol < 5; ++ubCol) {
        if (!(s_ubGlyphs[pLetters[ubLetter]][ubRow] & (16 >> ubCol))) continue;
        for (ubDy = 0; ubDy < ubScale; ++ubDy) {
          for (ubDx = 0; ubDx < ubScale; ++ubDx) {
            dot(pBitmap, uwX + ubCol * ubScale + ubDx,
              uwY + ubRow * ubScale + ubDy, ubColor);
          }
        }
      }
    }
    uwX += 6 * ubScale;
  }
}

static void micrixDraw(tBitMap *pBitmap, UWORD uwOriginYOffset) {
  UWORD uwX;
  wordDraw(pBitmap, s_ubMicrix, 6, 72, 100 - uwOriginYOffset, 5, 1);
  wordDraw(pBitmap, s_ubProduction, 10, 131, 146 - uwOriginYOffset, 1, 3);
  for (uwX = 72; uwX < 116; ++uwX)
    dot(pBitmap, uwX, 146 - uwOriginYOffset, 3);
  for (uwX = 0; uwX < 35; ++uwX)
    memcpy(s_pMicrixMask[uwX], pBitmap->Planes[0] +
      (100 - uwOriginYOffset + uwX) * pBitmap->BytesPerRow + 9, 22);
}

static void micrixCopy(tBitMap *pBitmap) {
  if (!s_sMicrixCache.Planes[0]) {
    /* Allocation failure was reported at startup. Preserve original pixels
     * and timing ticks, at the cost of the old transition stall. */
    micrixDraw(pBitmap, 0);
    return;
  }
  blitCopyAligned(&s_sMicrixCache, 64, 0, pBitmap, 64, MICRIX_ORIGIN_Y, 208, 64);
  /* micrixTick writes glint/spark pixels with the CPU immediately afterward. */
  blitWait();
}

static void sweep(tBitMap *pBitmap, WORD wCenter, UBYTE ubColor) {
  if (wCenter < 0) return;
  WORD left = wCenter - 4 - 72, right = wCenter + 4 - 72;
  if(right < 0 || left >= 175) return;
  if(left < 0) left = 0;
  if(right >= 175) right = 174;
  for(UBYTE byte = left >> 3; byte <= (right >> 3); ++byte) {
    UBYTE clip = 255;
    if(byte == (left >> 3)) clip &= 255 >> (left & 7);
    if(byte == (right >> 3)) clip &= 255 << (7 - (right & 7));
    UWORD offset = 100 * pBitmap->BytesPerRow + 9 + byte;
    for(UBYTE row = 0; row < 35; ++row, offset += pBitmap->BytesPerRow) {
      UBYTE bits = s_pMicrixMask[row][byte] & clip;
      if(ubColor == 1) {
        pBitmap->Planes[0][offset] |= bits;
        pBitmap->Planes[1][offset] &= ~bits;
      }
      else {
        pBitmap->Planes[0][offset] &= ~bits;
        pBitmap->Planes[1][offset] |= bits;
      }
    }
  }
}

static void micrixAnimate(tBitMap *pBitmap, WORD wGlint, UBYTE ubSpark) {
  UBYTE buffer = pBitmap != s_firstBuffer;
  WORD wDelta;
  sweep(pBitmap, s_wOldGlint[buffer], 1);
  sweep(pBitmap, wGlint, 2);
  s_wOldGlint[buffer] = wGlint;
  if (ubSpark == s_ubSpark[buffer]) return;
  s_ubSpark[buffer] = ubSpark;
  for (wDelta = -2; wDelta <= 2; ++wDelta) {
    dot(pBitmap, 253 + wDelta, 98, ubSpark ? 2 : 0);
    dot(pBitmap, 253, 98 + wDelta, ubSpark ? 2 : 0);
  }
}

static void micrixTick(void) {
  UBYTE buffer = s_pBuffer->pBack != s_firstBuffer;
  if(!s_loaded[buffer]) {
    clearBitmap(s_pBuffer->pBack);
    micrixCopy(s_pBuffer->pBack);
    s_loaded[buffer] = 1;
  }
  UBYTE ubColor, ubSpark = s_uwTick >= 43 && s_uwTick < 55;
  /* Keep the outgoing logo legible until the complete title replaces it.
   * Fading to zero before bounded preparation would create a black gap.
   * Original fade-in, stage duration, glint, PCM and skip timing are retained. */
  UWORD uwFade = s_uwTick < 9 ? 7 + s_uwTick * 8 / 9 : 15;
  WORD wGlint = s_uwTick >= 10 && s_uwTick < 45 ?
    70 + (s_uwTick - 10) * 180 / 35 : -1;
  for (ubColor = 0; ubColor < 4; ++ubColor) {
    s_pVPort->pPalette[ubColor] = blend(0, s_uwMicrixColors[ubColor], uwFade);
  }
  micrixAnimate(s_pBuffer->pBack, wGlint, ubSpark);
  if (s_uwTick == 10) soundPlay(SOUND_SFX_INTRO_RISE);
  if (s_uwTick == 43) soundPlay(SOUND_SFX_INTRO_SPARK);
}

static void beginStage(UBYTE ubStage) {
  s_ubStage = ubStage;
  s_uwTick = 0;
  s_ubArmed = 0;
  s_ubSpark[0] = s_ubSpark[1] = 0;
  s_wOldGlint[0] = s_wOldGlint[1] = -1;
  s_loaded[0] = s_loaded[1] = 0;
  if (ubStage == INTRO_ACE) {
    clearBuffers();
    aceDraw(s_pBuffer->pBack);
    if (s_pBuffer->pFront != s_pBuffer->pBack) aceDraw(s_pBuffer->pFront);
    acePalette();
    if(s_pAceSample) {
      /* Exact SuperRugbyV sample, channel, volume, priority and PAL period. */
      ptplayerSfxPlay(&s_sAceSound, 0, 64, 100);
      agkPrint("AGK sfx ace_original\n");
    }
  }
  else {
    ptplayerSfxStopOnChannel(0);
    memset(s_pVPort->pPalette, 0, 16 * sizeof(UWORD));
    micrixTick();
  }
}

void introCreate(tSimpleBufferManager *pBuffer, tVPort *pVPort) {
  introDestroy();
  if (!pBuffer || !pVPort || !pBuffer->pBack || !pBuffer->pFront ||
      !pVPort->pPalette) return;
  s_pBuffer = pBuffer;
  s_firstBuffer = pBuffer->pBack;
  s_pVPort = pVPort;
  /* Called before systemUnuse(): no allocation or glyph rasterization on
   * the normal ACE -> Micrix transition. Match ACE's interleaved layout. */
  s_sMicrixCache.Planes[0] = memAllocChipClear(MICRIX_CACHE_BYTES);
  if (s_sMicrixCache.Planes[0]) {
    s_sMicrixCache.BytesPerRow = 40 * 4;
    s_sMicrixCache.Rows = 64;
    s_sMicrixCache.Depth = 4;
    s_sMicrixCache.Flags = BMF_INTERLEAVED;
    for (UBYTE ubPlane = 1; ubPlane < 4; ++ubPlane)
      s_sMicrixCache.Planes[ubPlane] = s_sMicrixCache.Planes[0] + ubPlane * 40;
    micrixDraw(&s_sMicrixCache, MICRIX_ORIGIN_Y);
  }
  else agkPrint("AGK Micrix cache allocation failure: CPU draw fallback (transition stall)\n");
  s_pAceSample = memAllocChip(sizeof aceSample);
  if(s_pAceSample) {
    memcpy(s_pAceSample, aceSample, sizeof aceSample);
    s_sAceSound.pData = (UWORD *)s_pAceSample;
    s_sAceSound.uwWordLength = sizeof aceSample / 2;
    s_sAceSound.uwPeriod = 3546895 / 6000;
  }
  else agkPrint("AGK ACE audio allocation failure\n");
  beginStage(INTRO_ACE);
}

UBYTE introProcess(UBYTE ubFire) {
  UBYTE ubSkip;
  if (s_ubStage == INTRO_DONE) return 0;
  ubSkip = ubFire && s_ubArmed;
  if (!ubFire) s_ubArmed = 1;
  ++s_uwTick;
  if (ubSkip || s_uwTick >= (s_ubStage == INTRO_ACE ? ACE_TICKS : MICRIX_TICKS)) {
    if (s_ubStage == INTRO_ACE) {
      beginStage(INTRO_MICRIX);
      return 1;
    }
    /* Retain the last complete Micrix frame and its copper palette while the
     * title is prepared offscreen. No clear or palette reset on this handoff. */
    ptplayerSfxStopOnChannel(3);
    /* Keep original PCM alive until the shared player is destroyed. Its
     * channel-stop command is asynchronous and DMA must never see freed RAM. */
    s_ubStage = INTRO_DONE;
    return 0;
  }
  if (s_ubStage == INTRO_ACE) acePalette();
  else micrixTick();
  return 1;
}

void introDestroy(void) {
  if (s_sMicrixCache.Planes[0]) {
    blitWait();
    memFree(s_sMicrixCache.Planes[0], MICRIX_CACHE_BYTES);
  }
  memset(&s_sMicrixCache, 0, sizeof s_sMicrixCache);
  /* Caller must destroy the shared player first if it has been started. */
  if(s_pAceSample) memFree(s_pAceSample, sizeof aceSample);
  s_pAceSample = 0;
  s_ubStage = INTRO_DONE;
  s_pBuffer = 0;
  s_pVPort = 0;
}
