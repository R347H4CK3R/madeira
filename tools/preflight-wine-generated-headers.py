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
           'mftransform', 'dwrite', 'dwrite_3',
           # These IDL dependencies are pulled through non-generated Wine
           # headers outside the scanner's direct source roots.
           'd2d1', 'strmif', 'exdisp')

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
    # The first generated headers may themselves include more IDL-generated
    # headers (e.g. d3d11.h -> d3d10shader.h). Resolve to a fixed point.
    pending = set(seeds)
    discovered = set()
    built = set()
    missing = set()
    missing_refs = set()
    make_exit_code = 0
    max_rounds = len(idl_map) + 1
    rounds = 0
    while pending:
        rounds += 1
        if rounds > max_rounds:
            print('ERROR: IDL closure exceeded available source files', file=sys.stderr)
            make_exit_code = 1
            break
        new_stems = pending - discovered
        pending = set()
        if not new_stems:
            break
        # Expand IDL-to-IDL imports as well as C includes from generated headers.
        stack = list(sorted(new_stems))
        while stack:
            stem = stack.pop()
            if stem in discovered:
                continue
            discovered.add(stem)
            path = idl_map.get(stem + '.idl')
            if path:
                for dep in IDL_REF.findall(path.read_text(errors='replace')):
                    dep_name = Path(dep).name
                    if dep_name in idl_map and dep_name[:-4] not in discovered:
                        stack.append(dep_name[:-4])
        targets = ['include/' + name + '.h' for name in sorted(discovered)
                   if name + '.idl' in idl_map
                   and not (include_dir / (name + '.h')).is_file()
                   and 'include/' + name + '.h' not in built]
        if targets:
            print(f'Wine IDL preflight round {rounds}: compiling {len(targets)} headers', flush=True)
            result = subprocess.run(['make', '-C', str(build), '-j4', *targets], check=False)
            if result.returncode:
                make_exit_code = result.returncode
            built.update(targets)
        for item in built:
            p = build / item
            if not p.is_file() or p.stat().st_size == 0:
                missing.add(item)
                continue
            for entry in C_INC.findall(p.read_text(errors='replace')):
                name = Path(entry).name
                stem = name.removesuffix('.h')
                if not name.endswith('.h') or stem + '.idl' not in idl_map:
                    continue
                if (output_dir / name).is_file() or (include_dir / name).is_file():
                    continue
                if stem not in discovered:
                    pending.add(stem)
        if make_exit_code or missing:
            break
    for item in built:
        p = build / item
        if not p.is_file():
            continue
        for entry in C_INC.findall(p.read_text(errors='replace')):
            name = Path(entry).name
            if name.endswith('.h') and name[:-2] + '.idl' in idl_map:
                if not (output_dir / name).is_file() and not (include_dir / name).is_file():
                    missing_refs.add(f'{item} -> include/{name}')
    targets = sorted(built)
    print(f'Wine header preflight: inspected {scanned} sources, {len(targets)} generated headers in {rounds} rounds', flush=True)
    report = dict(source_files_inspected=scanned, idl_headers_requested=targets,
                  dependency_closure_rounds=rounds, make_exit_code=make_exit_code,
                  missing_generated_headers=sorted(missing),
                  missing_transitive_header_references=sorted(missing_refs))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    for item in sorted(missing) + sorted(missing_refs):
        print('MISSING: ' + item, file=sys.stderr)
    if make_exit_code or missing or missing_refs:
        return 1
    print('PASS: pinned Wine IDL header closure verified before Unix compilation')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
