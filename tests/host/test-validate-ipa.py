#!/usr/bin/env python3
"""Synthetic archive fixtures exercise validation; never distributed as application builds."""
import importlib.util
from pathlib import Path
import plistlib
import struct
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('validate_ipa', ROOT / 'tools/validate-ipa.py')
validator = importlib.util.module_from_spec(spec)
if spec.loader:
    spec.loader.exec_module(validator)


def macho(cpu=0x100000c, platform=2, filetype=2):
    command = struct.pack('<6I', 0x32, 24, platform, 0x110000, 0x120000, 0)
    return struct.pack('<8I', 0xfeedfacf, cpu, 0, filetype, 1, len(command), 0, 0) + command


class Validation(unittest.TestCase):
    def archive(self, replace=None, remove=None):
        files = {'Info.plist': plistlib.dumps({'CFBundleExecutable': 'Madeira', 'CFBundleIdentifier': 'test.Madeira', 'CFBundlePackageType': 'APPL'}),
                 'Madeira': macho(), 'prefix-template.tar.gz': b'fixture',
                 **{f'arm64ec-windows/{n}': b'MZfixture' for n in ('ntdll.dll', 'ucrtbase.dll', 'xtajit64.dll', 'd3d11.dll', 'dxgi.dll', 'd3d12.dll')}}
        files.update(replace or {})
        for name in remove or ():
            files.pop(name)
        p = Path(self.temp.name) / 'fixture.zip'
        with zipfile.ZipFile(p, 'w') as z:
            for name, value in files.items():
                z.writestr('Payload/Madeira.app/' + name, value)
        return p

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_arm64_ios_structure(self):
        self.assertEqual(validator.validate(self.archive())['architecture'], 'arm64')

    def test_rejects_x86(self):
        with self.assertRaisesRegex(ValueError, 'arm64'):
            validator.validate(self.archive({'Madeira': macho(cpu=0x1000007)}))

    def test_rejects_simulator(self):
        with self.assertRaisesRegex(ValueError, 'iOS device'):
            validator.validate(self.archive({'Madeira': macho(platform=7)}))

    def test_rejects_nonexecutable(self):
        with self.assertRaisesRegex(ValueError, 'executable'):
            validator.validate(self.archive({'Madeira': macho(filetype=6)}))

    def test_rejects_truncated_load_commands(self):
        with self.assertRaisesRegex(ValueError, 'truncated'):
            validator.validate(self.archive({'Madeira': macho()[:-4]}))

    def test_rejects_missing_translator(self):
        with self.assertRaisesRegex(ValueError, 'xtajit64'):
            validator.validate(self.archive(remove=['arm64ec-windows/xtajit64.dll']))

    def test_rejects_bad_pe(self):
        with self.assertRaisesRegex(ValueError, 'PE'):
            validator.validate(self.archive({'arm64ec-windows/ucrtbase.dll': b'notPE'}))

    def test_rejects_unsafe_archive_path(self):
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            validator.validate(self.archive({'../../escape': b'bad'}))

    def test_rejects_plist_executable_path(self):
        with self.assertRaisesRegex(ValueError, 'CFBundleExecutable'):
            validator.validate(self.archive({'Info.plist': plistlib.dumps({'CFBundleExecutable': '../Madeira', 'CFBundlePackageType': 'APPL'})}))

    def test_rejects_duplicate_zip_entry(self):
        p = self.archive()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(p, 'a') as z:
                z.writestr('Payload/Madeira.app/Madeira', macho())
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validator.validate(p)


if __name__ == '__main__':
    unittest.main()
