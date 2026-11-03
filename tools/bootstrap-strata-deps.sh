#!/usr/bin/env bash
# Madeira dependency bootstrap (macOS only). No redistribution of Apple/Microsoft binaries.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
MODE="${1:---check}"
if [[ "$MODE" != "--check" && "$MODE" != "--install" && "$MODE" != "--prepare" ]]; then echo "Usage: $0 --check|--install|--prepare"; exit 2; fi
install_requested=false
[[ "$MODE" == "--install" || "$MODE" == "--prepare" ]] && install_requested=true
missing=0
warn(){ printf 'MISSING: %s\n' "$*"; missing=$((missing+1)); }
ok(){ printf 'OK: %s\n' "$*"; }
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "BLOCKED: Xcode and this iOS build chain require macOS. Current host: $(uname -s)"
  exit 2
fi
# On GitHub macOS runners, Meson and LLVM's objcopy are not guaranteed to be installed.
# --install explicitly permits preparing these open-source build tools.
if [[ "$install_requested" == true ]]; then
  packages=()
  command -v meson >/dev/null 2>&1 || packages+=(meson)
  if ! command -v llvm-objcopy >/dev/null 2>&1; then
    if ! test -x /opt/homebrew/opt/llvm/bin/llvm-objcopy && ! test -x /usr/local/opt/llvm/bin/llvm-objcopy; then
      packages+=(llvm)
    fi
  fi
  if (( ${#packages[@]} > 0 )); then
    command -v brew >/dev/null 2>&1 || { echo "BLOCKED: install ${packages[*]} or provide Homebrew" >&2; exit 2; }
    brew install "${packages[@]}"
  fi
  if command -v brew >/dev/null 2>&1; then
    llvm_bin="$(brew --prefix llvm 2>/dev/null || true)/bin"
    if [[ -x "$llvm_bin/llvm-objcopy" ]]; then
      export PATH="$llvm_bin:$PATH"
      if [[ -n "${GITHUB_PATH:-}" ]]; then echo "$llvm_bin" >> "$GITHUB_PATH"; fi
    fi
  fi
fi
for tool in xcodebuild xcrun git cmake ninja python3 curl shasum tar cargo rustup meson pkg-config llvm-objcopy; do
  command -v "$tool" >/dev/null 2>&1 && ok "$tool" || warn "$tool"
done
if [[ "$install_requested" == true && $missing -gt 0 ]]; then echo "Install missing build tools first."; exit 2; fi
# Ensure a full Xcode (not just the Command Line Tools) is selected.
if xcodebuild -version >/dev/null 2>&1; then ok "Xcode selected"; else warn "Select full Xcode using xcode-select"; fi
# Preserve the pinned gitlink commits, never silently replace them with newer HEADs.
if [[ "$install_requested" == true ]]; then
  git submodule sync --recursive
  git submodule update --init --recursive || { echo "BLOCKED: Submodule checkout failed; inspect pinned commit availability."; exit 1; }
fi
for mod in FEX wine dxmt madeira-dock; do
  if [[ -f "$mod/.git" || -d "$mod/.git" ]]; then ok "submodule $mod"; else warn "submodule $mod (pinned checkout)"; fi
done
# A .git marker alone says nothing about checkout success or the pinned revision.
if submodule_status=$(git submodule status --recursive); then
  while IFS= read -r entry; do
    [[ -z "$entry" ]] && continue
    case "$entry" in
      ' '*) ok "pinned submodule revision: $entry" ;;
      *) warn "pinned submodule revision: $entry" ;;
    esac
  done <<< "$submodule_status"
else
  warn "pinned submodule revision status could not be read"
fi
# Exact upstream toolchain hash from docs/BUILDING.md.
TC="toolchains/llvm-mingw-20260421-ucrt-macos-universal"
ARCHIVE="llvm-mingw-20260421-ucrt-macos-universal.tar.xz"
URL="https://github.com/mstorsjo/llvm-mingw/releases/download/20260421/$ARCHIVE"
SHA="bd85a3975723815cef28dbbd2ca2cb0c926f6b348a12a0453f39f7af273cb3f7"
if [[ ! -d "$TC" && "$install_requested" == true ]]; then
  mkdir -p toolchains
  curl --fail --location --retry 3 "$URL" -o "toolchains/$ARCHIVE"
  echo "$SHA  toolchains/$ARCHIVE" | shasum -a 256 -c -
  tar -xf "toolchains/$ARCHIVE" -C toolchains
fi
[[ -d "$TC" ]] && ok "llvm-mingw toolchain" || warn "$TC"
# LLVM must be locally built for iOS; stage pinned source without claiming it is ready.
if [[ ! -d toolchains/llvm-project && "$install_requested" == true ]]; then
  mkdir -p toolchains
  git clone --filter=blob:none https://github.com/llvm/llvm-project.git toolchains/llvm-project
  git -C toolchains/llvm-project checkout 8dfdcc7b7
fi
llvm_revision=$(git -C toolchains/llvm-project rev-parse HEAD 2>/dev/null || true)
[[ "$llvm_revision" == 8dfdcc7b7* ]] && ok "LLVM source at $llvm_revision" || warn "LLVM source at commit 8dfdcc7b7"
# Directories are not compiled outputs. Check files consumed by native scripts.
for input in toolchains/llvm-ios-build/include/llvm/Config/llvm-config.h \
  toolchains/llvm-ios-build/lib/libLLVMCore.a \
  toolchains/llvm-host-build/bin/llvm-tblgen \
  wine/build-macos/include/config.h \
  toolchains/ffmpeg-ios/include/libavformat/avformat.h \
  toolchains/gnutls-ios/include/gnutls/gnutls.h; do
  [[ -s "$input" ]] && ok "$input" || warn "$input"
done
for lib in FEXCore/Source/libFEXCore.a FEXCore/Source/libFEXCore_Base.a \
  FEXCore/Source/libJemallocLibs.a External/fmt/libfmt.a \
  External/cephes/libcephes_128bit.a External/xxhash/cmake_unofficial/libxxhash.a \
  External/SoftFloat-3e/libsoftfloat_3e.a; do
  input="FEX/build-ios/$lib"
  [[ -s "$input" ]] && ok "$input" || warn "$input (build/fex-ios/build.sh)"
done
# Proprietary dependencies: never download unofficial copies or commit these.
[[ -d app/Madeira/x86_64-vcruntime && -n "$(find app/Madeira/x86_64-vcruntime -maxdepth 1 -iname 'vcruntime140*.dll' -print -quit 2>/dev/null)" ]] && ok "Microsoft VC++ x64 runtime" || warn "app/Madeira/x86_64-vcruntime (extract licensed vc_redist.x64.exe)"
# Native output files consumed by the Xcode target.
for lib in libavformat.a libavcodec.a libswresample.a libavutil.a libdxmt_combined.a libwineserver.a libntdll_unix.a libwin32u_unix.a libmadeira_rppairing.a libgnutls.a libnettle.a libhogweed.a libgmp.a; do
  [[ -s "app/Madeira/$lib" ]] && ok "$lib" || warn "app/Madeira/$lib (run the corresponding build script)"
done
echo "Missing prerequisites: $missing"
if (( missing > 0 )); then
  if [[ "$MODE" == "--prepare" ]]; then
    echo "PREPARE COMPLETE: generated native outputs remain missing; native build stages are required."
    exit 0
  fi
  exit 1
fi
echo "Prerequisites found. Run project native build scripts and compile Debug IPA; this does not verify Strata runtime."
