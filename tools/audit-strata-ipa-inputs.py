#!/usr/bin/env python3
"""Fail-closed iOS app link-input audit. Not a build or runtime test."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    ("FEXCore", "FEX/build-ios/FEXCore/Source/libFEXCore.a", "build/fex-ios/build.sh"),
    ("FEXCore_Base", "FEX/build-ios/FEXCore/Source/libFEXCore_Base.a", "build/fex-ios/build.sh"),
    ("FEX Jemalloc", "FEX/build-ios/FEXCore/Source/libJemallocLibs.a", "build/fex-ios/build.sh"),
    ("FEX fmt", "FEX/build-ios/External/fmt/libfmt.a", "build/fex-ios/build.sh"),
    ("FEX cephes", "FEX/build-ios/External/cephes/libcephes_128bit.a", "build/fex-ios/build.sh"),
    ("FEX xxhash", "FEX/build-ios/External/xxhash/cmake_unofficial/libxxhash.a", "build/fex-ios/build.sh"),
    ("FEX softfloat", "FEX/build-ios/External/SoftFloat-3e/libsoftfloat_3e.a", "build/fex-ios/build.sh"),
    ("Wine server", "app/Madeira/libwineserver.a", "build/wineserver/build.sh"),
    ("Wine ntdll unix", "app/Madeira/libntdll_unix.a", "build/ntdll-unix/build.sh"),
    ("Wine win32u unix", "app/Madeira/libwin32u_unix.a", "build/win32u-unix/build.sh"),
    ("DXMT", "app/Madeira/libdxmt_combined.a", "build/dxmt-ios/build.sh + iOS LLVM"),
    ("Rust pairing", "app/Madeira/libmadeira_rppairing.a", "build/rppairing-ios/build.sh"),
    ("FFmpeg avformat", "app/Madeira/libavformat.a", "build/ffmpeg/build.sh"),
    ("FFmpeg avcodec", "app/Madeira/libavcodec.a", "build/ffmpeg/build.sh"),
    ("FFmpeg swresample", "app/Madeira/libswresample.a", "build/ffmpeg/build.sh"),
    ("FFmpeg avutil", "app/Madeira/libavutil.a", "build/ffmpeg/build.sh"),
    ("GnuTLS", "app/Madeira/libgnutls.a", "build/gnutls-ios/build.sh"),
    ("Nettle", "app/Madeira/libnettle.a", "build/gnutls-ios/build.sh"),
    ("Hogweed", "app/Madeira/libhogweed.a", "build/gnutls-ios/build.sh"),
    ("GMP", "app/Madeira/libgmp.a", "build/gnutls-ios/build.sh"),
]
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/tmp/madeira-ipa-prerequisites.json")
    args = parser.parse_args()
    checks = []
    for name, relative, producer in REQUIRED:
        p = ROOT / relative
        ready = p.is_file() and p.stat().st_size > 0
        checks.append(dict(name=name, path=relative, ready=ready, producer=producer))
    runtime = ROOT / "app/Madeira/x86_64-vcruntime"
    ready = runtime.is_dir() and any(
        p.is_file() and p.name.lower() == "vcruntime140.dll" and p.stat().st_size > 0
        for p in runtime.iterdir()
    )
    checks.append(dict(name="Microsoft x64 VC++ runtime",
                       path="app/Madeira/x86_64-vcruntime/vcruntime140.dll",
                       ready=ready,
                       producer="user-provided legitimate Microsoft VC++ runtime"))
    missing = [c for c in checks if not c["ready"]]
    data = dict(assessment="Link-input presence only; not build, IPA or JIT proof",
                ready_for_xcode_attempt=not missing,
                available_count=len(checks)-len(missing),
                missing_count=len(missing), requirements=checks)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n")
    print("Madeira inputs:", data["available_count"], "present;", len(missing), "missing")
    for c in missing:
        print("MISSING:", c["path"], "| producer:", c["producer"])
    return 1 if missing else 0
if __name__ == "__main__":
    raise SystemExit(main())
