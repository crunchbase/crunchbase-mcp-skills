"""Release output isolation."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ReleaseBuildTests(unittest.TestCase):
    def test_nonempty_output_is_rejected_without_modifying_existing_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            old = output / 'retired-skill.zip'
            old.write_bytes(b'preserve existing artifact')
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/build_releases.py'),
                                     '--output', str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('must be empty', result.stderr)
            self.assertEqual(list(output.iterdir()), [old])
            self.assertEqual(old.read_bytes(), b'preserve existing artifact')
