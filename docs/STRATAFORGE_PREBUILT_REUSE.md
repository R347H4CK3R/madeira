# Prebuilt upstream runtime reuse audit (2026-11-01)

## Confirmed available
- Official upstream release: https://github.com/willfaust/Madeira/releases/tag/v0.1.3
- Asset: `Madeira-0.1.3.ipa` (~138.8 MiB), accompanied by `Madeira-0.1.3.ipa.sha256`.
- Reuse the official, checksummed IPA as the **reference executable build**, with author and licensing notices intact. Verify checksum before any inspection.
- The app includes the integrated FEX/ARM64EC Wine/DXMT translation stack, but installed iOS app binaries are not independently relinkable native static archives.
- The existing repository checkout already contains Windows-side ARM64EC PE DLL assets and four selected tracked static archives (GMP/Nettle/GnuTLS), but NOT the native FEX, Wine server or DXMT archives required by Xcode.

## Rules
1. Never claim that unzipping the original IPA recreates the missing `libFEXCore.a`, `libwineserver.a`, or `libdxmt_combined.a`; those were linked into the executable at build time.
2. For a baseline Strata compatibility test, verify the original signed IPA's bundle identity, signature and contents; do not strip the executable or advertise an untouched upstream binary as StrataForge.
3. For modified StrataForge SwiftUI/diagnostics source, rebuild all missing native static archives with the pinned iOS build scripts and appropriate Apple SDK/toolchain.
4. The official upstream release notes list iOS 26+ and JIT/Memory+ signing requirements; Strata may handle the guest differently, so physical-device verification is mandatory.
5. Preserve Wine/FEX/DXMT licenses and Steam auth behavior. The official release does not bundle Microsoft's Visual C++ redistributables.
6. In the release workflow, do not require an `Frameworks` directory to prove static native library linking; use compilation/link success plus checks of executable architecture and required resources.

## Fail-safe publication
The existing StrataForge source should remain unchanged until a compiled and tested runtime candidate exists. A baseline official Madeira IPA may be useful for diagnosis, but should not be silently republished as the user's custom app.
