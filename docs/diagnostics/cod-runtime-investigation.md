# COD HQ runtime investigation — 2026-10-24

Investigation base: Madeira `4537c7ad9931c5b6d5993346a675e8665aed845a`; Wine `4f5b19718f4de88ecc5cb0dc08b119497a67ba8f`; FEX `26859e184ad90f0e811d7f8bbd943a4b1573a2c3`. The supplied log contains 14,469 lines and identifies iPhone17,4 / iOS27.2 build24B115. The exact original IPA has not been supplied to this agent. No FEX or Wine submodule working-tree modifications were made.

## Conclusion from the actual log

The two startup failures execute x86-64 DLL initialization bytes directly as ARM64 before FEX ProcessInit/ThreadInit. This is an architecture/bootstrap dependency-selection failure. The supplied evidence does not establish an unsupported guest instruction, failed JIT authorization, an x18/TEB failure, or an anti-cheat failure as the cause of these two crashes.

The DLL's precise loaded file path is not printed in this log. An application-local x64 ucrtbase winning normal application DLL search while loading FEX is the source-supported explanation; matching the original DLL and full-path logging would complete provenance proof. The correction below isolates that early dependency search without changing ordinary application DLL search.

## Crash evidence

The original log is kept outside Git at:

`/tmp/codex-remote-attachments/01a16c28-bccd-746c-8b52-29b97e130010/03BC5BBF-D599-43F5-BBFD-85DA466D09A4/1-madeira-log.txt`

There are exactly two `Unhandled exception code` lines:

| Process / thread | Evidence | Result |
|---|---|---|
| bootstrapper_installer.exe /0070 | Spawn2923; ucrt mapping3153–3155; fault3517–3529; registers3638–3643; exception3663 |0xc000001d before FEX state exists |
| bootstrapper.exe /010c | Spawn11131; ucrt mapping11219–11221; fault11300–11308; exception11363 | Same entrypoint, same opcode bytes, same phase |

Installer mapping: PE base0x71745f0000, size0x111000, pool base0x14e985000, trampoline budget0. Fault native PC0x14e99ae30 reverse-maps exactly to PE0x7174605e30 =ucrtbase+0x15e30. Bootstrapper repeats the size and offset with different addresses.

The log prints `insn_stream` with first fault word0x245c8948 and subsequent words0x83485708,0x8b4920ec,0x83da8bf8. In little-endian byte order this begins:

`48 89 5c 24 08 57 48 83 ec 20 49 8b f8 8b da 83 ...`

This is an x64 prologue (`mov [rsp+8],rbx; push rdi; sub rsp,0x20; ...`) executing at a native ARM PC. It is not an ARM instruction from the tracked Wine ucrtbase.

Registers identify the initialization call: x0 is the ucrtbase module base, x1=1 (`DLL_PROCESS_ATTACH`), x2=0; LR maps to ntdll+0x323b4, whose previous native instruction is a BL (`0x940019b0`). Exact symbolization of that ntdll offset still requires the original IPA.

x28=0, `State.RIP=0`, `callret_sp=0`, `insim=0`, and termination explicitly prints `no FEX state on this thread`. FEX initialization banners appear for healthy helper processes004c/00a4, but neither failed process reaches the `about to call arm64ec_process_init` line. x18=0 is recorded, but Wine retrieves a valid TEB/PEB and dispatches the exception; the instruction stream itself already proves the architecture error.

The installer exits with signed status-1073741795 and the one-time install is not recorded as successful (line3998). Later, bootstrapper.exe is started with argument `cod.exe`; there is no NtCreateUserProcess spawn of cod.exe in the supplied log. The game executable is not shown executing.

## Source trace and approved correction

Relevant Wine source is `wine/dlls/ntdll/loader.c`:

1. `loader_init` calls `load_arm64ec_module` before fixing the game's own imports (around5712).
2. `load_arm64ec_module` calls `load_dll(NULL,module,...)` (around5338). NULL means the application's default DLL search path.
3. `build_module` passes the same load_path into `fixup_imports` (around2895), which passes it to `import_dll` (around1893), which calls `load_dll(load_path,dependency,...)` (around1414). The search policy therefore propagates through dependencies.
4. `search_dll_file` substitutes `default_load_path` when its paths argument is NULL (around3851). An x64 local CRT is a valid AMD64 file for an ARM64EC loader, so this load succeeds instead of taking the existing sysx64 mixed-architecture fallback.
5. `alloc_module` redirects a DLL entrypoint only when it has ARM64EC metadata (around1968). A pure x64 CRT keeps its x64 entrypoint.
6. The early ARM64EC checker simply passes a call through before initialization (`signal_arm64ec.c:4766`); the full checker is installed only after FEX ProcessInit/ThreadInit (around907). Calling this x64 DllMain during FEX dependency attachment therefore runs its bytes natively.

`system_dll_path` is no existing remedy: it is read after load_arm64ec_module, and iOS compiles `SYSTEMDLLPATH=""` (`build/ntdll-unix/build.sh:35`), so the environment builder normally produces no WINESYSTEMDLLPATH at all. Merely moving the environment-variable read earlier would not fix this configuration.

The approved top-level patch is:

`/workspace/madeira/build/patches/wine-arm64ec-bootstrap-path.patch`

It passes explicit `C:\windows\sysx64;C:\windows\system32` dependency search only while loading the translator. The sysx64 ARM64EC farm is confirmed by log202 (145 links); system32 supports a native ARM64EC session and supplies the existing absolute xtajit64 module path. An `[ec-bootstrap] native dependency search=...` marker identifies the actual policy in subsequent logs. It does not alter FEX code, skip prerequisites, or mark failed installers successful. Ordinary application path ordering remains unchanged, but later bare-name imports of ucrtbase normally reuse the already-loaded native CRT, as Wine's basename lookup does before searching files.

The root agent is integrating patch application into the build. This investigation agent leaves the pinned Wine working tree untouched, so building without applying this patch will not include the correction.

## Verification and limits

`tests/host/check-arm64ec-bootstrap.py` compiles the pinned production `load_arm64ec_module` and `search_dll_file` C functions with host NT file/registry/init shims. Fixtures distinguish an application-local x64 CRT from native CRTs in the two system directories. The mapper boundary passes the bootstrap path to production search; it does not emulate the entire Wine dependency graph, PE loader, FEX, or iOS.

Observed RED: `python3 tests/host/check-arm64ec-bootstrap.py --unpatched` exits1, failing three bootstrap cases while ordinary application search still passes.

Observed GREEN: `python3 tests/host/check-arm64ec-bootstrap.py` applies the patch in a temporary source copy, compiles the actual functions, and passes four cases:

- Native sysx64 CRT wins over an application-local x64 CRT during bootstrap.
- Native system32 CRT works when the sysx64 farm is absent.
- Missing native CRT fails before attach rather than selecting local x64 CRT.
- Ordinary application search keeps its local-first path order when resolving an unloaded DLL. This isolated search case does not bypass Wine's normal reuse of loaded modules.

`git -C wine apply --check ../build/patches/wine-arm64ec-bootstrap-path.patch` passes. Python compilation passes. `git -C wine status --short` and `git -C FEX status --short` were empty. Parent work is responsible for the complete host suite, actual PE rebuild, IPA validation, and device run.

This establishes a source-level correction with a regression test. It does not establish that a new IPA has built or that COD reaches gameplay. The supplied ucrtbase is distinct from the tracked Wine DLL, and the original IPA/DLL still needs identification.

## Secondary findings, not this crash's cause

The log has23 `Failed to mprotect last page of code buffer` warnings in functioning FEX/Steam processes. FEX's Windows allocator wrapper (`FEX/FEXCore/include/FEXCore/Utils/AllocatorHooks.h:214`) returns `::VirtualProtect(...) == 0`, inverting Win32 BOOL success. CodeBuffer checks `if (!VirtualProtect(...))` and logs that warning on a successful API return. iOS's NtProtect implementation explicitly substitutes an old-protection sink when the pointer is NULL (`build/ntdll-unix/virtual_ios.c:22714`), so NULL alone does not establish failure here. Do not conclude OOM or broken executable mapping from that warning. FEX/AGENTS.md forbids AI-generated code contributions; this wrapper is documented only, not edited.

FEX's iOS ARM64EC CPU feature detection hardcodes several feature flags true while host-probe overrides are currently limited to WOW64 (`FEX/Source/Windows/Common/CPUFeatures.cpp:61–120`). That is an independent portability concern for older cores. It is not implicated by the present native x64-byte crash on iPhone17,4.

The tracked ARM64EC ucrtbase SHA256 is `f43f7110434978853c83ba4d66a6d8d718b8ecd544eae2b4063767675eb83e59`, SizeOfImage0x130000. Its +0x15e30 lies in ARM64EC CodeMap type1 and contains ordinary ARM64 bytes. The tracked aarch64 copy hash is `949cfaec85a74275a4b5bcc40ca687b2343385c4cdcae5b91ef01fe190c79aa9`. Neither may be used to name the faulting x64 function in the user's different0x111000 module.

## Driver limitation and next device evidence

The Randgrid installer was invoked with `atvi-randgrid_sr true Randgrid.sys`, but dies before it can establish whether driver/service operations work. Wine's upstream NtLoadDriver is a STATUS_NOT_IMPLEMENTED stub (`wine/dlls/ntdll/unix/system.c:4697`); Wine's service manager also has a user-space winedevice path for some kernel-driver services (`wine/programs/services/services.c:964`). Neither implements an actual Windows kernel or guarantees a proprietary kernel anti-cheat driver. Successful CRT/bootstrap startup would not establish Randgrid/gameplay compatibility. The present log does not prove the eventual driver failure, and no bypass is proposed.

Required next evidence is a build containing the path patch, its `[ec-bootstrap]` markers, the resolved ucrtbase file/type, successful ProcessInit/ThreadInit for both formerly failing children, the prerequisite's true exit code, and whether a cod.exe process is subsequently created. Preserve any genuine later driver failure as its own limitation. Exact offset symbolization additionally requires the failing IPA's ntdll and the actual native-x64 CRT file used by the game.
