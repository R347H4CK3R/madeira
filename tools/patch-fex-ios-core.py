#!/usr/bin/env python3
"""Apply fail-closed, idempotent overlays to the pinned FEX Core.cpp.

The iOS build intentionally disables rpmalloc in FEX CMake, so rpmalloc's
optional remote-free CAS diagnostics must not create an unresolved reference.
This changes diagnostic instrumentation only, not guest execution or allocators.
"""
from pathlib import Path
import sys

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("FEX/FEXCore/Source/Interface/Core/Core.cpp")
source = path.read_text()
changed = False

# Keep the host-only FEX telemetry from leaking into non-iOS builds.
start = "  {\n    static uint64_t FfsLastCount = 0;"
end = "  /* iOS-Madeira: refuse to compile obviously-invalid guest RIPs."
if "#ifdef FEX_IOS_HOST\n" + start not in source:
    if source.count(start) != 1 or source.count(end) != 1:
        raise SystemExit("BLOCKED: unexpected pinned FEX Core.cpp telemetry layout")
    a = source.index(start)
    b = source.index(end, a)
    block = source[a:b]
    if "IosFfsBypassLog" not in block or "IosCbEntryLog" not in block:
        raise SystemExit("BLOCKED: missing expected telemetry identifiers")
    source = source[:a] + "#ifdef FEX_IOS_HOST\n" + block + "#endif // FEX_IOS_HOST telemetry\n\n" + source[b:]
    changed = True
    print("Guarded both iOS-only FEX telemetry reporters")
else:
    print("FEX telemetry platform guard already installed")

# The pinned FEX CMakeLists.txt disables rpmalloc for Apple (including iOS).
# Core.cpp nevertheless references its optional rpm_cas_snapshot_take logger.
# Exclude that diagnostic on Apple rather than inventing a stub/allocator or
# weakening the linker. Non-Apple builds retain the original instrumentation.
cas_start = "      {\n        rpm_cas_snapshot Snap;\n        if (rpm_cas_snapshot_take(&Snap)) {"
cas_end = "                            Snap.fail_changed, Snap.fail_unchanged, Snap.fail_invalid);\n        }\n      }"
cas_guard = "#if !defined(__APPLE__) // rpmalloc CAS snapshot provider is disabled on Apple"
if cas_guard not in source:
    if source.count(cas_start) != 1 or source.count(cas_end) != 1:
        raise SystemExit("BLOCKED: unexpected pinned FEX rpmalloc CAS diagnostic layout")
    if source.index(cas_start) >= source.index(cas_end):
        raise SystemExit("BLOCKED: malformed FEX CAS diagnostic boundaries")
    source = source.replace(cas_start, cas_guard + "\n" + cas_start, 1)
    source = source.replace(cas_end, cas_end + "\n#endif // !__APPLE__ rpmalloc snapshot", 1)
    changed = True
    print("Guarded absent rpmalloc CAS diagnostics on Apple; no allocator stub added")
else:
    if source.count(cas_guard) != 1:
        raise SystemExit("BLOCKED: duplicate FEX rpmalloc CAS guard")
    print("FEX rpmalloc CAS platform guard already installed")

if changed:
    path.write_text(source)
else:
    print("FEX overlays already applied")
