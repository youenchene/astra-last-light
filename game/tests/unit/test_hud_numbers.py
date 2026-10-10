"""Exercise production formatting at the word/long boundary and score wrap."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_title_composition import ROOT, function


class HudNumbersTests(unittest.TestCase):
    def test_counters_scores_and_word_boundary(self):
        source = (ROOT / 'game/src/render_world.c').read_text()
        source = source.replace('__attribute__((noinline)) ', '')
        prelude = '''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef uint32_t ULONG;
'''
        exercise = '''
static void check(uint32_t value, unsigned digits) {
    char actual[12], expected[12];
    memset(actual, 0x55, sizeof(actual));
    numberText(actual, value, digits);
    snprintf(expected, sizeof(expected), "%0*u", digits,
        value % (digits == 1 ? 10 : 100000000));
    assert(!strcmp(actual, expected));
    assert(actual[digits + 1] == 0x55);
}
int main(void) {
    for(uint32_t n = 0; n <= 65536; ++n) check(n, 8);
    for(uint32_t n = 0; n < 256; ++n) check(n, 1);
    const uint32_t edges[] = {9999999,10000000,99999999,100000000,
        4294967294u,4294967295u};
    for(unsigned i=0;i<sizeof(edges)/sizeof(*edges);++i) check(edges[i],8);
    uint32_t n = 12345;
    for(unsigned i=0;i<100000;++i) {
        n = n * 1664525u + 1013904223u;
        check(n,8);
    }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'numbers.c').write_text(prelude + function(source, 'numberText') + exercise)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(path / 'numbers.c'), '-o', str(path / 'numbers')], check=True)
            subprocess.run([str(path / 'numbers')], check=True)
