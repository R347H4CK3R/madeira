#!/usr/bin/env python3
"""Extract unmodified Microsoft x64 runtime DLLs from the official redist.

7-Zip opens Burn's attached cabinet; nested MSI/cabinet payloads may use
internal file identifiers. OriginalFilename in the PE version resource restores
their shipped names. This never strips, patches, or rewrites a DLL.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

NAMES = set('''concrt140.dll msvcp140.dll msvcp140_1.dll msvcp140_2.dll
msvcp140_atomic_wait.dll msvcp140_codecvt_ids.dll vcamp140.dll vccorlib140.dll
vcomp140.dll vcruntime140.dll vcruntime140_1.dll vcruntime140_threads.dll'''.split())
CORE = {'vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll'}


def signed_x64(data):
    try:
        pe = struct.unpack_from('<I', data, 0x3c)[0]
        if data[:2] != b'MZ' or data[pe:pe+4] != b'PE\0\0':
            return False
        if struct.unpack_from('<H', data, pe+4)[0] != 0x8664:
            return False
        if struct.unpack_from('<H', data, pe+24)[0] != 0x20b:
            return False
        off, size = struct.unpack_from('<II', data, pe+24+112+4*8)
        return size >= 8 and off > 0 and off+size <= len(data)
    except struct.error:
        return False


def original_name(data):
    key = 'OriginalFilename\0'.encode('utf-16le')
    start = data.find(key)
    if start < 0:
        return None
    start = (start+len(key)+3) & ~3
    end = start
    while end+1 < len(data) and data[end:end+2] != b'\0\0':
        end += 2
    try:
        return data[start:end].decode('utf-16le').lower()
    except UnicodeDecodeError:
        return None


def validate_folder(destination):
    result = {}
    for path in destination.iterdir() if destination.is_dir() else []:
        if path.name.lower() not in NAMES:
            continue
        data = path.read_bytes()
        if not signed_x64(data):
            raise ValueError(f'Not an intact signed x64 Microsoft runtime: {path}')
        result[path.name.lower()] = hashlib.sha256(data).hexdigest()
    if missing := CORE-result.keys():
        raise ValueError('Missing Microsoft x64 runtime inputs: '+', '.join(sorted(missing)))
    return result


def extract(installer, destination):
    executable = shutil.which('7zz')
    if not executable:
        raise ValueError('7zz is required to extract VC_redist.x64.exe')
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='madeira-vcredist-') as folder:
        root = Path(folder)

        def unpack(path, target):
            subprocess.run([executable, 'x', '-y', str(path.resolve()), '-o'+str(target)], check=True)

        unpack(installer, root/'outer')
        seen = set()
        for _ in range(6):
            containers = []
            for path in root.rglob('*'):
                if not path.is_file():
                    continue
                with path.open('rb') as file:
                    magic = file.read(8)
                if not (magic.startswith(b'MSCF') or magic == bytes.fromhex('d0cf11e0a1b11ae1')):
                    continue
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if digest not in seen:
                    seen.add(digest)
                    containers.append((path, root/('payload-'+digest)))
            if not containers:
                break
            for path, target in containers:
                unpack(path, target)

        candidates = {}
        for path in root.rglob('*'):
            if not path.is_file():
                continue
            with path.open('rb') as file:
                if file.read(2) != b'MZ':
                    continue
            data = path.read_bytes()
            if not signed_x64(data):
                continue
            name = path.name.lower()
            if name not in NAMES:
                name = original_name(data)
            if name not in NAMES:
                continue
            digest = hashlib.sha256(data).hexdigest()
            if name in candidates and candidates[name][0] != digest:
                raise ValueError(f'Redist contains different signed binaries named {name}; select the intended version explicitly')
            candidates[name] = digest, path
        for name, (_, path) in candidates.items():
            shutil.copyfile(path, destination/name)
    return validate_folder(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--installer', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = extract(args.installer, args.destination) if args.installer else validate_folder(args.destination)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'VC runtime input failure: {error}\n')
    args.report.write_text(json.dumps(result, indent=2)+'\n')
    print('Staged unmodified Microsoft x64 runtime DLLs: '+', '.join(sorted(result)))


if __name__ == '__main__':
    main()
