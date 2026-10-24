# COD HQ test IPA progress — 2026-10-24

Status: BLOCKED BY GITHUB ACTIONS SERVICE REJECTION. No new IPA has been built or validated. COD startup remains untested in a new build.

## Source and preservation

- Fork: R347H4CK3R/madeira. New working branch: fix/cod-1938090-ipa-20261024.
- Base: 4537c7ad9931c5b6d5993346a675e8665aed845a, from fix/cod-1938090-uctrbase-launch-diagnostics.
- Existing cloud checkout was clean. Existing Windows checkouts were inspected without changes. Main and old builds remain intact.
- Pinned FEX: 26859e184ad90f0e811d7f8bbd943a4b1573a2c3; Wine: 4f5b19718f4de88ecc5cb0dc08b119497a67ba8f; DXMT: 35a4db11bd1bda380c5176a3bc6c1878f7192101; Dock: 3cadfbea700e4da4b04e331dd7ef1ba633dfacef.
- Full recursive manifest: diagnostics/cod-ipa-submodules.txt. Recursive initialization succeeds for the pinned base.
- Upstream main at audit: e3a88fddb8daed1f5ac28a45dcb4663d65192629, 524 commits ahead / 1 fork-only commit. Upstream fetch exposed unreachable historical submodule objects (FEX 22337c8d..., Wine 0511f7e7...); this did not change the pinned working tree. No blanket upstream merge.
- FEX/AGENTS.md prohibits AI-generated code contributions. No FEX source modifications are planned.

## Hardware and toolchain compatibility

Observed GamingLaptop differs from the supplied Windows 10 Pro description: Windows 11 Home 10.0.26300, AMD Ryzen 5 6600H (6 cores/12 threads), virtualization enabled and hypervisor active, 16 GB RAM. AMD Radeon driver 32.0.21045.16010. C: approximately 510 GB total / 55 GB free at audit.

Git 2.55 and Python 3.13.15 are installed. Visual Studio Build Tools 2022 17.14.41 supplies MSVC 14.44 and bundled LLVM/CMake/Ninja outside PATH. WSL is not installed; Rust, Docker and gh are not on PATH. Git Credential Manager recognizes the user's GitHub account. The connected GitHub repository reports push/admin permissions. Credentials were used only through the existing broker for GitHub authentication; no credential values were printed or persisted. No security settings or unrelated applications were changed.

The cloud workspace is Debian 13 x86-64, five virtual CPUs, about 17 GiB RAM and 30 GiB free disk initially. Git, Python, GCC/make, Docker CLI and Rust 1.94.0 are available; Swift and Xcode are absent. Native iOS builds must use a macOS/Xcode runner. Windows and Linux checks cannot validate iOS runtime execution.

## Evidence and crash investigation

The actual supplied log is held outside Git (it can contain personal paths). It identifies iPhone17,4, iOS 27.2 build 24B115. The log shows StikJIT/Wine initialization and an attempted Randgrid prerequisite followed by 0xc000001d; the installer failure is not recorded as success.

The original Madeira-0.1.3.ipa is now identified in Drive (145,554,426 bytes), but cannot be materialized through the executor's 32 MiB transfer limit. The Madeira-COD-Debug folder is a source checkout, not an extracted app. Four smaller DLLs retrieved from that folder exactly equal the tracked files.

Binary evidence is now concrete: the Drive ARM64EC ntdll contains the exact logged caller instruction at RVA0x323b0, inside MODULE_InitDLL, calling the indirect-call thunk. The installed COD folder's x64 ucrtbase.dll (version10.0.22000.832, SHA256 a73bd7d75f368ab2fe949dcddbb25cd5d5975ff9091761a01b98f5e26de543ee) matches the logged image size0x111000, entrypoint0x15e30 and all32 logged instruction bytes. This corroborates native execution of the game's x64 CRT during FEX bootstrap, before emulator state exists. The source patch isolates the translator's dependency path to sysx64;system32 and rebuilds the ARM64EC ntdll in CI. It preserves ordinary application path ordering; later bare-name imports normally reuse the native CRT already loaded during bootstrap. Four behavioral cases pass; the unpatched bootstrap cases fail. Full iPhone file identity and device confirmation remain outstanding. See diagnostics/cod-runtime-investigation.md.

Official Activision and Steam sources establish a separate RICOCHET kernel-driver requirement for app1938090. Madeira/Wine does not supply a Windows kernel. Fixing the bootstrap failure does not establish gameplay compatibility; no anti-cheat or prerequisite bypass is implemented. See diagnostics/cod-platform-limitations.md.

The FEX guard-page mprotect message, reduced JIT pool, missing memory entitlements and x18 warnings are not independently established root causes. No memory/security/entitlement bypass is proposed. No anti-cheat, DRM, entitlement or kernel-driver bypass is authorized or implemented.

## Build investigation and implementation

All 66 existing fork Actions runs failed; none published an artifact. Three runs have no jobs (invalid workflow); 63 have failed build jobs. Recent failures occur before Xcode, including missing generated Wine IDL headers. The troubleshooting branch only supplies a presence audit, not a build workflow. The complete failure inventory is diagnostics/cod-ci-audit-2026-10-24.md and diagnostics/cod-ci-failed-runs.json.

Work underway: reconstruct native dependency archives, compile Debug arm64 iOS app on macOS, validate the actual bundle, package Madeira-COD-Fix-Test.ipa, upload build/test logs and real artifacts. Do not substitute empty archives, dummy binaries or a repackaged old IPA.

IPA validation tests pass 23 synthetic fixture cases covering real executable sections/entrypoints, CPU/iOS device platform, PE structure and CHPE metadata, valid Wine prefix registries, required native/EC DLLs, the JIT extension/framework, Metal converter, VC core runtimes, staged-resource hashes, unsafe paths and duplicate entries. Fixtures exercise the validator only; they are never delivered as an IPA. Structural checks do not prove code signing or successful execution.

## Tests and blockers

Baseline: 28/48 host check scripts exit 0 and 20 exit 1. Seventeen fail because Swift is unavailable; steam-library needs Python 3.14 compression.zstd; wma-decoder needs configured Wine headers; swap-coverage has a pre-existing expectation failure (coverage banner not printed at tier start). The pairing Rust suite passes all five tests. Two successful check scripts include optional omissions: Swift/C BOM agreement and a real MP3 fixture. Root, FEX, Wine, DXMT and Dock git fsck checks all pass. The pinned submodule working trees and indices match the gitlinks. Missing Swift and generated Wine headers cause explicit host test failures; these are not reported as passes. No connected iPhone test interface or macOS development computer has been established. No new IPA, checksum or download URL exists yet.

## Commits and current build blocker

- 3f351fe: scoped emulator bootstrap dependency path, behavioral test, full staged build workflow.
- c56c21a: 64-bit host configure, official VC runtime extraction, registered workflow filename.
- 3b05801: strict IPA validation, source-resource hashes, archive architecture checks and actual freshly built crypto inputs.

Supported Actions enable operations both returned HTTP204, but dispatch still returns HTTP422: "Actions has been disabled for this repository." Repository setting enabled=true, workflow active, branch/source readable and token repo/workflow scopes verified. No run exists. This is not a compilation failure. Exact account/service reason remains hidden; no billing cause has been established. Full evidence and GitHub request IDs: diagnostics/cod-actions-rejection.md.

Final local suite: 30/50 check scripts exit0, 20 baseline failures remain (17 Swift absent, Python compression.zstd absent, configured Wine headers absent, swap-coverage expectation mismatch). Pairing Rust tests5/5 pass. New tests: bootstrap4/4 and IPA validator23/23. Shell syntax, converter source hashes and diff checks pass. These do not validate native iOS compilation or device behavior. Machine-readable results: diagnostics/cod-host-results.json.

## Next steps

Finish build recipe and review; run macOS CI; inspect failures and retest; match original IPA's ucrtbase and ntdll against log; implement a regression-tested dispatch correction only if confirmed; validate/package/download real output. Update this record with actual commits, runs, test totals, signing state and hashes.
