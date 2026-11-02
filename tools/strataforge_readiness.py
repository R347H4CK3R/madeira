#!/usr/bin/env python3
"""Read-only StrataForge repository readiness audit. No device claims."""
from __future__ import annotations
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
checks = {
    "build_guide": (root / "docs/BUILDING.md").exists(),
    "submodule_manifest": (root / ".gitmodules").exists(),
    "strata_verification_plan": (root / "docs/STRATAFORGE_VERIFICATION.md").exists(),
    "license": (root / "LICENSE").exists() or (root / "COPYING").exists(),
    "ios_app_sources": (root / "app").is_dir(),
    "build_scripts": (root / "build").is_dir(),
}
dep_inputs = ("FEX", "wine", "dxmt", "madeira-dock")
checks.update({f"dependency_present_{name}": (root/name).is_dir() and any((root/name).iterdir()) for name in dep_inputs})
# Source checkout is not the same as a native iOS linkable runtime.
required_binaries = {
    "fex_core_ios": "FEX/build-ios/FEXCore/Source/libFEXCore.a",
    "fex_core_base_ios": "FEX/build-ios/FEXCore/Source/libFEXCore_Base.a",
    "wine_server_ios": "app/Madeira/libwineserver.a",
    "dxmt_ios": "app/Madeira/libdxmt_combined.a",
}
checks.update({f"native_binary_{name}": (root / relative).is_file() and (root / relative).stat().st_size > 0
              for name, relative in required_binaries.items()})
checks["windows_vcruntime_assets"] = (root / "app/Madeira/x86_64-vcruntime").is_dir()

report = {
    "project": "StrataForge",
    "scope": "repository-only",
    "checks": checks,
    "ready_for_native_compile": all(checks.values()),
    "physical_device_verified": False,
    "jit_verified": False,
    "wine_fex_verified": False,
    "strata_guest_verified": False,
    "gameplay_verified": False,
}
output = root / "strataforge-readiness.json"
output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
sys.exit(0)  # audit records missing inputs; it does not claim a successful native build
