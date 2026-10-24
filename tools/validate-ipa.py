#!/usr/bin/env python3
"""Validate Madeira IPA structure and record provenance; does not prove launch or signing."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import struct
import zipfile


def check_macho(data):
    if len(data) < 32:
        raise ValueError('truncated Mach-O header')
    magic, cpu, subtype, kind, count, command_bytes, flags, reserved = struct.unpack_from('<8I', data)
    if magic != 0xfeedfacf or cpu != 0x100000c:
        raise ValueError('expected thin arm64 Mach-O')
    if kind != 2:
        raise ValueError('expected Mach-O executable')
    end = 32 + command_bytes
    if end > len(data):
        raise ValueError('truncated Mach-O load commands')
    offset = 32
    ios = False
    for _ in range(count):
        if offset + 8 > end:
            raise ValueError('truncated Mach-O load command')
        cmd, size = struct.unpack_from('<2I', data, offset)
        if size < 8 or size % 8 or offset + size > end:
            raise ValueError('invalid Mach-O load command size')
        if cmd == 0x32:  # LC_BUILD_VERSION
            if size < 24:
                raise ValueError('truncated build version')
            ios |= struct.unpack_from('<I', data, offset + 8)[0] == 2
        if cmd == 0x25 and size >= 16:  # LC_VERSION_MIN_IPHONEOS
            ios = True
        offset += size
    if offset != end:
        raise ValueError('inconsistent Mach-O load command count')
    if not ios:
        raise ValueError('expected iOS device platform load command')
    return 'arm64'


def validate(path):
    path = Path(path)
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError('duplicate ZIP entry')
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name:
                raise ValueError('unsafe ZIP entry: ' + name)
        corrupt = z.testzip()
        if corrupt:
            raise ValueError('corrupt ZIP entry: ' + corrupt)
        plists = [n for n in names if len(PurePosixPath(n).parts) == 3 and n.startswith('Payload/') and n.endswith('.app/Info.plist')]
        if len(plists) != 1:
            raise ValueError('expected one Payload/*.app/Info.plist')
        base = plists[0][:-len('Info.plist')]
        info = plistlib.loads(z.read(plists[0]))
        executable = info.get('CFBundleExecutable')
        if not isinstance(executable, str) or not executable or '/' in executable or '\\' in executable or executable in ('.', '..'):
            raise ValueError('invalid CFBundleExecutable')
        if info.get('CFBundlePackageType') != 'APPL':
            raise ValueError('bundle must declare APPL')
        if base + executable not in names:
            raise ValueError('missing app executable')
        arch = check_macho(z.read(base + executable))
        required = ['prefix-template.tar.gz'] + ['arm64ec-windows/' + n for n in ('ntdll.dll', 'ucrtbase.dll', 'xtajit64.dll', 'd3d11.dll', 'dxgi.dll', 'd3d12.dll')]
        resources = {}
        for name in required:
            if base + name not in names:
                raise ValueError('missing runtime resource: ' + name)
            payload = z.read(base + name)
            if not payload:
                raise ValueError('empty runtime resource: ' + name)
            if name.endswith('.dll') and not payload.startswith(b'MZ'):
                raise ValueError('invalid PE runtime resource: ' + name)
            resources[name] = hashlib.sha256(payload).hexdigest()
    with path.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    return {'file': path.name, 'size_bytes': path.stat().st_size, 'sha256': digest,
            'architecture': arch, 'bundle_identifier': info.get('CFBundleIdentifier'),
            'version': info.get('CFBundleShortVersionString'), 'build': info.get('CFBundleVersion'),
            'resources_sha256': resources, 'validation': 'archive structure and selected runtime resources only',
            'signing': 'requires separate codesign/provisioning validation', 'runtime_test': 'not performed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.ipa)
    except (ValueError, KeyError, OSError, zipfile.BadZipFile, plistlib.InvalidFileException) as e:
        parser.exit(1, f'IPA validation failed: {e}\n')
    report = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(report)
    print(report, end='')


if __name__ == '__main__':
    main()
