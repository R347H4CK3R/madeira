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
# The app links JemallocLibs even when Apple disables Linux-specific allocators.
# FEX defines a standalone AllocatorHooks archive; compile that target explicitly.
cmake --build "$B" --target FEXCore FEXCore_Base JemallocLibs
ls "$B/FEXCore/Source/"*.a
