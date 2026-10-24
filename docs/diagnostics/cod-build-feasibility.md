# Madeira Debug arm64 iOS build feasibility

Audited base: `4537c7ad9931c5b6d5993346a675e8665aed845a` in `/workspace/madeira`.
This was a read-only input audit followed by the parent-authorized CI recipe
implementation. No Apple build has run in this Linux environment. A prepared
recipe is not evidence that its final app links or runs on a device.

## Finding

The current source can supply the actual native runtime build, but a plain
`xcodebuild` from the original checkout cannot: it is missing 16 required static
archives, configured Wine headers, LLVM iOS headers/libraries and Microsoft x64
runtime resources. There is no need to fabricate an archive or disable D3D12.
The Apple converter iOS library/public headers and StikJIT framework are already
tracked. Their proprietary installer is not a necessary input to this app build.
Whether the available hosted Xcode can import the tracked Swift 6.4 framework is
still a real build question.

The documentation's old claim that submodule commits are local-only is stale for
this session: recursive submodules exist and the parent independently checked
current remote reachability. Do not alter the pinned gitlinks.

## Required linked static archives

The definitive link list is `app/Madeira.xcodeproj/project.pbxproj`'s
`PBXFrameworksBuildPhase` (lines 317 onward).

| Required input | Original clean checkout | Real source/build producer |
|---|---|---|
| `FEX/build-ios/FEXCore/Source/libFEXCore.a` | missing/ignored | FEX CMake target FEXCore |
| `FEX/build-ios/FEXCore/Source/libFEXCore_Base.a` | missing/ignored | FEX CMake target FEXCore_Base |
| `FEX/build-ios/FEXCore/Source/libJemallocLibs.a` | missing/ignored | FEX CMake target JemallocLibs; Apple disables Linux allocators |
| `FEX/build-ios/External/fmt/libfmt.a` | missing | FEX dependency graph |
| `FEX/build-ios/External/cephes/libcephes_128bit.a` | missing | FEX dependency graph |
| `FEX/build-ios/External/xxhash/cmake_unofficial/libxxhash.a` | missing | FEX dependency graph |
| `FEX/build-ios/External/SoftFloat-3e/libsoftfloat_3e.a` | missing | FEX dependency graph |
| `app/Madeira/libntdll_unix.a` | missing/ignored | build/ntdll-unix/build.sh |
| `app/Madeira/libwineserver.a` | missing/ignored | full base bootstrap then build/wineserver/build.sh |
| `app/Madeira/libwin32u_unix.a` | missing/ignored | build/win32u-unix/build.sh with real FreeType |
| `app/Madeira/libdxmt_combined.a` | missing/ignored | DXMT iOS objects + actual LLVM iOS archives using Apple libtool |
| `app/Madeira/libmadeira_rppairing.a` | missing/ignored | locked Rust iOS staticlib |
| `app/Madeira/libavformat.a` | missing/ignored | tracked FFmpeg 7.1.1 tarball |
| `app/Madeira/libavcodec.a` | missing/ignored | tracked FFmpeg 7.1.1 tarball |
| `app/Madeira/libswresample.a` | missing/ignored | tracked FFmpeg 7.1.1 tarball |
| `app/Madeira/libavutil.a` | missing/ignored | tracked FFmpeg 7.1.1 tarball |
| `app/Madeira/lib{gnutls,hogweed,nettle,gmp}.a` | tracked | Four authentic existing iOS archives. Prefix headers/libs still must be rebuilt for Wine compilation. |

`app/libdxmt_unix.a` is tracked but is not the project-linked combined archive.
It cannot substitute for LLVM or the current native graphics implementation.
Apple system frameworks/tbds are SDK inputs, not absent project binaries.

## Source-supported build recipe

The new implementation is `build/ci/build-ios.sh`, invoked in stages by
`.github/workflows/cod-test-ipa.yml`. It preserves `Debug`, `iphoneos`, arm64 and
the tracked PE farms, except ntdll which is deliberately rebuilt with the
parent's external Wine bootstrap-path patch. It records exact source/SDK hashes
and does not claim a developer-signed result.

1. Install ordinary host tools: CMake, Ninja, pkg-config, Bison 3+, ccache,
   FreeType host dependency for configure, LLVM's llvm-objcopy, sevenzip. Rust
   needs `aarch64-apple-ios`; Cargo.toml edition 2024 needs a recent toolchain.
2. Fetch llvm-mingw `20260421-ucrt-macos-universal` at the documented URL and
   SHA256 `bd85a3975723815cef28dbbd2ca2cb0c926f6b348a12a0453f39f7af273cb3f7`.
3. Clone FreeType tag `VER-2-13-3` into `research/freetype`; record resolved SHA.
   Run the real GnuTLS/FFmpeg/FreeType iOS build scripts. The first two sources
   are tracked release tarballs. GnuTLS's script produces a prefix, not copied
   app archives; this is sufficient because its four matching app libs exist.
4. Configure Wine host tree with `--enable-win64 --without-x --disable-tests
   --enable-winegstreamer`. The win64 flag is essential on Intel macos-15:
   Wine configure.ac 111–121 otherwise selects `-m32`, unsupported by modern
   macOS. Run `make -C wine/build-macos -jN include/all`.
5. Configure the ARM64EC tree with `--enable-archs=arm64ec --without-x
   --disable-tests --enable-winegstreamer`; run its `include/all` as well.
   The source-supported aggregate target solves the complete transitive IDL
   closure: `wine/tools/makedep.c` generates IDL headers and includes them in
   each directory's `all` target. Prior `make include` was a no-op against an
   existing directory; guessing dwrite/wtypes/etc. omitted `docobj.h`.
6. Build ntdll unix side. It needs host config.h, flat native generated headers,
   ARM64EC dwrite headers (build script lines 108–112), FreeType include tree,
   GnuTLS prefix headers/libraries and FFmpeg prefix headers. No GStreamer
   installation is needed: Madeira supplies the FFmpeg/Apple backend.
7. Bootstrap the complete wineserver archive from `wine/server/Makefile.in`
   sources with the exact existing iOS/shim flags, then run the patcher script.
   Original `build/wineserver/build.sh` lines 15–23 only patch an existing
   archive and fail if neither ignored base/app archive is present. The helper
   `build/wineserver/bootstrap-base.sh` is recovered from a historical CI run
   that passed this stage, not a stub.
8. Build win32u unix side and merge actual `libfreetype.a`. Its generated-header
   closure is supplied by `include/all` rather than a manual list.
9. Rebuild ARM64EC ntdll using `build/wine-pe/build-ntdll.sh`; preserve its
   strip/pad-to-SizeOfImage+0x50000 logic. The parent's Wine-relative patch is
   applied explicitly and archived as build provenance; gitlinks remain pinned.
10. Configure FEX for iOS arm64 with explicit `CMAKE_SYSTEM_PROCESSOR=arm64`
    and `CMAKE_OSX_ARCHITECTURES=arm64`, no test/thunk/config builds. Build its
    three main targets plus dependencies. No FEX source is edited, respecting
    `FEX/AGENTS.md`'s prohibition on AI-generated contributions.
11. Run `build/rppairing-ios/build.sh`: locked release Cargo iOS target plus
    generated crate notices. Correct output is `libmadeira_rppairing.a`, not
    the old workflow's incorrectly cached `librppairing.a`.
12. LLVM 15.0.7: source pinned by required commit prefix `8dfdcc7b7`, fetch the
    release tag shallowly, verify the resolved commit. Build macOS host
    `llvm-tblgen` first with Release, no backend targets/projects/tests/zlib.
    Build iOS arm64 archives with system iOS, deployment17.0, host/default
    triples arm64-apple-ios17.0, `LLVM_TABLEGEN=<host binary>`, no tools/utils/
    tests/targets/projects/zlib/zstd. `AddLLVM.cmake` must recognize `Darwin|iOS`
    for dead stripping. This is a tracked documented build adaptation in
    `build/dxmt-ios/README.md` lines 35–43, not a guessed compiler patch.
13. Ensure MetalToolchain is actually present; download the Xcode component
    only if `xcrun --sdk macosx metal --version` fails. Build full DXMT native
    code, D3D9 and the D3D12 shader conversion service. Do not set
    `MADEIRA_ALLOW_NO_D3D12=1`. After object compilation, explicitly create
    `libdxmt_combined.a` from all current DXMT objects plus the real LLVM iOS
    archives. The original script only refreshes an existing combined archive,
    so its ordinary success alone cannot make a clean checkout link.
14. Build MadeiraDock with the pinned x64 llvm-mingw; stage actual dockhost.exe
    and notices. These are intentionally ignored build products. Merely having
    the submodule directory is insufficient.
15. Supply unmodified Microsoft x64 runtime DLLs. New CI tries the official
    Microsoft redist and recursively extracts CAB/MSI payloads with sevenzip;
    private archive URL can supply a previously obtained licensed input.
    Signed x64 PE/certificate structure is checked and input hashes recorded.
    Require current core `msvcp140.dll`, `vcruntime140.dll`, `vcruntime140_1.dll`;
    retain all expected runtime names available. Current redist may lack the
    deprecated VCAMP/VCCORLIB components. Parent has separately found all12 on
    the user's licensed Windows machine if extraction fails.
16. Stage real GPL/exception license copies, then Xcode build Debug generic iOS
    arm64 with code signing disabled. Package only its resulting Madeira.app
    into Payload/Madeira.app. Validate structure, Mach-O platform/architecture,
    required runtime resources; record lipo/otool/codesign diagnostics/hash.

## Proprietary input and toolchain limits

- `app/Madeira/d3d12/libmetalirconverter.dylib` and its Apache-2.0 public headers
  are tracked. `bash build/madeira-d3d12/deps.sh` verified their pinned hashes
  successfully in this audit. The Apple installer is absent, but only needed
  to refresh/re-extract the converter or compile separate macOS host tools.
  `deps.sh` succeeds with `MSC_HAVE_PKG=0`; it does not block the app pipeline.
  Redistribution remains governed by Apple's included agreement/NOTICE.
- The StikJIT xcframework/device slice, Swift interfaces and license notices
  are tracked. It is MPL-2.0, not an unavailable proprietary SDK. Its interface
  declares Apple Swift 6.4 / clang2100, whereas historical CI chose Xcode26.3.
  Highest installed Xcode is selected and real import compatibility must be
  observed. The iOS helper deployment target is26.0 while the app is17.0.
- Genuine Microsoft DLLs are absent from the repo and governed by Microsoft's
  terms. The similarly named DLLs in the tracked Wine farms are x64 Wine-built
  DLLs without Authenticode certificates; they must not be mislabeled as
  unmodified Microsoft binaries. Cloud policy blocks Microsoft's redirected
  download host here; the ordinary GitHub macOS runner is a separate network.
  No bypass or fake runtime is appropriate. Public extraction is unverified
  until the actual runner reaches it.
- No `MoltenVK` archive/framework appears in the Xcode linker list or these
  native build scripts. Research/MoltenVK is ignored reference material.
  This build uses native DXMT Metal and Madeira D3D12; adding MoltenVK is not
  a source-supported prerequisite. FAudio is part of the Wine guest/media
  context, not an additional standalone app-link archive in this project.
- No Apple ID/signing identity is required to compile the unsigned test app.
  Installation/JIT/device testing remains separate and needs compatible
  signing plus the project's documented runtime setup.

## Verification available now

- Original tracked converter headers/library hashes: PASS via deps.sh.
- New shell scripts: `bash -n` PASS.
- Workflow: YAML parsed with the expected host/build jobs before parent edits.
- VC runtime parser: hand-generated structure checks accepted an intact
  signed-x64-shaped input, rejected truncated certificate/missing core inputs,
  and decoded OriginalFilename. This does not test real redist extraction.
- `git diff --check`: PASS for the current changes.
- Full Apple compiler/linker/build, Microsoft redist extraction, Swift6.4
  import and device launch: pending real macOS/device execution. Parent owns
  run monitoring and the final evidence/claims.
