#include "galaxy_rows.h"
#include "galaxy_trace.h"
extern const unsigned short galaxyOffsets[];
extern const unsigned char galaxyBytes[];

/* A span is entirely nonzero. Clear-before-paint permits omitted zero runs and
 * planes without borrowing any previous framebuffer contents. */
static void spanWrite(unsigned char *dest, const unsigned char *src,
    unsigned char count, unsigned char repeat, unsigned char firstMask,
    unsigned char lastMask) {
    unsigned char value = *src;
    if(count == 1) { *dest |= value & firstMask & lastMask; return; }
    if(firstMask != 255) {
        *dest++ |= value & firstMask;
        if(!repeat) ++src;
        --count;
    }
    unsigned char tail = lastMask != 255;
    count -= tail;
    if(repeat) { while(count--) *dest++ = value; }
    else { while(count--) *dest++ = *src++; }
    if(tail) *dest |= (repeat ? value : *src) & lastMask;
}

static void rowPaint(unsigned char *const planes[4], unsigned short position,
    const unsigned char *src, unsigned char spans, unsigned short x, unsigned short end) {
    unsigned char first = x >> 3, last = (end + 7) >> 3;
    unsigned char leftMask = 255 >> (x & 7);
    unsigned char rightMask = (end & 7) ? 255 << (8 - (end & 7)) : 255;
    while(spans--) {
        unsigned char location = *src++, token = *src++;
        unsigned char byte = location & 63, count = token & 127;
        const unsigned char *payload = src;
        src += (token & 128) ? 1 : count;
        if(byte >= last || byte + count <= first) continue;
        if(byte < first) {
            unsigned char skip = first - byte;
            count -= skip; byte = first;
            if(!(token & 128)) payload += skip;
        }
        if(count > last - byte) count = last - byte;
        spanWrite(planes[location >> 6] + position + byte, payload, count, token & 128,
            byte == first ? leftMask : 255, byte + count == last ? rightMask : 255);
    }
}

unsigned short galaxyStep(unsigned char *const planes[4], unsigned short stride,
    unsigned char level, unsigned short x, unsigned short y,
    unsigned short width, unsigned short height, unsigned short row,
    unsigned char baseCleared) {
    if(!baseCleared) return row;
    if(!width || !height) return height;
    galaxyTraceDecodeBegin(x != 0);
    unsigned short bytes = 320;
    unsigned char ops = 64, rows = 0;
    while(row < height && rows < 8 && ops) {
        --ops; /* Charge the row lookup even if admission below refuses it. */
        unsigned short sy = y + row;
        if(sy >= 56 && sy < 216) {
            unsigned short id = (unsigned short)level * 160 + sy - 56;
            const unsigned char *src = galaxyBytes + galaxyOffsets[id];
            unsigned char cost = src[0]; /* Every span, including off-patch skips. */
            if(cost > ops || src[1] > bytes) break;
            ops -= cost; bytes -= src[1];
            rowPaint(planes, sy * stride, src + 2, src[0], x, x + width);
        }
        ++rows; ++row;
    }
    galaxyTraceDecodeEnd();
    return row;
}
