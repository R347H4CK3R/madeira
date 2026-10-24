# Madeira CI audit — 2026-10-24

Read-only audit of `R347H4CK3R/madeira`, including `fix/cod-1938090-uctrbase-launch-diagnostics`, compared with `willfaust/Madeira`. No workflows were rerun and no remote files were changed by this audit.

## Result

The fork has **66 Actions runs, all failed**: 22 COD workflow runs and 44 CSNZ workflow runs. There are 63 failed build jobs and 3 workflows with invalid YAML and no job. Repository-wide enumeration used `actions/runs?per_page=100&page=1`; page 2 was empty with total_count 66. All attempts are 1. Every failed build job's steps and decoded log were fetched. There are no runs for the target diagnostics branch. Every one of the 66 run artifact listings is currently empty; no downloadable IPA exists in these runs. CSNZ diagnostics uploads used 14-day retention and are now beyond that window.

The target diagnostics branch has only `.github/workflows/cod-launch-preflight.yml`. It runs on `macos-15`, recursively checks out submodules, audits 10 required paths and prints Xcode version. It **does not compile, package or upload an IPA**. It explicitly says that input presence is not a compiled or device-verified IPA. The upstream main `.github/workflows` directory returned 404.

## Permissions and execution route

Authenticated login is `R347H4CK3R`. Fork repository metadata reports admin/maintain/push/pull/triage true. Upstream reports pull true, push/admin false. These metadata do not independently prove the connector's Actions mutation scope. Connected tools expose file/git commits and rerun endpoints, but no workflow-dispatch endpoint; the generic fetch tool is GET-only. A new workflow with a push trigger on the authorized fork branch can run a new commit. A valid authenticated gh token on the connected laptop is another dispatch route (root coordinates).

## Unique failure classes and current resolution evidence

| Failure | Historical evidence | Resolution status |
|---|---|---|
| Invalid YAML containing literal `\\n` | 3 runs with no job; fetched workflow revisions fail PyYAML parsing at lines 20, 67, 69 | Correct syntax known; must validate new workflow before push |
| Literal `\\n` in shell `export` | COD 37558081309: invalid identifiers `-v`, compiler names suffixed `n` | Actual multiline shell fixes later COD runs |
| Rust target typo | CSNZ 37166910320/37166765716/37166596094: `aarch64-apple-iosn` | Correct `aarch64-apple-ios` later passed |
| Old bison | COD/CSNZ configure demand bison >=3 | Homebrew bison path addition later passed |
| Missing PE cross compiler | Wine configure cannot find clang/llvm-dlltool/lld for aarch64 | Pinned llvm-mingw download and PATH later passed |
| GitHub release API rate limit | COD 37557810548 HTTP403 during unauthenticated gh download | Direct release URL with SHA256 later passed |
| Unbuilt WIDL tool | COD 37565989341 missing tools/widl/widl; 37566608964 `make tools/widl` no-op | `make tools/widl/widl` later passed |
| Wrong generated header target/location | `make include` no-op; nonexistent `include/wine/windows/wtypes.h`; flattened symlink assertions; latest COD wtypes.h/dwrite.h missing | **Pending CI verification:** generate complete flat native header set with `make -C wine/build-macos include/all` |
| Missing iOS crypto/media dependency prefixes | Early COD native object failures; later prefix stage passed | gnutls/ffmpeg build scripts later passed |
| iOS SDK telemetry field removed | COD 37559932757: rusage_info_v6 lacks ri_page_wait_time_mach | Remove/replace obsolete telemetry access; later runs pass server object |
| Missing iOS FreeType headers | `ft2build.h` absent in dwrite or win32u | Clone FreeType VER-2-13-3 and run build/freetype-ios; later CSNZ freetype object passed |
| Wineserver assumes existing base archive | CSNZ 37174165350 missing base; 37174528801 bootstrap helper missing | Complete historical bootstrap script was added and wineserver passed in later CSNZ |
| Incomplete transitive COM header set for win32u | CSNZ propidl -> oaidl -> oleidl -> exdisp -> docobj successive failures | **Pending CI verification:** complete `include/all` generation, not an explicit short list |
| Unreached native stages | No run reached FEX, pairing, LLVM iOS, DXMT, xcodebuild, packaging | **Unverified in CI:** full workflow must execute these and retain build/validation artifacts |

### Source-supported native header correction

At the pinned Wine tree, `tools/makedep.c:2000` generates every regular include IDL's header, `output_source_h` at line 2987 adds generated headers to `all_targets`, and lines 4270–4276 emit the per-directory `include/all` phony target. Thus `make -C wine/build-macos -jN include/all` generates the full flat native header set, including docobj.h. `make include` names the existing directory and does nothing. Manually placing headers under `include/wine/windows` does not satisfy native build scripts expecting `wine/build-macos/include`.

## Historical build backbone and IPA requirements

The latest CSNZ workflow was saved as `/workspace/ci-history-csnz.yml`, latest COD as `/workspace/ci-history-cod.yml`, and a full wineserver bootstrap that passed that stage as `/workspace/ci-history-wineserver-bootstrap.sh`. They are historical reference, not proof of a working end-to-end build.

CSNZ uses macos-15, Xcode 26.3, Debug, iphoneos, deployment target17 for C/C++ dependencies. It downloads pinned llvm-mingw 20260421 with SHA256 `bd85a3975723815cef28dbbd2ca2cb0c926f6b348a12a0453f39f7af273cb3f7`. Complete build order: headers + toolchains, crypto/media + FreeType, Wine native libraries and PE ntdll, FEX native and ARM64EC, Rust pairing, LLVM host tablegen + iOS libraries, DXMT combined static archive, runtime/resource staging and licenses, then generic-platform iOS Debug xcodebuild without signing, IPA packaging, structural validation, SHA256 and artifact upload. Existing tracked PE farms must be audited against required runtime resources. A base release IPA or old static archive cannot stand in for fresh modified code.

LLVM recipe is pinned source `8dfdcc7b7`, host llvm-tblgen first, then iOS CMAKE_SYSTEM_NAME=iOS / arm64 / iphoneos, target triple arm64-apple-ios17.0, empty LLVM targets/projects, tools/utils/tests/zlib off. Historical workflow changes AddLLVM Darwin match to Darwin|iOS. Native FEX/LLVM/DXMT stages remain CI-unverified.

`docs/BUILDING.md` itself labels clean-checkout steps unverified. It records missing inputs: llvm-mingw, LLVM iOS/host toolchains and optional Microsoft VC runtime DLLs. Project resource directory x86_64-vcruntime must exist even when no redistributable DLLs are supplied. The existing historical preflight treating generated products as prerequisites cannot create them.

## Every failed run

All rows below have conclusion `failure`, attempt1 and zero current artifacts. COD means branch `cod-store-emulator-fix`; CSNZ means branch `csnz-smc-diag-clean`.

| Run | Branch | SHA | Failed step | Log root cause |
|---|---|---|---|---|
| [37568055319](https://github.com/R347H4CK3R/madeira/actions/runs/37568055319) | COD | `e3ea2dcb5d18` | Build iOS ntdll unix library | 'wtypes.h' file not found; 'dwrite.h' file not found |
| [37567269834](https://github.com/R347H4CK3R/madeira/actions/runs/37567269834) | COD | `6c5edba22db0` | Build iOS ntdll unix library | 'wtypes.h' file not found; 'dwrite.h' file not found |
| [37566608964](https://github.com/R347H4CK3R/madeira/actions/runs/37566608964) | COD | `2d2bccd9229f` | Configure Wine ARM64EC headers | make tools/widl was a no-op directory target; WIDL executable assertion failed. |
| [37565989341](https://github.com/R347H4CK3R/madeira/actions/runs/37565989341) | COD | `c72a6e5b3376` | Configure Wine ARM64EC headers | WIDL executable not built before direct invocation. |
| [37565232722](https://github.com/R347H4CK3R/madeira/actions/runs/37565232722) | COD | `8f890bfc383b` | Build iOS ntdll unix library | 'wtypes.h' file not found; 'dwrite.h' file not found |
| [37564561769](https://github.com/R347H4CK3R/madeira/actions/runs/37564561769) | COD | `0ef52bed5ec4` | Configure Wine ARM64EC headers | Requested nonexistent generated target include/wine/windows/wtypes.h. |
| [37562770672](https://github.com/R347H4CK3R/madeira/actions/runs/37562770672) | COD | `66b227a90701` | Build iOS ntdll unix library | 'wtypes.h' file not found; 'dwrite.h' file not found |
| [37562063514](https://github.com/R347H4CK3R/madeira/actions/runs/37562063514) | COD | `b30dbe864d4f` | Build iOS ntdll unix library | 'wtypes.h' file not found; 'dwrite.h' file not found |
| [37562052780](https://github.com/R347H4CK3R/madeira/actions/runs/37562052780) | COD | `24f66cddc663` | Configure Wine ARM64EC headers | make include no-op; asserted generated wtypes.h absent. |
| [37560936922](https://github.com/R347H4CK3R/madeira/actions/runs/37560936922) | COD | `3094d7880d1b` | Configure Wine ARM64EC headers | make include no-op; asserted generated wtypes.h absent. |
| [37560905935](https://github.com/R347H4CK3R/madeira/actions/runs/37560905935) | COD | `e9dc1246cb8e` | Build iOS ntdll unix library | 'wtypes.h' file not found; 'dwrite.h' file not found |
| [37560787692](https://github.com/R347H4CK3R/madeira/actions/runs/37560787692) | COD | `12ae2ed44b9a` | Build iOS ntdll unix library | 'wtypes.h' file not found; 'ft2build.h' file not found |
| [37559932757](https://github.com/R347H4CK3R/madeira/actions/runs/37559932757) | COD | `0efa4d3ca43d` | Build iOS ntdll unix library | iOS SDK rusage_info_v6 missing ri_page_wait_time_mach; also missing generated Wine/FreeType headers. |
| [37558720571](https://github.com/R347H4CK3R/madeira/actions/runs/37558720571) | COD | `3a654fd3fdec` | Build iOS ntdll unix library | Failed: dwrite_unixlib winegstreamer_unixlib server; compiler .err details not printed (artifacts now absent). |
| [37558391122](https://github.com/R347H4CK3R/madeira/actions/runs/37558391122) | COD | `29eb97c93629` | Build iOS ntdll unix library | Failed: bcrypt_unixlib secur32_unixlib dwrite_unixlib crypt32_unixlib winegstreamer_unixlib server; compiler .err details not printed (artifacts now absent). |
| [37558081309](https://github.com/R347H4CK3R/madeira/actions/runs/37558081309) | COD | `80060e0eef8a` | Configure Wine host tree | Literal \\n embedded in shell export block. |
| [37557810548](https://github.com/R347H4CK3R/madeira/actions/runs/37557810548) | COD | `8febfad06d92` | Install pinned Madeira llvm-mingw | Unauthenticated gh release download hit GitHub API rate limit. |
| [37557797333](https://github.com/R347H4CK3R/madeira/actions/runs/37557797333) | COD | `bca8a13a34e2` | Configure Wine host tree | aarch64 PE cross compiler not available to Wine configure. |
| [37557388562](https://github.com/R347H4CK3R/madeira/actions/runs/37557388562) | COD | `cc82fc3385ac` | Configure Wine host tree | aarch64 PE cross compiler not available to Wine configure. |
| [37553979600](https://github.com/R347H4CK3R/madeira/actions/runs/37553979600) | COD | `559dad9d63e1` | Configure Wine host tree | aarch64 PE cross compiler not available to Wine configure. |
| [37548576553](https://github.com/R347H4CK3R/madeira/actions/runs/37548576553) | COD | `00fd4c191f65` | Workflow rejected; no job | Invalid YAML: literal \\n embedded in run/name block (locally reproduced parser failure). |
| [37548024648](https://github.com/R347H4CK3R/madeira/actions/runs/37548024648) | COD | `388c1582d9ed` | Configure Wine host tree | Apple/system bison too old; Homebrew bison not first in PATH. |
| [37177659866](https://github.com/R347H4CK3R/madeira/actions/runs/37177659866) | CSNZ | `75ff64dfbd9c` | Build win32u | 'docobj.h' file not found |
| [37177214978](https://github.com/R347H4CK3R/madeira/actions/runs/37177214978) | CSNZ | `444fabc11319` | Build Wine support libraries | 'exdisp.h' file not found |
| [37176954632](https://github.com/R347H4CK3R/madeira/actions/runs/37176954632) | CSNZ | `a215a9b72954` | Configure Wine generated headers | make include was a no-op; generated-header/flattened-symlink assertions failed. |
| [37176524496](https://github.com/R347H4CK3R/madeira/actions/runs/37176524496) | CSNZ | `aab7a481575a` | Build Wine support libraries | 'oleidl.h' file not found |
| [37175979685](https://github.com/R347H4CK3R/madeira/actions/runs/37175979685) | CSNZ | `eec6424c79a4` | Build Wine support libraries | 'oaidl.h' file not found |
| [37175537261](https://github.com/R347H4CK3R/madeira/actions/runs/37175537261) | CSNZ | `e222e15410c3` | Build Wine support libraries | 'propidl.h' file not found; 'ft2build.h' file not found |
| [37175532897](https://github.com/R347H4CK3R/madeira/actions/runs/37175532897) | CSNZ | `25beed95c03f` | Build Wine support libraries | 'propidl.h' file not found; 'ft2build.h' file not found |
| [37174534601](https://github.com/R347H4CK3R/madeira/actions/runs/37174534601) | CSNZ | `51ecf8facd3d` | Build Wine support libraries | Failed: class clipboard cursoricon d3dkmt dce defwnd driver freetype hook imm input menu message opengl palette rawinput region scroll spy syscall sysparams systray vulkan window winstation; compiler .err details not printed (artifacts now absent). |
| [37174528801](https://github.com/R347H4CK3R/madeira/actions/runs/37174528801) | CSNZ | `ecf86ed82aef` | Build Wine support libraries | Workflow called bootstrap-base.sh before script was added. |
| [37174165350](https://github.com/R347H4CK3R/madeira/actions/runs/37174165350) | CSNZ | `ce74ce2e2853` | Build Wine support libraries | wineserver patch build requires an existing untracked base archive. |
| [37174159191](https://github.com/R347H4CK3R/madeira/actions/runs/37174159191) | CSNZ | `4d342aa88e13` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37173104356](https://github.com/R347H4CK3R/madeira/actions/runs/37173104356) | CSNZ | `ae741c36e1f0` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37172426563](https://github.com/R347H4CK3R/madeira/actions/runs/37172426563) | CSNZ | `f322e470361e` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37172424556](https://github.com/R347H4CK3R/madeira/actions/runs/37172424556) | CSNZ | `f322e470361e` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37171941997](https://github.com/R347H4CK3R/madeira/actions/runs/37171941997) | CSNZ | `bb5911c822a7` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37171940008](https://github.com/R347H4CK3R/madeira/actions/runs/37171940008) | CSNZ | `bb5911c822a7` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37171186653](https://github.com/R347H4CK3R/madeira/actions/runs/37171186653) | CSNZ | `773e6ed17310` | Configure Wine ARM64EC generated headers | make include was a no-op; generated-header/flattened-symlink assertions failed. |
| [37171184679](https://github.com/R347H4CK3R/madeira/actions/runs/37171184679) | CSNZ | `773e6ed17310` | Configure Wine ARM64EC generated headers | make include was a no-op; generated-header/flattened-symlink assertions failed. |
| [37171183049](https://github.com/R347H4CK3R/madeira/actions/runs/37171183049) | CSNZ | `4a084b046bcd` | Configure Wine ARM64EC generated headers | make include was a no-op; generated-header/flattened-symlink assertions failed. |
| [37171180870](https://github.com/R347H4CK3R/madeira/actions/runs/37171180870) | CSNZ | `4a084b046bcd` | Configure Wine ARM64EC generated headers | make include was a no-op; generated-header/flattened-symlink assertions failed. |
| [37171153559](https://github.com/R347H4CK3R/madeira/actions/runs/37171153559) | CSNZ | `278fe423bc0e` | Configure Wine ARM64EC generated headers | make include was a no-op; generated-header/flattened-symlink assertions failed. |
| [37171151245](https://github.com/R347H4CK3R/madeira/actions/runs/37171151245) | CSNZ | `278fe423bc0e` | Configure Wine ARM64EC generated headers | make include was a no-op; generated-header/flattened-symlink assertions failed. |
| [37170130405](https://github.com/R347H4CK3R/madeira/actions/runs/37170130405) | CSNZ | `45d37f16798c` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37170127679](https://github.com/R347H4CK3R/madeira/actions/runs/37170127679) | CSNZ | `45d37f16798c` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37170125327](https://github.com/R347H4CK3R/madeira/actions/runs/37170125327) | CSNZ | `5f60faab4c45` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37170122834](https://github.com/R347H4CK3R/madeira/actions/runs/37170122834) | CSNZ | `5f60faab4c45` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37169723209](https://github.com/R347H4CK3R/madeira/actions/runs/37169723209) | CSNZ | `11a4e8ae76bb` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37169720565](https://github.com/R347H4CK3R/madeira/actions/runs/37169720565) | CSNZ | `11a4e8ae76bb` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37169155387](https://github.com/R347H4CK3R/madeira/actions/runs/37169155387) | CSNZ | `ac8ed0b6f518` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37169152466](https://github.com/R347H4CK3R/madeira/actions/runs/37169152466) | CSNZ | `ac8ed0b6f518` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37169131060](https://github.com/R347H4CK3R/madeira/actions/runs/37169131060) | CSNZ | `ac200b300ea8` | Workflow rejected; no job | Invalid YAML: literal \\n embedded in run/name block (locally reproduced parser failure). |
| [37168827091](https://github.com/R347H4CK3R/madeira/actions/runs/37168827091) | CSNZ | `b1bd6213b1c0` | Workflow rejected; no job | Invalid YAML: literal \\n embedded in run/name block (locally reproduced parser failure). |
| [37168797839](https://github.com/R347H4CK3R/madeira/actions/runs/37168797839) | CSNZ | `1cd5e42e1184` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37168396056](https://github.com/R347H4CK3R/madeira/actions/runs/37168396056) | CSNZ | `220a9918e41b` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37167981955](https://github.com/R347H4CK3R/madeira/actions/runs/37167981955) | CSNZ | `022ed19c06c9` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib; compiler .err details not printed (artifacts now absent). |
| [37167951152](https://github.com/R347H4CK3R/madeira/actions/runs/37167951152) | CSNZ | `abaf390e1bae` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib server; compiler .err details not printed (artifacts now absent). |
| [37167507585](https://github.com/R347H4CK3R/madeira/actions/runs/37167507585) | CSNZ | `85e89fba334a` | Build Wine iOS unix library with CSNZ diagnostic | Failed: dwrite_unixlib winegstreamer_unixlib server; compiler .err details not printed (artifacts now absent). |
| [37167363237](https://github.com/R347H4CK3R/madeira/actions/runs/37167363237) | CSNZ | `418fbeebe37c` | Configure Wine generated headers | Apple/system bison too old; Homebrew bison not first in PATH. |
| [37167241165](https://github.com/R347H4CK3R/madeira/actions/runs/37167241165) | CSNZ | `83ba8a5454ee` | Configure Wine generated headers | Apple/system bison too old; Homebrew bison not first in PATH. |
| [37166914455](https://github.com/R347H4CK3R/madeira/actions/runs/37166914455) | CSNZ | `c0d35b532d38` | Configure Wine generated headers | aarch64 PE cross compiler not available to Wine configure. |
| [37166910320](https://github.com/R347H4CK3R/madeira/actions/runs/37166910320) | CSNZ | `a82e06a7c8b4` | Install host tools | Invalid Rust target aarch64-apple-iosn. |
| [37166765716](https://github.com/R347H4CK3R/madeira/actions/runs/37166765716) | CSNZ | `d25b5471f6c9` | Install host tools | Invalid Rust target aarch64-apple-iosn. |
| [37166596094](https://github.com/R347H4CK3R/madeira/actions/runs/37166596094) | CSNZ | `2c093877b454` | Install host tools | Invalid Rust target aarch64-apple-iosn. |
| [37166455190](https://github.com/R347H4CK3R/madeira/actions/runs/37166455190) | CSNZ | `98c6afa04a70` | Configure Wine generated headers | Apple/system bison too old; Homebrew bison not first in PATH. |

Machine-readable evidence: `cod-ci-failed-runs.json` contains all 66 run IDs, full SHAs, titles, timestamps, failed step names, job IDs, extracted strong log errors, and current artifact arrays. For jobs that redirected compiler diagnostics to .err files without printing them, the cause is reported at the object/group level because those artifacts are now absent.
