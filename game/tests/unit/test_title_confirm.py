from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class TitleConfirmTests(unittest.TestCase):
    def test_confirmation_uses_publication_not_hidden_work(self):
        source = r'''
#include <assert.h>
#include "title_confirm.h"
int main(void) {
    tGameState state;
    tTitleConfirm confirm = {0};
    tInput fire = {1,0,1};
    logicInit(&state);
    state.presentationBusy = 1;
    assert(titleConfirmFilter(&confirm,&state,&fire));
    logicUpdate(&state,&fire);
    assert(state.level == 1 && state.phase == TITLE && confirm.active);
    for(int i=0;i<400;++i) {
        fire = (tInput){-1,0,1};
        assert(!titleConfirmFilter(&confirm,&state,&fire));
        logicUpdate(&state,&fire);
        assert(state.phase == TITLE && state.level == 1 && !confirm.visible);
    }
    for(int i=0;i<TITLE_CONFIRM_FRAMES;++i) {
        fire = (tInput){1,0,1};
        titleConfirmFilter(&confirm,&state,&fire);
        logicUpdate(&state,&fire);
        assert(state.phase == TITLE);
        titleConfirmPresented(&confirm);
    }
    fire = (tInput){-1,0,1};
    titleConfirmFilter(&confirm,&state,&fire);
    logicUpdate(&state,&fire);
    assert(!confirm.active && state.phase == SECTOR_INTRO && state.level == 1);
    assert(!titleConfirmFilter(&confirm,&state,&fire));
    logicInit(&state);
    state.titleInputBlocked = 1;
    assert(!titleConfirmFilter(&confirm,&state,&fire));
    state.titleInputBlocked = 0;
    state.fireWasDown = 1;
    assert(!titleConfirmFilter(&confirm,&state,&fire));
    state.phase = GAMEOVER;
    state.fireWasDown = 0;
    assert(!titleConfirmFilter(&confirm,&state,&fire));
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / "confirm.c").write_text(source)
            subprocess.run(["cc", "-std=c11", "-I", str(ROOT / "game/src"),
                            str(path / "confirm.c"), str(ROOT / "game/src/logic.c"),
                            "-o", str(path / "confirm")], check=True)
            subprocess.run([str(path / "confirm")], check=True)
