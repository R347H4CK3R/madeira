#!/usr/bin/env python3
"""Keep the pinned FEX CASPAL diagnostic portable across iOS and Windows.

The original Windows VirtualQuery probe cannot compile for Apple arm64.
This overlay changes diagnostics only; CASPAL execution remains untouched.
"""
from pathlib import Path
import sys

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    "FEX/FEXCore/Source/Utils/ArchHelpers/Arm64.cpp")
source = path.read_text()
old = '''  MEMORY_BASIC_INFORMATION mbi {};
  const char* type = "?";
  if (VirtualQuery(reinterpret_cast<LPCVOID>(GPRs[AddressReg]), &mbi, sizeof(mbi))) {
    type = mbi.Type == MEM_IMAGE ? "MEM_IMAGE" : mbi.Type == MEM_MAPPED ? "MEM_MAPPED" : "MEM_PRIVATE";
  }
  LogMan::Msg::EFmt("[caspal128] MISALIGNED-UNSUPPORTED Size={} addrReg=x{} addr={:#x} misalign={} "
                    "crosses16B={} | region base={} size={:#x} prot={:#x} type={} state={:#x}",
                    Size, AddressReg, GPRs[AddressReg], GPRs[AddressReg] & 15,
                    (GPRs[AddressReg] & 15) ? "yes" : "no", mbi.BaseAddress, mbi.RegionSize,
                    mbi.Protect, type, mbi.State);'''
new = '''#if defined(_WIN32)
''' + old + '''
#else
  // Apple/iOS does not expose Windows VirtualQuery/MEMORY_BASIC_INFORMATION.
  // Log the instruction and alignment without inventing region metadata.
  LogMan::Msg::EFmt("[caspal128] MISALIGNED-UNSUPPORTED Size={} addrReg=x{} addr={:#x} misalign={} crosses16B={}",
                    Size, AddressReg, GPRs[AddressReg], GPRs[AddressReg] & 15,
                    (GPRs[AddressReg] & 15) ? "yes" : "no");
#endif'''
if new in source:
    print("FEX CASPAL platform guard already installed")
    raise SystemExit(0)
if source.count(old) != 1:
    raise SystemExit("BLOCKED: unexpected pinned FEX Arm64.cpp CASPAL diagnostic")
path.write_text(source.replace(old, new, 1))
print("Guarded Windows VirtualQuery diagnostic; added portable iOS fallback")
