#!/usr/bin/env python3
"""Audit the actual IPA ZIP and fail closed on incomplete public integration builds.

Checks bundle paths and resource presence; cannot prove runtime JIT/game compatibility.
No external Python packages are required.
"""
import argparse
import hashlib
import json
import plistlib
import sys
import zipfile
from pathlib import Path

PREFIX = "Payload/Madeira.app/"
REQUIRED = (
    "Info.plist",
    "d3d12/libmetalirconverter.dylib",
    "d3d12/NOTICE.txt",
    "x86_64-vcruntime/README-runtime-not-included.txt",
)
MIN_BINARY_SIZE = 4096


def inspect_ipa(path: Path, public: bool) -> dict:
    result = {
        "ipa": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "public_build": public,
        "checks": {},
    }
    checks = result["checks"]
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        items = set(names)
        checks["no_duplicate_paths"] = len(items) == len(names)
        checks["no_unsafe_paths"] = all(
            not n.startswith("/") and "\\" not in n
            and all(part not in ("..", ".") for part in n.split("/"))
            for n in names
        )
        checks["zip_integrity"] = z.testzip() is None
        checks["bundle_present"] = any(x.startswith(PREFIX) for x in names)
        for item in REQUIRED:
            checks["resource:" + item] = (
                PREFIX + item in items and z.getinfo(PREFIX + item).file_size > 0
            ) if PREFIX + item in items else False
        plist_path = PREFIX + "Info.plist"
        if plist_path in items:
            try:
                info = plistlib.loads(z.read(plist_path))
                exe = info.get("CFBundleExecutable")
                checks["executable_declared"] = isinstance(exe, str) and bool(exe)
                checks["executable_exists"] = (
                    bool(exe) and PREFIX + exe in items
                    and z.getinfo(PREFIX + exe).file_size >= MIN_BINARY_SIZE
                )
            except (ValueError, TypeError, OSError, KeyError):
                checks["executable_declared"] = False
                checks["executable_exists"] = False
        else:
            checks["executable_declared"] = False
            checks["executable_exists"] = False
        converter = PREFIX + "d3d12/libmetalirconverter.dylib"
        checks["converter_nontrivial"] = (
            converter in items and z.getinfo(converter).file_size >= MIN_BINARY_SIZE
        )
        if public:
            # Never upload a public artifact that accidentally includes Microsoft's
            # DLLs. User-owned private packaging happens outside GitHub Actions.
            checks["no_windows_runtime_dlls"] = not any(
                n.lower().endswith(".dll")
                and (n.startswith(PREFIX + "x86_64-vcruntime/")
                     or "/vc-runtime-x64/" in n)
                for n in names
            )
    result["passed"] = all(checks.values())
    result["limits"] = (
        "Checks package structure and presence only; does not verify device JIT, "
        "Steam, Wine startup, Direct3D rendering, or code signing."
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ipa", type=Path)
    parser.add_argument("--public-build", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = inspect_ipa(args.ipa, args.public_build)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        print(f"IPA audit failed: {exc}", file=sys.stderr)
        return 2
    payload = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload, encoding="utf-8")
    print(payload)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
