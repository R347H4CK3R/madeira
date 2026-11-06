#!/bin/bash
# Configure (first time) and build the FEXCore static libraries the app links
# (FEX/build-ios/FEXCore/Source/*.a and External/*). Options mirror the
# development build's CMakeCache.
set -eu
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
B="$R/FEX/build-ios"
# The pinned FEX Core.cpp references iOS-only log buffers from all hosts.
# Guard that telemetry in a reproducible overlay rather than moving gitlinks.
python3 "$R/tools/patch-fex-ios-core.py" "$R/FEX/FEXCore/Source/Interface/Core/Core.cpp"
python3 "$R/tools/patch-fex-arm64-ios.py" "$R/FEX/FEXCore/Source/Utils/ArchHelpers/Arm64.cpp"
if [ ! -f "$B/CMakeCache.txt" ]; then
    cmake -S "$R/FEX" -B "$B" -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_ARCHITECTURES=arm64 \
        -DCMAKE_OSX_SYSROOT=iphoneos -DCMAKE_OSX_DEPLOYMENT_TARGET=17.0 \
        -DCMAKE_SYSTEM_PROCESSOR=arm64 -DCMAKE_BUILD_TYPE=Release \
        -DTUNE_CPU=none -DTUNE_ARCH=generic \
        -DBUILD_TESTING=OFF -DBUILD_THUNKS=OFF -DBUILD_FEXCONFIG=OFF -DBUILD_FEX_LINUX_TESTS=OFF \
        -DENABLE_FEX_ALLOCATOR=OFF -DENABLE_ASSERTIONS=OFF -DENABLE_CLANG_THUNKS=ON -DENABLE_CCACHE=ON
fi
# Build each native target explicitly. Multiple targets passed to one cmake
# --build command did not produce libJemallocLibs.a on the CI runner.
# The Apple port disables glibc jemalloc/rpmalloc, but JemallocLibs is a
# separate FEX AllocatorHooks static target and must not be replaced by an
# empty archive merely to satisfy the Xcode linker input.
for target in FEXCore FEXCore_Base JemallocLibs; do
    echo "=== Building FEX target: $target ==="
    cmake --build "$B" --target "$target"
done
echo "=== FEX native archive inventory ==="
find "$B" -name '*.a' -type f -print | sort
test -s "$B/FEXCore/Source/libJemallocLibs.a" || {
    echo "Missing real JemallocLibs archive after explicit target build" >&2
    exit 1
}
