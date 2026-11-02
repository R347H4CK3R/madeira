#!/usr/bin/env python3
"""Explain which inputs block a reproducible native Madeira/StrataForge build.

Read-only and intentionally strict. A source checkout is not a native build.
"""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
items={
 "FEX iOS archive":root/"FEX/build-ios/FEXCore/Source/libFEXCore.a",
 "FEX base iOS archive":root/"FEX/build-ios/FEXCore/Source/libFEXCore_Base.a",
 "Wine server BASE archive (required by patch-based build script)":root/"app/Madeira/libwineserver.a",
 "Wine native NTDLL archive":root/"app/Madeira/libntdll_unix.a",
 "DXMT native iOS archive":root/"app/Madeira/libdxmt_combined.a",
 "LLVM iOS build":root/"toolchains/llvm-ios-build",
 "LLVM host build":root/"toolchains/llvm-host-build",
 "Cross compiler":root/"toolchains/llvm-mingw-20260421-ucrt-macos-universal",
}
report={name:{"present":p.exists() and (p.is_dir() or p.stat().st_size>0),"relative":str(p.relative_to(root))} for name,p in items.items()}
print(json.dumps(report,indent=2))
if any(not x["present"] for x in report.values()):
 print("BLOCKED: Requires actual source-built or trusted verified compatible archives/toolchains; an IPA cannot be used as a linkable static archive.")
 raise SystemExit(2)
print("Required native build inputs present; Visual C++ redist is provisioned separately in-app.")
