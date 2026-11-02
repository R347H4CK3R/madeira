# StrataForge: verified-on-device development track

**Status:** feasibility and integration track; NOT a working Windows game emulator or verified Strata guest.

## Target
A low-overhead iPhone 16 Plus launcher for Windows x86/x64 games, with a single-process runtime usable as a Strata guest if Strata actually provides the required execution privileges. Operated through OmniForge for project management, source edits, diagnostics, and triggering the authorized build pipeline.

## Preserve upstream translation technology
- FEX x86/x86-64 -> ARM64 dynamic binary translation.
- ARM64EC Wine + WoW64 Windows compatibility, wineserver in-process.
- DXMT Direct3D 9/10/11 -> Metal; D3D12 Metal pipeline where supported.
- Controller touch/XInput layer.
- Do NOT substitute browser-based emulation or VM emulation and claim equivalent compatibility.
- Maintain third-party licensing, notices, and required redistributable dependencies.

## Performance design
1. Lazy-load Wine components; measure startup peak RSS, steady-state RSS, launch time and frame pacing.
2. Per-game graphics presets. Default to modest internal resolution with adjustable render scaling.
3. Bound texture/shader caches and support explicit cache-clear in diagnostics.
4. Use translated-code caching only when compatible with iOS code-signing/JIT constraints.
5. Avoid duplicated game archives and giant bundled redistributables.
6. Controller and touch controls should not compete for focus.

## Mandatory Strata preflight (physical iPhone)
- Verify installed guest's process and app-container identity; Strata's JIT must apply to the actual process executing translated code.
- Verify JIT entitlement/debugger state *at the instant* a translated test function executes.
- Verify sufficient accessible memory; do not mistake an allocated virtual region for actual physical memory entitlement.
- Test Mach-compatible threading and Wine AF_UNIX/socket server startup, client handshake, clean teardown.
- Verify dynamic libraries load in Strata's guest context.
- Verify offscreen Metal drawing and a rendered test triangle.
- Verify controller input and audio playback.
- Save timestamped, redacted crash logs with each failure state.

## Acceptance gates
Gate 0: Clean reproducible build from pinned upstream sources, all needed native dependencies, and verified license notices.
Gate 1: Strata installs the guest package, launches and shows SwiftUI library on iPhone 16 Plus.
Gate 2: JIT check passes on the translating process (not merely Strata's UI); memory limits are measured.
Gate 3: Wine initialization, wineserver handshake and FEX CPU self-test pass in the guest.
Gate 4: Metal/DXMT rendering and gamepad/keyboard input pass.
Gate 5: One lawfully obtained lightweight Windows game starts and renders interactively, with FPS/RSS logs and crash-free exit.
Only after Gate 5 may the release be called a working StrataForge emulator. No assertion of broad Windows game compatibility follows from a single game.

## OmniForge boundaries
Its current installer bridge is restricted to approved package operations. Building this project end-to-end requires a separate opt-in authenticated build job on a configured macOS toolchain, or real native in-app compilation support. Do not promise iOS-on-iOS native LLVM linking where it is absent. Existing GitHub Actions jobs are only considered validated when a successful build, artifact integrity check, and physical-device runtime evidence exist.

## Immediate technical blockers
- The current Madeira fork has clean-checkout native dependency gaps documented in docs/BUILDING.md.
- JIT and Wine socket lifecycle within Strata are not proven.
- A successful IPA package does not prove translated games will execute.

## Verification record
- [ ] Clean compile
- [ ] Strata guest launch
- [ ] Physical device JIT
- [ ] Wine server handshake
- [ ] FEX translated self-test
- [ ] Metal test
- [ ] Controller test
- [ ] Game launch
