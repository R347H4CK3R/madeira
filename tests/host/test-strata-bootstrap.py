#!/usr/bin/env python3
"""Exercise bootstrap failures on any host; fake only macOS/tool boundaries."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class BootstrapTests(unittest.TestCase):
    def run_probe(self, mode, status=' ', update=0):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'tools').mkdir()
            shutil.copy(ROOT/'tools/bootstrap-strata-deps.sh', root/'tools/bootstrap-strata-deps.sh')
            bins = root/'bin'
            bins.mkdir()
            scripts = {'uname': 'echo Darwin', 'xcodebuild': 'exit 0', 'xcrun': 'exit 0', 'cmake': 'exit 0', 'ninja': 'exit 0', 'curl': 'exit 9',
                       'git': f'''case "$*" in
  "submodule update --init --recursive") exit {update};;
  "submodule status --recursive") printf '%s\\n' '{status}0123456789012345678901234567890123456789 FEX (pin)';;
  "-C toolchains/llvm-project rev-parse HEAD") echo 8dfdcc7b70000000000000000000000000000000;;
esac'''}
            for name in ['cargo', 'rustup', 'meson', 'pkg-config', 'llvm-objcopy']:
                scripts[name] = 'exit 0'
            for name, body in scripts.items():
                p = bins/name
                p.write_text('#!/bin/bash\n'+body+'\n')
                p.chmod(0o755)
            for mod in ['FEX','wine','dxmt','madeira-dock']:
                (root/mod).mkdir()
                (root/mod/'.git').touch()
            env = dict(os.environ, PATH=str(bins)+':'+os.environ['PATH'])
            return subprocess.run(['bash',str(root/'tools/bootstrap-strata-deps.sh'),mode],env=env,text=True,capture_output=True)

    def test_failed_checkout_stops_before_reporting_ready(self):
        r = self.run_probe('--install', update=1)
        self.assertEqual(r.returncode, 1)
        self.assertIn('BLOCKED: Submodule checkout failed', r.stdout)
        self.assertNotIn('OK: submodule', r.stdout)

    def test_wrong_recursive_pin_is_reported(self):
        r = self.run_probe('--check', status='+')
        self.assertIn('MISSING: pinned submodule revision', r.stdout)

    def test_fex_and_generated_wine_inputs_are_required(self):
        r = self.run_probe('--check')
        self.assertIn('FEX/build-ios/FEXCore/Source/libFEXCore.a', r.stdout)
        self.assertIn('wine/build-macos/include/config.h', r.stdout)
        self.assertIn('toolchains/llvm-host-build/bin/llvm-tblgen', r.stdout)

if __name__ == '__main__':
    unittest.main()
