#!/usr/bin/env bash
# Rebuild the exact LLVM support libraries Madeira's DXMT compiler expects.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v xcrun >/dev/null
command -v cmake >/dev/null
command -v ninja >/dev/null
mkdir -p toolchains
if [[ ! -f toolchains/llvm-project/llvm/CMakeLists.txt ]]; then
  git clone --filter=blob:none --no-checkout https://github.com/llvm/llvm-project.git toolchains/llvm-project
  git -C toolchains/llvm-project checkout 8dfdcc7b7
fi
test "$(git -C toolchains/llvm-project rev-parse --short=9 HEAD)" = "8dfdcc7b7"
HOST="$PWD/toolchains/llvm-host-build"
IOS="$PWD/toolchains/llvm-ios-build"
cmake -S toolchains/llvm-project/llvm -B "$HOST" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DLLVM_TARGETS_TO_BUILD=AArch64 \
  -DLLVM_ENABLE_PROJECTS='' -DLLVM_INCLUDE_TESTS=OFF \
  -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_ENABLE_ZLIB=OFF \
  -DLLVM_ENABLE_ZSTD=OFF -DLLVM_ENABLE_TERMINFO=OFF
cmake --build "$HOST" --target llvm-tblgen --parallel 3
test -x "$HOST/bin/llvm-tblgen"
cmake -S toolchains/llvm-project/llvm -B "$IOS" -G Ninja \
  -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_SYSTEM_PROCESSOR=arm64 \
  -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_SYSROOT=iphoneos \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=17.0 -DCMAKE_MACOSX_BUNDLE=OFF \
  -DCMAKE_BUILD_TYPE=Release -DLLVM_HOST_TRIPLE=arm64-apple-ios17.0 \
  -DLLVM_DEFAULT_TARGET_TRIPLE=arm64-apple-ios17.0 \
  -DLLVM_TARGET_ARCH=host -DLLVM_TARGETS_TO_BUILD='' \
  -DLLVM_ENABLE_PROJECTS='' -DLLVM_BUILD_TOOLS=OFF \
  -DLLVM_INCLUDE_TESTS=OFF -DLLVM_INCLUDE_BENCHMARKS=OFF \
  -DLLVM_ENABLE_ZLIB=OFF -DLLVM_ENABLE_ZSTD=OFF \
  -DLLVM_ENABLE_TERMINFO=OFF -DLLVM_TABLEGEN="$HOST/bin/llvm-tblgen"
cmake --build "$IOS" --target LLVMPasses LLVMBitWriter --parallel 3
echo "Built LLVM iOS dependencies for Madeira DXMT."
