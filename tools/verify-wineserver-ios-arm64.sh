#!/usr/bin/env bash
set -euo pipefail
archive="$1"
report="$2"
test -s "$archive" || { echo "Missing patched Wine archive: $archive" >&2; exit 1; }
archive="$(cd "$(dirname "$archive")" && pwd)/$(basename "$archive")"
mkdir -p "$(dirname "$report")"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
xcrun --sdk iphoneos ar t "$archive" | grep -E '[.]o$' > "$tmp/members.txt"
grep -Fxq 'request_ios.o' "$tmp/members.txt" || { echo "Missing request_ios.o" >&2; exit 1; }
if grep -Fxq 'request.o' "$tmp/members.txt"; then
  echo "Unpatched request.o remains" >&2
  exit 1
fi
(cd "$tmp" && xcrun --sdk iphoneos ar x "$archive")
count=0
while IFS= read -r obj; do
  test -s "$tmp/$obj" || { echo "Missing member $obj" >&2; exit 1; }
  archs="$(xcrun --sdk iphoneos lipo -archs "$tmp/$obj")"
  if test "$archs" != "arm64"; then
    echo "Bad architecture in $obj: $archs" >&2
    exit 1
  fi
  count=$((count + 1))
done < "$tmp/members.txt"
test "$count" -ge 20 || { echo "Too few objects: $count" >&2; exit 1; }
{
  echo "Verified $count patched Wine server object files for arm64."
  echo "request_ios.o present; unpatched request.o absent."
  shasum -a 256 "$archive"
} | tee "$report"
