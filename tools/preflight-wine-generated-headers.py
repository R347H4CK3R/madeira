#!/usr/bin/env python3
"""Generate Wine IDL headers and verify their dependency closure before native builds."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

IDL_REF = re.compile(r'\bimport\s+"([^"\n]+\.idl)"', re.I)
C_INC = re.compile(r'^\s*#\s*include\s*[<"]([^">\n]+)[">]', re.M)
DEFAULT = ('wtypesbase', 'unknwn', 'objidlbase', 'wtypes', 'mfobjects',
           'mftransform', 'dwrite', 'dwrite_3')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wine', type=Path, required=True)
    ap.add_argument('--build', type=Path, required=True)
    ap.add_argument('--repository', type=Path, required=True)
    ap.add_argument('--report', type=Path, default=Path('/tmp/wine-headers-preflight.json'))
    args = ap.parse_args()
    wine, build, repo = (p.resolve() for p in (args.wine, args.build, args.repository))
    include_dir = wine / 'include'
    output_dir = build / 'include'
    if not (build / 'include/config.h').is_file() or not include_dir.is_dir():
        sys.exit('ERROR: pinned Wine sources and configured headers required')
    idl_map = {p.name: p for p in include_dir.glob('*.idl')}
    seeds = set(DEFAULT)
    code_roots = [wine / 'dlls/ntdll/unix', wine / 'dlls/win32u',
                  repo / 'build/ntdll-unix', repo / 'build/win32u-unix']
    scanned = 0
    for root in code_roots:
        if not root.is_dir():
            sys.exit(f'ERROR: missing Wine source directory: {root}')
        for p in root.rglob('*'):
            if p.suffix not in ('.c', '.h') or not p.is_file():
                continue
            scanned += 1
            for entry in C_INC.findall(p.read_text(errors='replace')):
                name = Path(entry).name
                if name.endswith('.h') and name[:-2] + '.idl' in idl_map:
                    seeds.add(name[:-2])
    pending = sorted(seeds)
    discovered = set()
    while pending:
        stem = pending.pop()
        if stem in discovered:
            continue
        discovered.add(stem)
        path = idl_map.get(stem + '.idl')
        if path:
            for dep in IDL_REF.findall(path.read_text(errors='replace')):
                name = Path(dep).name
                if name in idl_map and name[:-4] not in discovered:
                    pending.append(name[:-4])
    targets = ['include/' + name + '.h' for name in sorted(discovered)
               if not (include_dir / (name + '.h')).is_file()]
    if not targets:
        sys.exit('ERROR: no Wine IDL targets found; check source revision')
    print(f'Wine header preflight: inspected {scanned} sources, building {len(targets)} IDL headers', flush=True)
    result = subprocess.run(['make', '-C', str(build), '-j4', *targets], check=False)
    missing = [item for item in targets if not (build / item).is_file()
               or (build / item).stat().st_size == 0]
    missing_refs = set()
    for item in targets:
        p = build / item
        if not p.is_file():
            continue
        for entry in C_INC.findall(p.read_text(errors='replace')):
            name = Path(entry).name
            stem = name.removesuffix('.h')
            if name.endswith('.h') and stem + '.idl' in idl_map:
                if not (output_dir / name).is_file() and not (include_dir / name).is_file():
                    missing_refs.add(f'{item} -> include/{name}')
    report = dict(source_files_inspected=scanned, idl_headers_requested=targets,
                  make_exit_code=result.returncode, missing_generated_headers=missing,
                  missing_transitive_header_references=sorted(missing_refs))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    for item in missing + sorted(missing_refs):
        print('MISSING: ' + item, file=sys.stderr)
    if result.returncode or missing or missing_refs:
        return 1
    print('PASS: pinned Wine IDL header closure verified before Unix compilation')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
