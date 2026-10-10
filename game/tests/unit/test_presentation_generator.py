"""The freshness gate must work with only game/ mounted, and never repair data."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
INPUTS = ('tools/make-presentation.py', 'src/render_scenes.c', 'src/scene_font.h',
          'src/logic.c', 'art/font.txt', 'art/palette.txt', 'tools/selected_rd.py')


class PresentationGeneratorTests(unittest.TestCase):
    def invoke(self, script, cwd, check=True):
        return subprocess.run([sys.executable, str(script)] + (['--check'] if check else []),
                              cwd=cwd, capture_output=True, text=True)

    def copy_game(self, destination):
        for name in INPUTS:
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / 'game' / name, target)
        shutil.copytree(ROOT / 'game/art/selected-rd', destination / 'art/selected-rd')
        return destination / 'tools/make-presentation.py'

    def test_both_entry_points_from_unrelated_cwd(self):
        expected = (ROOT / 'game/art/presentation-rows.h').read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            for script in (ROOT / 'tools/make-presentation.py', ROOT / 'game/tools/make-presentation.py'):
                result = self.invoke(script, temp)
                self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((ROOT / 'game/art/presentation-rows.h').read_bytes(), expected)

    def test_game_only_layout_generates_identical_output(self):
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp) / 'isolated-game'
            script = self.copy_game(game)
            result = self.invoke(script, temp, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((game / 'art/presentation-rows.h').read_bytes(),
                             (ROOT / 'game/art/presentation-rows.h').read_bytes())
            self.assertEqual(self.invoke(script, temp).returncode, 0)

    def test_missing_check_fails_without_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp) / 'isolated-game'
            result = self.invoke(self.copy_game(game), temp)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('stale presentation rows', result.stderr)
            self.assertFalse((game / 'art/presentation-rows.h').exists())

    def test_stale_check_fails_without_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp) / 'isolated-game'
            script = self.copy_game(game)
            output = game / 'art/presentation-rows.h'
            output.write_bytes(b'preserve this stale evidence\n')
            before = output.stat().st_mtime_ns
            result = self.invoke(script, temp)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('stale presentation rows', result.stderr)
            self.assertEqual(output.read_bytes(), b'preserve this stale evidence\n')
            self.assertEqual(output.stat().st_mtime_ns, before)
