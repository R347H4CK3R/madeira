#!/usr/bin/env bash
# Retrieve pinned, checksum-verified compiler input for Madeira on macOS.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p toolchains
ARCHIVE="$RUNNER_TEMP/llvm-mingw-20260421-ucrt-macos-universal.tar.xz"
URL="https://github.com/mstorsjo/llvm-mingw/releases/download/20260421/llvm-mingw-20260421-ucrt-macos-universal.tar.xz"
SHA="bd85a3975723815cef28dbbd2ca2cb0c926f6b348a12a0453f39f7af273cb3f7"
curl --fail --location --retry 4 --retry-delay 4 --output "$ARCHIVE" "$URL"
echo "$SHA  $ARCHIVE" | shasum -a 256 --check
tar -xJf "$ARCHIVE" -C toolchains
test -x toolchains/llvm-mingw-20260421-ucrt-macos-universal/bin/arm64ec-w64-mingw32-clang
echo "Verified llvm-mingw compiler input."
