"""Portable selector rules and independent reference-pixel reconstruction.

No emulator or reference checkout required. Compile the production module with
strict warnings; validate full planar images, not golden replacements.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class LanguageSelectTests(unittest.TestCase):
    def test_english_is_the_cold_start_default(self):
        self.compile_run(r'''
#include <assert.h>
#include "language_select.h"
int main(void) {
    tLanguageSelect choice;
    languageSelectBegin(&choice);
    assert(languageGet() == LANGUAGE_EN);
    assert(choice.selected == LANGUAGE_EN);
}
''')

    def test_startup_fixtures_confirm_language_only_before_first_title(self):
        for path in (ROOT / "game/tests").rglob("*.agk"):
            text = path.read_text()
            first_title = text.find('wait-serial "AGK title_ready"')
            if first_title < 0:
                continue
            with self.subTest(scenario=path.name):
                self.assertEqual(text.count('wait-serial "AGK language_ready"'), 1)
                self.assertLess(text.index('wait-serial "AGK language_ready"'), first_title)

    def test_status_tracks_actual_input_gates(self):
        self.compile_run(r'''
#include <assert.h>
#include "ui_status.h"
int main(void) {
    tGameState s;
    tLanguageSelect c;
    tInput neutral = {0};
    logicInit(&s);
    languageSelectBegin(&c);
    assert(uiStatus(&s,&c,0,0,0)==UI_IDLE);
    assert(uiStatus(&s,&c,1,0,0)==UI_LOADING);
    c.row[0]=c.row[1]=256;
    c.borderRow[0]=c.borderRow[1]=72;
    c.drawn[0]=c.drawn[1]=c.selected;
    languageSelectPresented(&c,0);
    assert(uiStatus(&s,&c,1,0,0)==UI_LOADING);
    languageSelectPresented(&c,1);
    assert(uiStatus(&s,&c,1,0,0)==UI_RELEASE);
    languageSelectInput(&c,0,0);
    assert(uiStatus(&s,&c,1,0,0)==UI_IDLE);
    languageSelectInput(&c,0,1);
    assert(uiStatus(&s,&c,1,0,0)==UI_RELEASE);
    const tPhase phases[]={TITLE, SECTOR_INTRO, PLAY, BOSS_INTRO, BOSS, CLEAR, WIN, GAMEOVER};
    for(unsigned i=0;i<sizeof phases/sizeof *phases;++i) {
        s.phase=phases[i];
        logicSetPresentationBusy(&s,1);
        assert(uiStatus(&s,&c,0,1,0)==UI_LOADING);
    }
    logicSetPresentationBusy(&s,0);
    s.phase=TITLE; s.titleInputBlocked=1;
    assert(uiStatus(&s,&c,0,1,0)==UI_RELEASE);
    logicUpdate(&s,&neutral);
    assert(uiStatus(&s,&c,0,1,0)==UI_IDLE);
    assert(uiStatus(&s,&c,0,1,1)==UI_LOADING);
    s.phase=WIN; s.sceneReady=1; s.phaseFrame=0;
    assert(uiStatus(&s,&c,0,1,0)==UI_WAIT);
    for(unsigned i=0;i<SCENE_SKIP_FRAMES;++i) logicUpdate(&s,&neutral);
    assert(uiStatus(&s,&c,0,1,0)==UI_CONTINUE);
    s.sceneArmed=0;
    assert(uiStatus(&s,&c,0,1,0)==UI_RELEASE);
    s.manualPause=1;
    assert(uiStatus(&s,&c,0,1,0)==UI_IDLE);
}
''')

    def compile_run(self, source):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / "test.c").write_text(source)
            subprocess.run([
                "cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                "-I", str(ROOT / "game/src"), str(path / "test.c"),
                str(ROOT / "game/src/language_select.c"),
                str(ROOT / "game/src/logic.c"), "-o", str(path / "test"),
            ], check=True)
            return subprocess.run([str(path / "test")], check=True, capture_output=True).stdout

    def test_publication_release_edges_and_persistence(self):
        self.compile_run(r'''
#include <assert.h>
#include <string.h>
#include "language_select.h"
#include "logic.h"
static uint8_t pixels[2][40960];
static void step(tLanguageSelect *c, uint8_t target) {
    uint8_t *p[4];
    for(int i=0;i<4;++i) p[i]=pixels[target]+40*i;
    languageSelectStep(c,target,p,160);
}
static void finish(tLanguageSelect *c) {
    for(int t=0;t<2;++t) {
        while(!languageSelectTargetReady(c,t)) step(c,t);
        languageSelectPresented(c,t);
    }
    assert(languageSelectReady(c));
}
int main(void) {
    tLanguageSelect c;
    tGameState game;
    assert(languageGet()==LANGUAGE_EN);
    languageSelectBegin(&c);
    memset(pixels,255,sizeof pixels);
    for(int n=0;n<59;++n) {
        unsigned before=c.row[0];
        step(&c,0);
        assert(c.row[0]>before && c.row[0]<=before+8 && c.row[1]==0);
        if(before>=74 && before<146) assert(c.row[0]==before+2);
        assert(pixels[1][0]==255 && pixels[0][40959]==255);
        assert(!languageSelectInput(&c,2,1));
        languageSelectPresented(&c,0);
        assert(!c.published && !languageSelectReady(&c));
    }
    step(&c,0);
    assert(languageSelectTargetReady(&c,0));
    languageSelectPresented(&c,0);
    for(int n=0;n<60;++n) step(&c,1);
    assert(!languageSelectReady(&c)); /* hidden completion is not publication */
    languageSelectPresented(&c,1);
    assert(languageSelectReady(&c));
    assert(!languageSelectInput(&c,2,1) && !c.confirmed); /* held skip/fire */
    languageSelectInput(&c,2,0);
    assert(c.selected==LANGUAGE_EN); /* held entry direction consumed */
    languageSelectInput(&c,0,0);
    languageSelectInput(&c,1,1); /* fresh left and fire: render before confirm */
    assert(c.selected==LANGUAGE_FR && !c.confirmed && !c.armed);
    for(int n=0;n<9;++n) {
        step(&c,0);
        assert(c.borderRow[0]==(n+1)*8);
        assert(!languageSelectInput(&c,2,1));
    }
    assert(!languageSelectReady(&c));
    finish(&c);
    assert(!languageSelectInput(&c,2,1) && !c.confirmed);
    languageSelectInput(&c,0,0);
    languageSelectInput(&c,3,0); /* left wins simultaneous directions */
    assert(c.selected==LANGUAGE_FR);
    finish(&c);
    languageSelectInput(&c,0,0);
    languageSelectInput(&c,2,0);
    finish(&c);
    languageSelectInput(&c,0,0);
    assert(!languageSelectInput(&c,0,1) && c.confirmed);
    assert(languageGet()==LANGUAGE_EN);
    for(int i=0;i<400;++i) assert(!languageSelectInput(&c,1,1));
    assert(languageSelectInput(&c,1,0));
    logicInit(&game);
    assert(languageGet()==LANGUAGE_EN);
    languageSelectBegin(&c);
    assert(c.selected==LANGUAGE_EN && !c.confirmed);
    /* Main's post-selector guard consumes held fire/direction through TITLE. */
    game.titleInputBlocked=1;
    game.presentationBusy=1;
    tInput held={1,0,1}, neutral={0};
    for(int i=0;i<400;++i) logicUpdate(&game,&held);
    assert(game.phase==TITLE && game.level==0);
    game.presentationBusy=0;
    logicUpdate(&game,&held);
    assert(game.phase==TITLE && game.titleInputBlocked);
    logicUpdate(&game,&neutral);
    assert(!game.titleInputBlocked);
    logicUpdate(&game,&held);
    assert(game.phase==SECTOR_INTRO && languageGet()==LANGUAGE_EN);
}
''')

    def test_both_targets_match_reference_and_repair_only_border(self):
        data = self.compile_run(r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "language_select.h"
static uint8_t storage[2][40962];
static void finish(tLanguageSelect *c) {
    for(int t=0;t<2;++t) {
        uint8_t *p[4];
        for(int i=0;i<4;++i) p[i]=storage[t]+1+40*i;
        while(!languageSelectTargetReady(c,t)) languageSelectStep(c,t,p,160);
        languageSelectPresented(c,t);
        assert(storage[t][0]==0xa5 && storage[t][40961]==0xa5);
    }
    assert(!memcmp(storage[0],storage[1],40962));
    assert(fwrite(storage[0]+1,1,40960,stdout)==40960);
}
int main(void) {
    tLanguageSelect c;
    memset(storage,0xa5,sizeof storage);
    languageSelectBegin(&c);
    finish(&c);
    languageSelectInput(&c,0,0);
    languageSelectInput(&c,1,0);
    finish(&c);
    languageSelectInput(&c,0,0);
    languageSelectInput(&c,2,0);
    finish(&c);
    assert(g_languagePalette[0]==0x011 && g_languagePalette[1]==0x149);
    assert(g_languagePalette[2]==0xfed && g_languagePalette[3]==0xc23);
}
''')
        self.assertEqual(len(data), 40960 * 3)
        for capture, selected in enumerate((1, 0, 1)):
            planar = data[capture * 40960:(capture + 1) * 40960]
            actual = [[sum(((planar[y * 160 + p * 40 + x // 8] >>
                             (7 - x % 8)) & 1) << p for p in range(4))
                       for x in range(320)] for y in range(256)]
            self.assertEqual(actual, self.reference(selected))

    @staticmethod
    def reference(selected):
        image = [[0] * 320 for _ in range(256)]

        def rect(x, y, w, h, ink):
            for yy in range(y, y + h):
                image[yy][x:x + w] = [ink] * w

        glyphs = {
            'F': [31,16,16,30,16,16,16], 'R': [30,17,17,30,20,18,17],
            'A': [14,17,17,31,17,17,17], 'N': [17,25,21,19,17,17,17],
            'Ç': [14,17,16,16,17,14,4], 'I': [14,4,4,4,4,4,14],
            'S': [15,16,16,14,1,1,30], 'E': [31,16,16,30,16,16,31],
            'G': [14,17,16,23,17,17,15], 'L': [16,16,16,16,16,16,31],
            'H': [17,17,17,31,17,17,17],
        }
        for item, label in enumerate(('FRANÇAIS', 'ENGLISH')):
            x, y = 42 + item * 158, 82
            rect(x, y, 64, 40, 1)
            if not item:
                rect(x + 21, y, 22, 40, 2)
                rect(x + 43, y, 21, 40, 3)
            else:
                for row in range(40):
                    for col in range(64):
                        d = col * 40 - row * 64
                        e = (63 - col) * 40 - row * 64
                        if -160 < d < 160 or -160 < e < 160:
                            image[y + row][x + col] = 2
                        if -50 < d < 50 or -50 < e < 50:
                            image[y + row][x + col] = 3
                rect(x + 26, y, 12, 40, 2)
                rect(x, y + 14, 64, 12, 2)
                rect(x + 29, y, 6, 40, 3)
                rect(x, y + 17, 64, 6, 3)
            for letter, ch in enumerate(label):
                for row, bits in enumerate(glyphs[ch]):
                    for col in range(5):
                        if bits & (16 >> col):
                            image[y + 48 + row][x + (11 if item else 8) + letter * 6 + col] = 2
            ink = 2 if item == selected else 0
            rect(x - 8, y - 8, 80, 2, ink)
            rect(x - 8, y + 62, 80, 2, ink)
            rect(x - 8, y - 8, 2, 72, ink)
            rect(x + 70, y - 8, 2, 72, ink)
        return image


if __name__ == '__main__':
    unittest.main()
