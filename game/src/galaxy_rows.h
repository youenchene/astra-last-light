#ifndef ASTRA_GALAXY_ROWS_H
#define ASTRA_GALAXY_ROWS_H
/* Sparse independent rows: no framebuffer backreferences, heap or CHIP staging.
 * Cursor is a relative row in the requested rectangle, owned by its bitmap.
 * Caller clears the rectangle once and waits for blits before starting.
 * baseCleared must explicitly confirm that clear, otherwise no work is done.
 * At most 320 written bytes / 64 row-or-span operations / eight rows per call;
 * skipped spans consume the operation budget too. */
unsigned short galaxyStep(unsigned char *const planes[4], unsigned short stride,
    unsigned char level, unsigned short x, unsigned short y,
    unsigned short width, unsigned short height, unsigned short row,
    unsigned char baseCleared);
#endif
