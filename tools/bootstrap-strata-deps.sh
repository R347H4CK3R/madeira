#!/usr/bin/env bash
# Madeira dependency bootstrap (macOS only). No redistribution of Apple/Microsoft binaries.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
MODE="${1:---check}"
if [[ "$MODE" != "--check" && "$MODE" != "--install" ]]; then echo "Usage: $0 --check|--install"; exit 2; fi
missing=0
warn(){ printf 'MISSING: %s\n' "$*"; missing=$((missing+1)); }
ok(){ printf 'OK: %s\n' "$*"; }
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "BLOCKED: Xcode and this iOS build chain require macOS. Current host: $(uname -s)"
  exit 2
fi
for tool in xcodebuild xcrun git cmake ninja python3 curl shasum tar; do
  command -v "$tool" >/dev/null 2>&1 && ok "$tool" || warn "$tool"
done
if [[ "$MODE" == "--install" && $missing -gt 0 ]]; then echo "Install missing build tools first."; exit 2; fi
# Ensure a full Xcode (not just the Command Line Tools) is selected.
if xcodebuild -version >/dev/null 2>&1; then ok "Xcode selected"; else warn "Select full Xcode using xcode-select"; fi
# Preserve the pinned gitlink commits, never silently replace them with newer HEADs.
if [[ "$MODE" == "--install" ]]; then
  git submodule sync --recursive
  git submodule update --init --recursive || echo "Submodule checkout failed; inspect pinned commit availability."
fi
for mod in FEX wine dxmt madeira-dock; do
  if [[ -f "$mod/.git" || -d "$mod/.git" ]]; then ok "submodule $mod"; else warn "submodule $mod (pinned checkout)"; fi
done
# Exact upstream toolchain hash from docs/BUILDING.md.
TC="toolchains/llvm-mingw-20260421-ucrt-macos-universal"
ARCHIVE="llvm-mingw-20260421-ucrt-macos-universal.tar.xz"
URL="https://github.com/mstorsjo/llvm-mingw/releases/download/20260421/$ARCHIVE"
SHA="bd85a3975723815cef28dbbd2ca2cb0c926f6b348a12a0453f39f7af273cb3f7"
if [[ ! -d "$TC" && "$MODE" == "--install" ]]; then
  mkdir -p toolchains
  curl --fail --location --retry 3 "$URL" -o "toolchains/$ARCHIVE"
  echo "$SHA  toolchains/$ARCHIVE" | shasum -a 256 -c -
  tar -xf "toolchains/$ARCHIVE" -C toolchains
fi
[[ -d "$TC" ]] && ok "llvm-mingw toolchain" || warn "$TC"
# LLVM must be locally built for iOS; stage pinned source without claiming it is ready.
if [[ ! -d toolchains/llvm-project && "$MODE" == "--install" ]]; then
  mkdir -p toolchains
  git clone --filter=blob:none https://github.com/llvm/llvm-project.git toolchains/llvm-project
  git -C toolchains/llvm-project checkout 8dfdcc7b7
fi
[[ -d toolchains/llvm-project ]] && ok "LLVM source" || warn "LLVM source at commit 8dfdcc7b7"
[[ -d toolchains/llvm-ios-build ]] && ok "LLVM iOS build directory" || warn "toolchains/llvm-ios-build (compile LLVM per docs/BUILDING.md)"
[[ -d toolchains/llvm-host-build ]] && ok "LLVM host build directory" || warn "toolchains/llvm-host-build (TableGen)"
# Proprietary dependencies: never download unofficial copies or commit these.
[[ -d app/Madeira/x86_64-vcruntime && -n "$(find app/Madeira/x86_64-vcruntime -maxdepth 1 -iname 'vcruntime140*.dll' -print -quit 2>/dev/null)" ]] && ok "Microsoft VC++ x64 runtime" || warn "app/Madeira/x86_64-vcruntime (extract licensed vc_redist.x64.exe)"
# Native output files consumed by the Xcode target.
for lib in libavformat.a libavcodec.a libswresample.a libavutil.a libdxmt_combined.a libwineserver.a libntdll_unix.a libwin32u_unix.a libmadeira_rppairing.a; do
  [[ -f "app/Madeira/$lib" ]] && ok "$lib" || warn "app/Madeira/$lib (run the corresponding build script)"
done
echo "Missing prerequisites: $missing"
if (( missing > 0 )); then exit 1; fi
echo "Prerequisites found. Run project native build scripts and compile Debug IPA; this does not verify Strata runtime."
