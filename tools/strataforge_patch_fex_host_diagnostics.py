#!/usr/bin/env python3
"""Keep Madeira iOS-only callback diagnostics out of non-iOS FEX compilation.

The pinned upstream FEX source currently uses these counters in CompileBlock
unconditionally, although their declarations are guarded by FEX_IOS_HOST.
Apply only when both unique anchors are present, and fail closed if changed.
"""
from pathlib import Path
import sys
path = Path(sys.argv[1] if len(sys.argv) > 1 else "FEX/FEXCore/Source/Interface/Core/Core.cpp")
data = path.read_text()
start = "  {\n    static uint64_t FfsLastCount = 0;"
end = "  /* iOS-Madeira: refuse to compile obviously-invalid guest RIPs."
if data.count(start) != 1 or data.count(end) != 1:
    raise SystemExit("FEX diagnostics anchors changed; refusing unsafe patch")
section = data[data.index(start):data.index(end)]
if "IosCbEntryLog" not in section or "IosFfsBypassLog" not in section:
    raise SystemExit("FEX diagnostics content changed; refusing patch")
data = data.replace(start, "#ifdef FEX_IOS_HOST\n" + start, 1)
data = data.replace(end, "#endif // FEX_IOS_HOST callback counters\n\n" + end, 1)
# The upstream CASPAL debug reporter uses Windows VirtualQuery unconditionally.
# Preserve its Windows path; use bounded generic diagnostics on iOS.
cas_start = '  MEMORY_BASIC_INFORMATION mbi {};'
cas_end = '\n}'
arm_path = Path('FEX/FEXCore/Source/Utils/ArchHelpers/Arm64.cpp')
arm_data = arm_path.read_text()
if arm_data.count(cas_start) != 1:
    raise SystemExit("FEX CASPAL diagnostic anchor changed")
i = arm_data.index(cas_start)
j = arm_data.index(cas_end, i)
original = arm_data[i:j]
if "VirtualQuery" not in original or "mbi.State" not in original:
    raise SystemExit("Unexpected FEX CASPAL diagnostic implementation")
fallback = ('#if defined(_WIN32)\n' + original +
            '\n#else\n'
            '  LogMan::Msg::EFmt("[caspal128] size={} addrReg=x{} addr={:#x} misalign={}", '
            'Size, AddressReg, GPRs[AddressReg], GPRs[AddressReg] & 15);\n'
            '#endif')
arm_data = arm_data[:i] + fallback + arm_data[j:]
arm_path.write_text(arm_data)
path.write_text(data)
print("Guarded iOS-only callback counters in native FEX compilation")
