# Strata native build audit — November 1, 2026

Inspected PR #2 at `931967f418b47a60805746e802da7e7bcc81d500`.
Dependency-check repair is published at `f112c75c9203b7d0175e799b15c83342cc19eb3b`.
No unsigned IPA was built. This audit is not evidence of Wine execution, JIT activation, or rendering.

## Pinned source availability

`git submodule update --init --recursive` completed with exit 0. All recursive
submodule status lines match their gitlinks. In particular, the old unpublished
fork warning in BUILDING.md is no longer true for these tested pins:

| Module | Commit |
|---|---|
| FEX | 26859e184ad90f0e811d7f8bbd943a4b1573a2c3 |
| Wine | 4f5b19718f4de88ecc5cb0dc08b119497a67ba8f |
| DXMT | 35a4db11bd1bda380c5176a3bc6c1878f7192101 |
| madeira-dock | 3cadfbea700e4da4b04e331dd7ef1ba633dfacef |
| FEX/External/rpmalloc | 812c2b9cf4310ffacf14e6b64066e78ab0c394b5 |

No pins were changed. Tracked FFmpeg 7.1.1, GMP 6.3.0, Nettle 3.10.1,
and GnuTLS 3.8.9 source archives passed their SHA256SUMS. Running
`bash build/madeira-d3d12/deps.sh` verified the tracked converter headers and
iOS dylib without requiring the optional Apple installer.

## Remaining native build prerequisites

| Required input/output | Producer or blocker |
|---|---|
| Full Xcode, iphoneos SDK, Metal Toolchain | Local host is Linux; no connected macOS device was listed. The PR branch has no recorded Actions runs after its update. No native compiler/linker result is available. |
| llvm-mingw 20260421 UCRT macOS universal | Bootstrap downloads the pinned archive and verifies SHA256; actual macOS download/build not executed here. |
| LLVM source 8dfdcc7b7, host llvm-tblgen, iOS generated headers and static libraries | Two-stage LLVM 15.0.7 build; see build/dxmt-ios/README.md. Requires LLVM_TABLEGEN and documented AddLLVM.cmake Darwin/iOS dead-strip adjustment. Empty build directories do not satisfy this. |
| Wine build-macos/include/config.h and generated headers | Configure the pinned Wine host tree and generate its headers; absent from a clean checkout. |
| FEXCore, FEXCore_Base, JemallocLibs, fmt, cephes_128bit, xxhash, softfloat_3e archives under FEX/build-ios | build/fex-ios/build.sh; all seven outputs are now checked explicitly. |
| libavformat.a, libavcodec.a, libswresample.a, libavutil.a; toolchains/ffmpeg-ios/include | build/ffmpeg/build.sh. |
| GnuTLS include prefix | build/gnutls-ios/build.sh; four tracked crypto archives exist, but generated prefix headers are still required by the Wine unix build. |
| libwineserver.a | build/wineserver/build.sh is an archive patcher, not a complete clean server build. It requires obj/libwineserver.a or app/Madeira/libwineserver.a before compiling. Neither exists. |
| libntdll_unix.a and libwin32u_unix.a | Corresponding build/*-unix/build.sh scripts; Wine generated headers and multimedia/crypto prefixes must exist first. FreeType archive is optional in the script; without it fonts are disabled. |
| libdxmt_combined.a | build/dxmt-ios/build.sh builds unix objects and only refreshes an existing combined archive. Clean assembly still requires the documented libtool merge of obj/*.o and LLVM iOS lib/*.a, then staging in app/Madeira. |
| libmadeira_rppairing.a | Rust/cargo with aarch64-apple-ios target; build/rppairing-ios/build.sh uses Cargo.lock. |
| Microsoft x64 VC++ runtime folder | Supply legitimate Microsoft redistributable DLLs under app/Madeira/x86_64-vcruntime; ARM64EC runtime DLLs already tracked do not replace this folder. |
| PE DLL regeneration when changing Wine/FEX/DXMT PE code | llvm-mingw, host Wine tools/generated IDL headers, meson/ninja; use the pinned source rather than newer upstream branches. |

Reproduction of the server prerequisite failure: with **only the SDK lookup
stubbed** to reach the archive guard on Linux, `bash build/wineserver/build.sh`
exits 1 with `ERROR: No base libwineserver.a found`. This is a build-script
preflight reproduction, not an iOS compilation failure. A complete base archive
recipe or an authorized original development archive remains necessary. No
placeholder archives or unrelated replacement submodules were used.

Once prerequisites are satisfied, build Debug (the documented game configuration):

```sh
xcodebuild -project app/Madeira.xcodeproj -scheme Madeira \
  -configuration Debug -destination 'generic/platform=iOS' \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO build
```

Then package the actual built Madeira.app in Payload, inspect its Mach-O arm64
platform, embedded dependencies and Info.plist, and retain complete build logs.
An unsigned build still needs suitable signing when installed through Strata.

## Wine transport and host JIT

WineProcessBridge.m creates a socketpair, injects the server end, and exports the
client end through WINESERVERSOCKET. server_ios.c consumes that variable before
its server_connect fallback. fd_ios.c exchanges the injected descriptor and calls
master_socket_handle_client. The PR's bind-denial socketpair is a separate dummy
master descriptor: it does not itself establish a working client handshake.
Its retained dummy peer and startup/shutdown lifecycle still need device tests.

The guest guard in ContentView and JITBuiltInHost prevents trying to launch a
standalone guest helper under LC_HOME_PATH. Madeira's script uses StikDebug's
get_pid/send_command APIs and BRK #0xf00d dispatch. No Strata host source or
working debugger session was available to prove that Strata supports that script
API, attaches to the correct host PID, keeps servicing BRK, or survives guest
startup. CS_DEBUGGED and a successful static assertion cannot prove these facts.

Physical-device gates: host debugger lifecycle, BRK pool allocation and code-page
requests, Wine init/registry handshake, repeated launch/stop, actual Metal frame
presentation, input, memory pressure, and background/foreground recovery on the
iPhone 16 Plus. Do not merge or publish this as a verified runtime repair yet.

## Repairs and verification

- Bootstrap now rejects failed recursive checkout, reports mismatched/uninitialized
  pins, validates LLVM source revision, and checks real generated/native outputs
  rather than accepting build directories. It also lists missing Rust/meson/objcopy tools.
- CI runs three behavioral bootstrap regression tests and the JIT static contract;
  the macOS probe preserves bootstrap and checkout logs as artifacts.
- The pre-existing JIT static test was updated for the third failure path added
  by PR #2, with a specific check that Strata rejection settles the pending launch.
- Three regression tests, shell syntax, git diff whitespace, PR source assertions,
  converter/source hashes and the updated JIT contract passed locally.
- Full host sweep after recursive checkout: 26 passed, 22 failed. It used
  ASAN_OPTIONS=detect_leaks=0 because LeakSanitizer cannot inspect this sandbox;
  it does not validate leaks. The JIT contract failure was subsequently repaired
  and its complete test passed. The other failures remain listed below.
- Git CLI push lacked credentials; the authorized GitHub connector applied the
  source commit to PR #2 instead. No workflow run was observed, and no macOS
  native compilation or IPA artifact is claimed.

### Full-sweep failures (before the targeted JIT test correction)

- `check-control-presets.py`: FileNotFoundError: [Errno 2] No such file or directory: 'swiftc'
- `check-dock-components.py`: FileNotFoundError: [Errno 2] No such file or directory: '/root/.local/share/swiftly/bin/swiftc'
- `check-dock-contract.py`: FileNotFoundError: [Errno 2] No such file or directory: '/root/.local/share/swiftly/bin/swiftc'
- `check-dock-installers.py`: FileNotFoundError: [Errno 2] No such file or directory: '/root/.local/share/swiftly/bin/swiftc'
- `check-dock-path.py`: FileNotFoundError: [Errno 2] No such file or directory: '/root/.local/share/swiftly/bin/swiftc'
- `check-dock-report.py`: FileNotFoundError: [Errno 2] No such file or directory: '/root/.local/share/swiftly/bin/swiftc'
- `check-dock-start-screen.py`: FileNotFoundError: [Errno 2] No such file or directory: '/root/.local/share/swiftly/bin/swiftc'
- `check-frontend.py`: FileNotFoundError: [Errno 2] No such file or directory: 'swift'
- `check-hardware-input.py`: FileNotFoundError: [Errno 2] No such file or directory: 'swiftc'
- `check-jit-method.py`: AssertionError: every way Enable JIT ends settles the waiting game
- `check-jit-network.py`: FileNotFoundError: [Errno 2] No such file or directory: '/root/.local/share/swiftly/bin/swiftc'
- `check-library-api.py`: FileNotFoundError: [Errno 2] No such file or directory: 'swift'
- `check-onboarding.py`: FileNotFoundError: [Errno 2] No such file or directory: '/root/.local/share/swiftly/bin/swiftc'
- `check-runtime-settings.py`: FileNotFoundError: [Errno 2] No such file or directory: 'swift'
- `check-steam-cloud.py`: FileNotFoundError: [Errno 2] No such file or directory: '/root/.local/share/swiftly/bin/swiftc'
- `check-steam-games.py`: FileNotFoundError: [Errno 2] No such file or directory: '/root/.local/share/swiftly/bin/swiftc'
- `check-steam-library.py`: ModuleNotFoundError: No module named 'compression'
- `check-steam-signin-native.py`: FileNotFoundError: [Errno 2] No such file or directory: '/root/.local/share/swiftly/bin/swiftc'
- `check-swap-coverage.py`:   - coverage line printed at tier start
- `check-touch-gamepad.py`: FileNotFoundError: [Errno 2] No such file or directory: 'swiftc'
- `check-wg-parser.py`: subprocess.CalledProcessError: Command '['tar', '-xJf', '/workspace/scratch/0289be6e96af/madeira/build/ffmpeg/src/ffmpeg-7.1.1.tar.xz', '-C', '/root/.cache/madeira-host-ffmpeg/7.1.1-3c7e993eec95-src']' returned non-zero exit status 2.
- `check-wma-decoder.py`: SKIP-FAIL: /workspace/scratch/0289be6e96af/madeira/wine/build-macos/include/config.h is missing; point MADEIRA_WINE_BUILD at a configured Wine tree
