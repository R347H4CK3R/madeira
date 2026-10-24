#!/usr/bin/env python3
"""Check Madeira IPA structure and staged resource hashes; not execution or signature proof."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import plistlib
import stat
import struct
import tarfile
import zipfile

EC_DLLS = 'ntdll ucrtbase xtajit64 d3d11 dxgi d3d12 kernel32 kernelbase win32u winemetal'.split()
NATIVE_DLLS = 'ntdll kernel32 kernelbase ucrtbase'.split()
VC_DLLS = '''concrt140 msvcp140 msvcp140_1 msvcp140_2 msvcp140_atomic_wait
msvcp140_codecvt_ids vcamp140 vccorlib140 vcomp140 vcruntime140
vcruntime140_1 vcruntime140_threads'''.split()
VC_REQUIRED = ('msvcp140', 'vcruntime140', 'vcruntime140_1')


def safe_path(name):
    p = PurePosixPath(name)
    return bool(p.parts) and name.rstrip('/') == p.as_posix() and not p.is_absolute() and '..' not in p.parts and '\\' not in name and '\0' not in name


def check_macho(data, filetype=2):
    if len(data) < 32:
        raise ValueError('truncated Mach-O header')
    magic, cpu, subtype, kind, count, command_bytes, flags, reserved = struct.unpack_from('<8I', data)
    if magic != 0xfeedfacf or cpu != 0x100000c:
        raise ValueError('expected thin arm64 Mach-O')
    if kind != filetype:
        raise ValueError('expected Mach-O executable' if filetype == 2 else 'expected Mach-O dylib')
    end = 32 + command_bytes
    if end > len(data):
        raise ValueError('truncated Mach-O load commands')
    offset = 32
    ios = False
    code_ranges = []
    entry = None
    for _ in range(count):
        if offset + 8 > end:
            raise ValueError('truncated Mach-O load command')
        cmd, size = struct.unpack_from('<2I', data, offset)
        if size < 8 or size % 8 or offset + size > end:
            raise ValueError('invalid Mach-O load command size')
        if cmd == 0x32:  # LC_BUILD_VERSION
            if size < 24:
                raise ValueError('truncated build version')
            if struct.unpack_from('<I', data, offset + 8)[0] != 2:
                raise ValueError('expected iOS device platform load command')
            ios = True
        elif cmd == 0x25 and size >= 16:  # LC_VERSION_MIN_IPHONEOS
            ios = True
        elif cmd == 0x19:  # LC_SEGMENT_64
            if size < 72:
                raise ValueError('truncated Mach-O segment')
            _, _, _, vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, _ = struct.unpack_from('<II16sQQQQIIII', data, offset)
            if size < 72 + 80*nsects or fileoff+filesize > len(data) or filesize > vmsize:
                raise ValueError('invalid Mach-O segment bounds')
            for index in range(nsects):
                section = struct.unpack_from('<16s16sQQIIIIIIII', data, offset+72+80*index)
                _, _, addr, length, raw, align, reloff, nreloc, secflags, _, _, _ = section
                # S_ATTR_PURE_INSTRUCTIONS or S_ATTR_SOME_INSTRUCTIONS.
                if initprot & 4 and secflags & 0x80000400 and length:
                    if raw < fileoff or raw+length > fileoff+filesize or addr < vmaddr or addr+length > vmaddr+vmsize or addr-vmaddr != raw-fileoff:
                        raise ValueError('invalid Mach-O executable section bounds')
                    code_ranges.append((raw, raw+length))
        elif cmd == 0x80000028:  # LC_MAIN
            if size < 24 or entry is not None:
                raise ValueError('invalid Mach-O entry command')
            entry = struct.unpack_from('<Q', data, offset+8)[0]
        offset += size
    if offset != end:
        raise ValueError('inconsistent Mach-O load command count')
    if not ios:
        raise ValueError('expected iOS device platform load command')
    if not code_ranges:
        raise ValueError('missing Mach-O executable code section')
    if filetype == 2 and (entry is None or not any(start <= entry < stop for start, stop in code_ranges)):
        raise ValueError('Mach-O entry must map to an executable code section')
    return 'arm64'


def check_pe(data, architecture):
    if len(data) < 64 or data[:2] != b'MZ':
        raise ValueError('truncated or invalid PE DOS header')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    if pe < 64 or pe+24 > len(data) or data[pe:pe+4] != b'PE\0\0':
        raise ValueError('invalid PE signature')
    machine, count, _, _, _, optional_size, characteristics = struct.unpack_from('<HHIIIHH', data, pe+4)
    expected = {'arm64': (0xaa64,), 'arm64ec': (0x8664, 0xa641), 'x86_64': (0x8664,)}[architecture]
    if machine not in expected:
        raise ValueError('wrong PE architecture: expected ' + architecture)
    optional = pe+24
    table = optional+optional_size
    if not count or optional_size < 112 or table+count*40 > len(data):
        raise ValueError('truncated PE headers or sections')
    if struct.unpack_from('<H', data, optional)[0] != 0x20b or characteristics & 0x2002 != 0x2002:
        raise ValueError('expected PE32+ executable DLL')
    image_base = struct.unpack_from('<Q', data, optional+24)[0]
    image_size, header_size = struct.unpack_from('<II', data, optional+56)
    directory_count = struct.unpack_from('<I', data, optional+108)[0]
    if header_size < table+count*40 or header_size > len(data) or image_size < header_size or 112+directory_count*8 > optional_size:
        raise ValueError('invalid PE optional header bounds')
    sections = []
    code = False
    for index in range(count):
        _, virtual_size, rva, raw_size, raw, _, _, _, _, flags = struct.unpack_from('<8sIIIIIIHHI', data, table+40*index)
        if rva+max(virtual_size, raw_size) > image_size or (raw_size and (raw < header_size or raw+raw_size > len(data))):
            raise ValueError('invalid PE section bounds')
        sections.append((rva, raw_size, raw))
        code |= bool(raw_size and flags & 0x20000000 and flags & 0x20)
    if not code:
        raise ValueError('missing PE executable code section')

    def mapped(rva, length):
        for section_rva, raw_size, raw in sections:
            delta = rva-section_rva
            if delta >= 0 and delta+length <= raw_size:
                return raw+delta
        raise ValueError('PE RVA does not map to file data')

    if architecture == 'arm64ec':
        # ARM64EC's hybrid image commonly declares AMD64, so machine alone
        # cannot distinguish it from an unrelated x64 DLL.
        if directory_count <= 10:
            raise ValueError('missing ARM64EC load config')
        config_rva, config_size = struct.unpack_from('<II', data, optional+112+10*8)
        if config_size < 208:
            raise ValueError('missing ARM64EC CHPE metadata')
        config = mapped(config_rva, 208)
        if struct.unpack_from('<I', data, config)[0] < 208:
            raise ValueError('truncated ARM64EC load config')
        metadata = struct.unpack_from('<Q', data, config+200)[0]
        if metadata < image_base:
            raise ValueError('missing ARM64EC CHPE metadata')
        mapped(metadata-image_base, 4)
    return architecture


def check_prefix(data):
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            members = {}
            for member in archive:
                if not safe_path(member.name) or PurePosixPath(member.name).parts[0] != 'prefix' or member.issym() or member.islnk():
                    raise ValueError('unsafe prefix archive entry: ' + member.name)
                name = member.name.rstrip('/')
                if name in members:
                    raise ValueError('duplicate prefix archive entry: ' + name)
                members[name] = member
            for name in ('system.reg', 'user.reg', 'userdef.reg'):
                member = members.get('prefix/' + name)
                if member is None or not member.isfile() or not archive.extractfile(member).read(64).startswith(b'WINE REGISTRY Version 2'):
                    raise ValueError('missing or invalid prefix registry: ' + name)
            system = members.get('prefix/drive_c/windows/system32')
            if system is None or not system.isdir():
                raise ValueError('missing prefix system32 directory')
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise ValueError('invalid gzip tar prefix archive') from exc


def validate(path, source_root=None):
    path = Path(path)
    resources = {}
    source_checked = []
    optional_vcruntime_missing = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError('duplicate ZIP entry')
        for entry in z.infolist():
            if not safe_path(entry.filename) or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('unsafe ZIP entry: ' + entry.filename)
        corrupt = z.testzip()
        if corrupt:
            raise ValueError('corrupt ZIP entry: ' + corrupt)
        plists = [n for n in names if len(PurePosixPath(n).parts) == 3 and n.startswith('Payload/') and n.endswith('.app/Info.plist')]
        if len(plists) != 1:
            raise ValueError('expected one Payload/*.app/Info.plist')
        base = plists[0][:-len('Info.plist')]
        info = plistlib.loads(z.read(plists[0]))
        if not isinstance(info, dict):
            raise ValueError('app plist must be a dictionary')
        executable = info.get('CFBundleExecutable')
        if not isinstance(executable, str) or not executable or '/' in executable or '\\' in executable or executable in ('.', '..'):
            raise ValueError('invalid CFBundleExecutable')
        if info.get('CFBundlePackageType') != 'APPL':
            raise ValueError('bundle must declare APPL')
        if base != 'Payload/Madeira.app/' or executable != 'Madeira' or not isinstance(info.get('CFBundleIdentifier'), str) or not info['CFBundleIdentifier']:
            raise ValueError('expected Madeira app identity')

        def resource(name, compare_source=True):
            if base+name not in names:
                raise ValueError('missing runtime resource: ' + name)
            payload = z.read(base+name)
            if not payload:
                raise ValueError('empty runtime resource: ' + name)
            digest = hashlib.sha256(payload).hexdigest()
            resources[name] = digest
            if source_root is not None and compare_source:
                expected = Path(source_root) / 'app/Madeira' / name
                if not expected.is_file() or hashlib.sha256(expected.read_bytes()).hexdigest() != digest:
                    raise ValueError('source resource mismatch: ' + name)
                source_checked.append(name)
            return payload

        arch = check_macho(resource(executable, compare_source=False))
        check_prefix(resource('prefix-template.tar.gz'))
        for folder, dlls, architecture in (('arm64ec-windows', EC_DLLS, 'arm64ec'),
                                           ('aarch64-windows', NATIVE_DLLS, 'arm64'),
                                           ('x86_64-vcruntime', VC_DLLS, 'x86_64')):
            for name in dlls:
                filename = folder+'/'+name+'.dll'
                if folder == 'x86_64-vcruntime' and name not in VC_REQUIRED and base+filename not in names:
                    optional_vcruntime_missing.append(name+'.dll')
                    continue
                try:
                    check_pe(resource(filename), architecture)
                except ValueError as exc:
                    raise ValueError(filename + ': ' + str(exc)) from exc
        resource('nls/l_intl.nls')
        # Xcode ad-hoc signs its copied converter, changing signature bytes.
        # Structure is checked here; its staged source is hash-checked by deps.sh.
        check_macho(resource('d3d12/libmetalirconverter.dylib', compare_source=False), filetype=6)
        check_macho(resource('Frameworks/StikJIT.framework/StikJIT', compare_source=False), filetype=6)
        helper = 'PlugIns/MadeiraJITHelper.appex/'
        helper_info = plistlib.loads(resource(helper+'Info.plist', compare_source=False))
        if not isinstance(helper_info, dict) or helper_info.get('CFBundleExecutable') != 'MadeiraJITHelper' or helper_info.get('CFBundlePackageType') != 'XPC!' or helper_info.get('CFBundleIdentifier') != info['CFBundleIdentifier']+'.JITHelper':
            raise ValueError('invalid JIT helper bundle identity')
        check_macho(resource(helper+'MadeiraJITHelper', compare_source=False))
    with path.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    return {'file': path.name, 'size_bytes': path.stat().st_size, 'sha256': digest,
            'architecture': arch, 'bundle_identifier': info.get('CFBundleIdentifier'),
            'version': info.get('CFBundleShortVersionString'), 'build': info.get('CFBundleVersion'),
            'resources_sha256': resources, 'source_resources_match': True if source_root is not None else None,
            'source_resources_checked': source_checked,
            'optional_vcruntime_missing': optional_vcruntime_missing,
            'validation': 'selected Mach-O/PE structures, prefix and required resources; not proof of compilation or execution',
            'signing': 'requires separate codesign/provisioning validation', 'runtime_test': 'not performed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--source-root', type=Path, help='compare selected resources against this staged repository')
    args = parser.parse_args()
    try:
        result = validate(args.ipa, source_root=args.source_root)
    except (ValueError, KeyError, OSError, zipfile.BadZipFile, plistlib.InvalidFileException) as e:
        parser.exit(1, f'IPA validation failed: {e}\n')
    report = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(report)
    print(report, end='')


if __name__ == '__main__':
    main()
