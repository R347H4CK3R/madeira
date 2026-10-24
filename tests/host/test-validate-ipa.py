#!/usr/bin/env python3
"""Synthetic structural fixtures only; never runnable or distributed applications."""
import importlib.util
import io
from pathlib import Path
import plistlib
import struct
import tarfile
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('validate_ipa', ROOT / 'tools/validate-ipa.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
EC_NAMES = 'ntdll ucrtbase xtajit64 d3d11 dxgi d3d12 kernel32 kernelbase win32u winemetal'.split()
NATIVE_NAMES = 'ntdll kernel32 kernelbase ucrtbase'.split()
VC_NAMES = '''concrt140 msvcp140 msvcp140_1 msvcp140_2 msvcp140_atomic_wait
msvcp140_codecvt_ids vcamp140 vccorlib140 vcomp140 vcruntime140
vcruntime140_1 vcruntime140_threads'''.split()


def macho(cpu=0x100000c, platform=2, filetype=2, entry=0x200, text_size=4):
    section = struct.pack('<16s16sQQIIIIIIII', b'__text', b'__TEXT', 0x100000200,
                          text_size, 0x200, 2, 0, 0, 0x80000400, 0, 0, 0)
    segment = struct.pack('<II16sQQQQIIII', 0x19, 152, b'__TEXT', 0x100000000,
                          0x1000, 0, 0x1000, 5, 5, 1, 0) + section
    commands = segment + struct.pack('<6I', 0x32, 24, platform, 0x110000, 0x120000, 0)
    if filetype == 2:
        commands += struct.pack('<IIQQ', 0x80000028, 24, entry, 0)
    data = bytearray(0x1000)
    data[:32] = struct.pack('<8I', 0xfeedfacf, cpu, 0, filetype, 3 if filetype == 2 else 2,
                            len(commands), 0, 0)
    data[32:32+len(commands)] = commands
    data[0x200:0x204] = b'\xc0\x03\x5f\xd6'
    return bytes(data)


def pe(machine=0x8664, hybrid=True, raw_size=0x200):
    data = bytearray(0x400)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3c, 0x80)
    data[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<HHIIIHH', data, 0x84, machine, 1, 0, 0, 0, 0xf0, 0x2022)
    optional = 0x98
    struct.pack_into('<H', data, optional, 0x20b)
    struct.pack_into('<I', data, optional+16, 0x1000)
    struct.pack_into('<Q', data, optional+24, 0x180000000)
    struct.pack_into('<II', data, optional+56, 0x2000, 0x200)
    struct.pack_into('<I', data, optional+108, 16)
    struct.pack_into('<8sIIIIIIHHI', data, optional+0xf0, b'.text', 0x200, 0x1000,
                     raw_size, 0x200, 0, 0, 0, 0, 0x60000020)
    data[0x200:0x204] = b'\xc0\x03\x5f\xd6'
    if hybrid:
        struct.pack_into('<II', data, optional+112+10*8, 0x1040, 208)
        struct.pack_into('<I', data, 0x240, 208)
        struct.pack_into('<Q', data, 0x240+200, 0x180001180)
    return bytes(data)


def prefix(remove=(), unsafe=False):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as t:
        for name in ('system.reg', 'user.reg', 'userdef.reg'):
            if name in remove:
                continue
            content = b'WINE REGISTRY Version 2\n#arch=win64\n'
            member = tarfile.TarInfo('prefix/' + name)
            member.size = len(content)
            t.addfile(member, io.BytesIO(content))
        member = tarfile.TarInfo('prefix/drive_c/windows/system32')
        member.type = tarfile.DIRTYPE
        t.addfile(member)
        if unsafe:
            t.addfile(tarfile.TarInfo('../escape'))
    return data.getvalue()


class Validation(unittest.TestCase):
    def files(self):
        return {
            'Info.plist': plistlib.dumps({'CFBundleExecutable': 'Madeira', 'CFBundleIdentifier': 'test.Madeira', 'CFBundlePackageType': 'APPL'}),
            'Madeira': macho(), 'prefix-template.tar.gz': prefix(),
            **{f'arm64ec-windows/{n}.dll': pe() for n in EC_NAMES},
            **{f'aarch64-windows/{n}.dll': pe(machine=0xaa64, hybrid=False) for n in NATIVE_NAMES},
            **{f'x86_64-vcruntime/{n}.dll': pe(hybrid=False) for n in VC_NAMES},
            'nls/l_intl.nls': b'synthetic NLS fixture',
            'd3d12/libmetalirconverter.dylib': macho(filetype=6),
            'Frameworks/StikJIT.framework/StikJIT': macho(filetype=6),
            'PlugIns/MadeiraJITHelper.appex/Info.plist': plistlib.dumps({'CFBundleExecutable': 'MadeiraJITHelper', 'CFBundleIdentifier': 'test.Madeira.JITHelper', 'CFBundlePackageType': 'XPC!'}),
            'PlugIns/MadeiraJITHelper.appex/MadeiraJITHelper': macho(),
        }

    def archive(self, replace=None, remove=()):
        files = self.files()
        files.update(replace or {})
        for name in remove:
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

    def test_rejects_header_only_executable(self):
        header = struct.pack('<8I6I', 0xfeedfacf, 0x100000c, 0, 2, 1, 24, 0, 0,
                             0x32, 24, 2, 0x110000, 0x120000, 0)
        with self.assertRaisesRegex(ValueError, 'executable'):
            validator.validate(self.archive({'Madeira': header}))

    def test_rejects_entry_outside_code(self):
        with self.assertRaisesRegex(ValueError, 'entry'):
            validator.validate(self.archive({'Madeira': macho(entry=0xf00)}))

    def test_rejects_empty_text_section(self):
        with self.assertRaisesRegex(ValueError, 'executable'):
            validator.validate(self.archive({'Madeira': macho(text_size=0)}))

    def test_rejects_truncated_load_commands(self):
        with self.assertRaisesRegex(ValueError, 'truncated'):
            validator.validate(self.archive({'Madeira': macho()[:40]}))

    def test_rejects_missing_runtime_resources(self):
        for resource in ('arm64ec-windows/xtajit64.dll', 'aarch64-windows/ntdll.dll',
                         'x86_64-vcruntime/vcruntime140.dll', 'nls/l_intl.nls',
                         'd3d12/libmetalirconverter.dylib', 'Frameworks/StikJIT.framework/StikJIT',
                         'PlugIns/MadeiraJITHelper.appex/MadeiraJITHelper'):
            with self.subTest(resource=resource), self.assertRaises(ValueError):
                validator.validate(self.archive(remove=[resource]))

    def test_rejects_bad_pe(self):
        with self.assertRaisesRegex(ValueError, 'PE'):
            validator.validate(self.archive({'arm64ec-windows/ucrtbase.dll': b'MZfixture'}))

    def test_rejects_wrong_native_architecture(self):
        with self.assertRaisesRegex(ValueError, 'architecture'):
            validator.validate(self.archive({'aarch64-windows/ntdll.dll': pe()}))

    def test_rejects_x64_masquerading_as_arm64ec(self):
        with self.assertRaisesRegex(ValueError, 'ARM64EC'):
            validator.validate(self.archive({'arm64ec-windows/ucrtbase.dll': pe(hybrid=False)}))

    def test_rejects_truncated_pe_section(self):
        with self.assertRaisesRegex(ValueError, 'PE'):
            validator.validate(self.archive({'arm64ec-windows/ucrtbase.dll': pe(raw_size=0x1000)}))

    def test_rejects_wrong_dylib_platform(self):
        with self.assertRaisesRegex(ValueError, 'iOS device'):
            validator.validate(self.archive({'d3d12/libmetalirconverter.dylib': macho(filetype=6, platform=7)}))

    def test_rejects_invalid_prefix(self):
        for value in (b'fixture', prefix(remove=['system.reg']), prefix(unsafe=True)):
            with self.subTest(value=value[:10]), self.assertRaisesRegex(ValueError, 'prefix'):
                validator.validate(self.archive({'prefix-template.tar.gz': value}))

    def test_rejects_unsafe_archive_path(self):
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            validator.validate(self.archive({'../../escape': b'bad'}))

    def test_rejects_plist_executable_path(self):
        with self.assertRaisesRegex(ValueError, 'CFBundleExecutable'):
            validator.validate(self.archive({'Info.plist': plistlib.dumps({'CFBundleExecutable': '../Madeira', 'CFBundlePackageType': 'APPL'})}))

    def test_rejects_non_dictionary_plist(self):
        with self.assertRaisesRegex(ValueError, 'plist'):
            validator.validate(self.archive({'Info.plist': plistlib.dumps([])}))

    def test_rejects_ambiguous_zip_path(self):
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            validator.validate(self.archive({'./alias': b'bad'}))

    def test_rejects_duplicate_zip_entry(self):
        p = self.archive()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(p, 'a') as z:
                z.writestr('Payload/Madeira.app/Madeira', macho())
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validator.validate(p)

    def test_compares_runtime_resources_to_staged_source(self):
        source = Path(self.temp.name) / 'source'
        for name, value in self.files().items():
            if name.startswith(('arm64ec-windows/', 'aarch64-windows/', 'x86_64-vcruntime/', 'nls/', 'd3d12/')) or name == 'prefix-template.tar.gz':
                target = source / 'app/Madeira' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(value)
        p = self.archive()
        self.assertTrue(validator.validate(p, source_root=source)['source_resources_match'])
        (source / 'app/Madeira/arm64ec-windows/ntdll.dll').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'source.*ntdll'):
            validator.validate(p, source_root=source)

    def test_accepts_current_redist_core_and_reports_missing_optional_dlls(self):
        optional = [name for name in VC_NAMES if name not in ('msvcp140', 'vcruntime140', 'vcruntime140_1')]
        result = validator.validate(self.archive(remove=['x86_64-vcruntime/'+name+'.dll' for name in optional]))
        self.assertIn('vcamp140.dll', result['optional_vcruntime_missing'])

    def test_validates_optional_redist_dll_when_present(self):
        with self.assertRaisesRegex(ValueError, 'PE'):
            validator.validate(self.archive({'x86_64-vcruntime/vcamp140.dll': b'MZfixture'}))


if __name__ == '__main__':
    unittest.main()
