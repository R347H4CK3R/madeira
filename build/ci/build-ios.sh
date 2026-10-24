#!/bin/bash
# Build real arm64 iOS archives and the Debug app from the pinned source tree.
# Each stage is independently callable so CI can cache only completed builds.
set -euo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$R"
STAGE="${1:-all}"
JOBS="${JOBS:-$(sysctl -n hw.ncpu)}"
LLVM_REV=8dfdcc7b7
TC="$R/toolchains/llvm-mingw-20260421-ucrt-macos-universal"
export PATH="$TC/bin:$PATH"
export CMAKE_BUILD_PARALLEL_LEVEL="$JOBS"
OUT="$R/build/ci-output"
mkdir -p "$OUT/logs"

require() { for p in "$@"; do test -s "$p" || { echo "Missing build output: $p" >&2; return 1; }; done; }

setup() {
    test "$(uname -s)" = Darwin
    xcodebuild -version
    xcrun --sdk iphoneos --show-sdk-version
    xcrun --sdk iphoneos --show-sdk-build-version
    git rev-parse HEAD > "$OUT/source-revision.txt"
    git submodule status --recursive > "$OUT/submodules.txt"
    if [ ! -x "$TC/bin/x86_64-w64-mingw32-clang" ]; then
        mkdir -p toolchains
        curl -fL --retry 3 -o toolchains/llvm-mingw.tar.xz \
            https://github.com/mstorsjo/llvm-mingw/releases/download/20260421/llvm-mingw-20260421-ucrt-macos-universal.tar.xz
        echo 'bd85a3975723815cef28dbbd2ca2cb0c926f6b348a12a0453f39f7af273cb3f7  toolchains/llvm-mingw.tar.xz' | shasum -a 256 -c -
        tar -xJf toolchains/llvm-mingw.tar.xz -C toolchains
    fi
    if [ ! -d research/freetype/.git ]; then
        mkdir -p research
        git clone --depth 1 --branch VER-2-13-3 https://github.com/freetype/freetype.git research/freetype
    fi
    git -C research/freetype rev-parse HEAD > "$OUT/freetype-revision.txt"
    rustup target add aarch64-apple-ios
    rustc --version > "$OUT/rust-version.txt"
    # Verify the tracked converter library and public headers; Apple's installer
    # is needed only to refresh them or run converter tools on the host.
    bash build/madeira-d3d12/deps.sh
}

media() {
    bash build/gnutls-ios/build.sh
    bash build/ffmpeg/build.sh
    bash build/freetype-ios/build.sh
    require toolchains/gnutls-ios/include/gnutls/gnutls.h \
        toolchains/ffmpeg-ios/include/libavformat/avformat.h \
        build/freetype-ios/build/libfreetype.a
}

headers() {
    mkdir -p wine/build-macos wine/build-arm64ec
    (cd wine/build-macos && ../configure --without-x --disable-tests --enable-winegstreamer)
    # makedep emits include/all for ALL generated headers. `make include` is
    # a no-op because include is an existing directory, and a partial hand-picked
    # list omitted transitive headers such as docobj.h in previous CI attempts.
    make -C wine/build-macos -j"$JOBS" include/all
    (cd wine/build-arm64ec && ../configure --enable-archs=arm64ec \
        --without-x --disable-tests --enable-winegstreamer)
    make -C wine/build-arm64ec -j"$JOBS" include/all
    require wine/build-macos/include/config.h wine/build-macos/include/docobj.h \
        wine/build-macos/include/dwrite.h wine/build-arm64ec/include/dwrite_3.h \
        wine/build-arm64ec/include/mfobjects.h
}

native() {
    bash build/ntdll-unix/build.sh
    if [ ! -s build/wineserver/obj/libwineserver.a ]; then
        bash build/wineserver/bootstrap-base.sh
    fi
    bash build/wineserver/build.sh
    bash build/win32u-unix/build.sh
    require app/Madeira/libntdll_unix.a app/Madeira/libwineserver.a app/Madeira/libwin32u_unix.a
}

pe() {
    local patch="$R/build/patches/wine-arm64ec-bootstrap-path.patch"
    require "$patch"
    if git -C wine apply --check "$patch"; then
        git -C wine apply "$patch"
    else
        git -C wine apply --reverse --check "$patch"
    fi
    bash build/wine-pe/build-ntdll.sh
    shasum -a 256 app/Madeira/arm64ec-windows/ntdll.dll > "$OUT/ntdll-sha256.txt"
    git -C wine diff > "$OUT/wine-build.patch"
}

fex() {
    # Explicit processor prevents an Intel macos-15 runner from selecting its
    # host CPU for the iOS cross build. No FEX source files are modified.
    cmake -S FEX -B FEX/build-ios -G Ninja \
        -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_SYSTEM_PROCESSOR=arm64 \
        -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_SYSROOT=iphoneos \
        -DCMAKE_OSX_DEPLOYMENT_TARGET=17.0 -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_TESTING=OFF -DBUILD_THUNKS=OFF -DBUILD_FEXCONFIG=OFF \
        -DBUILD_FEX_LINUX_TESTS=OFF -DENABLE_FEX_ALLOCATOR=OFF \
        -DENABLE_ASSERTIONS=OFF -DENABLE_CLANG_THUNKS=ON -DENABLE_CCACHE=ON \
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5
    cmake --build FEX/build-ios --target FEXCore FEXCore_Base JemallocLibs
    require FEX/build-ios/FEXCore/Source/libFEXCore.a FEX/build-ios/FEXCore/Source/libFEXCore_Base.a \
        FEX/build-ios/FEXCore/Source/libJemallocLibs.a FEX/build-ios/External/fmt/libfmt.a \
        FEX/build-ios/External/cephes/libcephes_128bit.a FEX/build-ios/External/xxhash/cmake_unofficial/libxxhash.a \
        FEX/build-ios/External/SoftFloat-3e/libsoftfloat_3e.a
}

pairing() {
    bash build/rppairing-ios/build.sh
    require app/Madeira/libmadeira_rppairing.a
}

llvm() {
    if [ ! -d toolchains/llvm-project/.git ]; then
        git clone --filter=blob:none --no-checkout https://github.com/llvm/llvm-project.git toolchains/llvm-project
        git -C toolchains/llvm-project checkout "$LLVM_REV"
    fi
    case "$(git -C toolchains/llvm-project rev-parse HEAD)" in
        "$LLVM_REV"*) ;;
        *) echo "LLVM checkout does not match $LLVM_REV" >&2; return 1 ;;
    esac
    git -C toolchains/llvm-project rev-parse HEAD > "$OUT/llvm-revision.txt"
    cmake -S toolchains/llvm-project/llvm -B toolchains/llvm-host-build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release -DLLVM_TARGETS_TO_BUILD= -DLLVM_INCLUDE_TESTS=OFF \
        -DLLVM_ENABLE_PROJECTS= -DLLVM_ENABLE_ZLIB=OFF -DLLVM_ENABLE_ZSTD=OFF
    cmake --build toolchains/llvm-host-build --target llvm-tblgen
    # LLVM 15 treats iOS as ELF here; Apple ld needs -dead_strip.
    python3 - <<'PY'
from pathlib import Path
p = Path('toolchains/llvm-project/llvm/cmake/modules/AddLLVM.cmake')
s = p.read_text()
assert 'MATCHES "Darwin"' in s or 'MATCHES "Darwin|iOS"' in s
p.write_text(s.replace('MATCHES "Darwin"', 'MATCHES "Darwin|iOS"'))
PY
    cmake -S toolchains/llvm-project/llvm -B toolchains/llvm-ios-build -G Ninja \
        -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_SYSTEM_PROCESSOR=arm64 -DCMAKE_OSX_ARCHITECTURES=arm64 \
        -DCMAKE_OSX_SYSROOT=iphoneos -DCMAKE_OSX_DEPLOYMENT_TARGET=17.0 \
        -DCMAKE_BUILD_TYPE=Release -DLLVM_HOST_TRIPLE=arm64-apple-ios17.0 \
        -DLLVM_DEFAULT_TARGET_TRIPLE=arm64-apple-ios17.0 -DLLVM_TARGET_ARCH=host \
        -DLLVM_TARGETS_TO_BUILD= -DLLVM_ENABLE_PROJECTS= -DLLVM_BUILD_TOOLS=OFF \
        -DLLVM_BUILD_UTILS=OFF -DLLVM_INCLUDE_TESTS=OFF -DLLVM_ENABLE_ZLIB=OFF -DLLVM_ENABLE_ZSTD=OFF \
        -DLLVM_TABLEGEN="$R/toolchains/llvm-host-build/bin/llvm-tblgen" \
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5
    cmake --build toolchains/llvm-ios-build
    require toolchains/llvm-ios-build/lib/libLLVMCore.a toolchains/llvm-ios-build/lib/libLLVMBitReader.a
}

graphics() {
    # Fail if Metal tooling is unavailable; the app and DXMT both compile Metal.
    if ! xcrun --sdk macosx metal --version; then
        xcodebuild -downloadComponent MetalToolchain
    fi
    unset MADEIRA_ALLOW_NO_D3D12
    bash build/dxmt-ios/build.sh
    # build.sh only refreshes an EXISTING combined archive; a fresh checkout
    # must create it explicitly from genuine DXMT objects and iOS LLVM libs.
    xcrun -sdk iphoneos libtool -static -o build/dxmt-ios/libdxmt_combined.a \
        build/dxmt-ios/obj/*.o toolchains/llvm-ios-build/lib/*.a
    cp build/dxmt-ios/libdxmt_combined.a app/Madeira/libdxmt_combined.a
    require app/Madeira/libdxmt_combined.a
}

dock() { bash build/madeira-dock/build.sh; require app/Madeira/arm64ec-windows/dockhost.exe; }

vcruntime() {
    # Microsoft DLLs are an external, unmodified input (tools/fetch-vcruntime.md).
    # CI accepts a private archive URL if its runner cannot extract the public
    # redist layout. No replacement DLLs or empty runtime directory are created.
    if [ -n "${MADEIRA_VCRUNTIME_ARCHIVE_URL:-}" ]; then
        mkdir -p app/Madeira/x86_64-vcruntime
        curl -fL --retry 3 "$MADEIRA_VCRUNTIME_ARCHIVE_URL" -o "$OUT/vcruntime.zip"
        unzip -jo "$OUT/vcruntime.zip" '*.dll' -d app/Madeira/x86_64-vcruntime
        rm "$OUT/vcruntime.zip"
    fi
    python3 - <<'PY'
from pathlib import Path
import hashlib, json, struct
root = Path('app/Madeira/x86_64-vcruntime')
names = '''concrt140.dll msvcp140.dll msvcp140_1.dll msvcp140_2.dll
msvcp140_atomic_wait.dll msvcp140_codecvt_ids.dll vcamp140.dll vccorlib140.dll
vcomp140.dll vcruntime140.dll vcruntime140_1.dll vcruntime140_threads.dll'''.split()
result = {}
for name in names:
    p = root / name
    if not p.is_file():
        raise SystemExit(f'Missing unmodified Microsoft input {p}; see tools/fetch-vcruntime.md or set MADEIRA_VCRUNTIME_ARCHIVE_URL')
    d = p.read_bytes()
    pe = struct.unpack_from('<I', d, 0x3c)[0]
    if d[:2] != b'MZ' or d[pe:pe+4] != b'PE\0\0' or struct.unpack_from('<H', d, pe+4)[0] != 0x8664:
        raise SystemExit(f'Not an x64 PE runtime: {p}')
    off, size = struct.unpack_from('<II', d, pe+24+112+4*8)
    if not size or off+size > len(d):
        raise SystemExit(f'Authenticode payload missing or truncated: {p}')
    result[name] = hashlib.sha256(d).hexdigest()
Path('build/ci-output/vcruntime-sha256.json').write_text(json.dumps(result, indent=2)+'\n')
PY
}

app() {
    bash build/stage-licenses.sh
    xcodebuild -project app/Madeira.xcodeproj -scheme Madeira \
        -configuration Debug -sdk iphoneos -destination 'generic/platform=iOS' \
        -derivedDataPath "$OUT/DerivedData" -resultBundlePath "$OUT/Madeira.xcresult" \
        ARCHS=arm64 ONLY_ACTIVE_ARCH=YES CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO build
    require "$OUT/DerivedData/Build/Products/Debug-iphoneos/Madeira.app/Madeira"
}

package() {
    local app_path="$OUT/DerivedData/Build/Products/Debug-iphoneos/Madeira.app"
    require "$app_path/Madeira"
    xcrun lipo -archs "$app_path/Madeira" > "$OUT/architectures.txt"
    xcrun otool -L "$app_path/Madeira" > "$OUT/linked-libraries.txt"
    xcrun otool -l "$app_path/Madeira" > "$OUT/load-commands.txt"
    # Unsigned build: record codesign's actual diagnostic without inventing a
    # developer identity or claiming installation readiness.
    codesign -dvvv "$app_path" > "$OUT/codesign.txt" 2>&1 || true
    codesign -d --entitlements :- "$app_path" > "$OUT/entitlements.txt" 2>&1 || true
    mkdir -p "$OUT/package/Payload"
    ditto "$app_path" "$OUT/package/Payload/Madeira.app"
    (cd "$OUT/package" && zip -qry "$OUT/Madeira-COD-Fix-Test.ipa" Payload)
    python3 tools/validate-ipa.py "$OUT/Madeira-COD-Fix-Test.ipa" --output "$OUT/ipa-validation.json"
    shasum -a 256 "$OUT/Madeira-COD-Fix-Test.ipa" > "$OUT/Madeira-COD-Fix-Test.ipa.sha256"
}

case "$STAGE" in
    setup|media|headers|native|pe|fex|pairing|llvm|graphics|dock|vcruntime|app|package) "$STAGE" ;;
    all) for task in setup media headers native pe fex pairing llvm graphics dock vcruntime app package; do "$task"; done ;;
    *) echo "Unknown build stage: $STAGE" >&2; exit 2 ;;
esac
