import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('campaign_report', ROOT / 'tools/check-campaign-native.py')
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class CampaignReporterTests(unittest.TestCase):
    def test_missing_empty_and_malformed_evidence_is_unavailable(self):
        for content in (None, '', 'AGK perf frames=50 dropped=0\n',
                        'AGK perf frames=50 maxload=42\n'):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                if content is not None:
                    (folder / 'serial.txt').write_text(content)
                result = CHECK.inspect(folder)
                self.assertFalse(result['functional_pass'])
                self.assertIsNone(result['performance'])
                self.assertTrue(result['error'])

    def test_reinspection_preserves_command_failure_and_restores_off(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'evidence'
            cache = root / 'game/build'
            cache.mkdir(parents=True)
            (cache / 'CMakeCache.txt').write_text('ASTRA_CAMPAIGN_PROBE:BOOL=OFF\n')
            calls = []
            def command(args, **kwargs):
                calls.append(args)
                if 'run' in args:
                    folder = output / 'a500'
                    folder.mkdir(parents=True)
                    (folder / 'serial.txt').write_text('')
                    raise subprocess.CalledProcessError(1, args)
            with patch.object(CHECK, 'ROOT', root), patch.object(CHECK.subprocess, 'run', command), \
                 patch.object(CHECK, 'preserve_probe', return_value={}, create=True), \
                 patch.object(sys, 'argv', ['check', '--out', str(output)]):
                self.assertEqual(CHECK.main(), 1)
            report = json.loads((output / 'report.json').read_text())
            self.assertIn('returned non-zero exit status', report['error'])
            self.assertIn('missing performance windows', report['profiles']['a500']['error'])
            self.assertIsNone(report['profiles']['a500']['performance'])
            self.assertTrue(report['production_restored'])
            self.assertIn('ASTRA_CAMPAIGN_PROBE=OFF', calls[-1])
