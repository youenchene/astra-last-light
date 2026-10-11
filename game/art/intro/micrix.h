/* Micrix Production by Youen CHENE (1996-2022), CC BY-NC-SA 4.0.
 * Adapted via SuperRugbyV from Blower .Intro. See README.md. */
#ifndef ASTRA_MICRIX_DATA_H
#define ASTRA_MICRIX_DATA_H
#include <ace/types.h>
static const UBYTE s_ubGlyphs[][7] = {
  {17,27,21,21,17,17,17}, /* M */
  {31,4,4,4,4,4,31},     /* I */
  {15,16,16,16,16,16,15},/* C */
  {30,17,17,30,20,18,17},/* R */
  {17,17,10,4,10,17,17}, /* X */
  {30,17,17,30,16,16,16},/* P */
  {14,17,17,17,17,17,14},/* O */
  {30,17,17,17,17,17,30},/* D */
  {17,17,17,17,17,17,14},/* U */
  {31,4,4,4,4,4,4},     /* T */
  {17,25,25,21,19,19,17} /* N */
};
static const UBYTE s_ubMicrix[] = {0,1,2,3,1,4};
static const UBYTE s_ubProduction[] = {5,3,6,7,8,2,9,1,6,10};
static const UWORD s_uwMicrixColors[] = {0x000,0x73b,0xfff,0xdbf};
#endif
