#!/usr/bin/env python3
"""Guard FEX iOS-only telemetry in the pinned source during host builds.

This is a minimal, idempotent overlay. Keep the pinned FEX gitlink unchanged.
"""
from pathlib import Path
import sys

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("FEX/FEXCore/Source/Interface/Core/Core.cpp")
source = path.read_text()
start = "  {\n    static uint64_t FfsLastCount = 0;"
end = "  /* iOS-Madeira: refuse to compile obviously-invalid guest RIPs."
if "#ifdef FEX_IOS_HOST\n" + start in source:
    print("FEX telemetry guard already installed")
    raise SystemExit(0)
if source.count(start) != 1 or source.count(end) != 1:
    raise SystemExit("BLOCKED: unexpected pinned FEX Core.cpp layout")
a = source.index(start)
b = source.index(end, a)
block = source[a:b]
if "IosFfsBypassLog" not in block or "IosCbEntryLog" not in block:
    raise SystemExit("BLOCKED: missing expected telemetry identifiers")
source = source[:a] + "#ifdef FEX_IOS_HOST\n" + block + "#endif // FEX_IOS_HOST telemetry\n\n" + source[b:]
path.write_text(source)
print("Guarded both iOS-only FEX telemetry reporters")
