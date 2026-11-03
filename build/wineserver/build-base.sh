#!/usr/bin/env bash
# Experimental: construct an iOS-arm64 Wine server base from pinned Wine sources.
# Native compile/link and runtime success require macOS and physical-device tests.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WINE="$ROOT/wine"
HERE="$ROOT/build/wineserver"
OBJ="$HERE/obj/base"
OUT="$HERE/obj/libwineserver.a"
MANIFEST="$WINE/server/Makefile.in"
CONFIG="$WINE/build-macos/include/config.h"

for tool in xcrun python3; do command -v "$tool" >/dev/null || { echo "ERROR: missing $tool" >&2; exit 2; }; done
[[ -s "$MANIFEST" && -s "$CONFIG" ]] || { echo "ERROR: pinned Wine source manifest or generated config.h missing" >&2; exit 2; }
SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
[[ -d "$SDK" ]] || { echo "ERROR: iPhoneOS SDK unavailable" >&2; exit 2; }
mkdir -p "$OBJ"

# Derive inputs from the pinned Wine version's Makefile, not wildcard source globs.
MANIFEST_LIST="$OBJ/sources.list"
python3 - "$MANIFEST" > "$MANIFEST_LIST" <<'PY'
from pathlib import Path
import re
import sys
lines = Path(sys.argv[1]).read_text().splitlines()
found = False
sources = []
for line in lines:
    if not found:
        if not re.match(r'^SOURCES\s*=', line):
            continue
        found = True
        line = line.split('=', 1)[1]
    sources.extend(re.findall(r'[A-Za-z0-9_./-]+\.c\b', line))
    if not line.rstrip().endswith('\\'):
        break
if not found:
    raise SystemExit('Missing SOURCES declaration in Wine manifest')
print('\n'.join(sources))
PY
FILES=()
while IFS= read -r file; do [[ -n "$file" ]] && FILES+=("$file"); done < "$MANIFEST_LIST"
(( ${#FILES[@]} >= 35 )) || { echo "ERROR: incomplete Wine server source manifest" >&2; exit 2; }
flags=( -arch arm64 -isysroot "$SDK" -miphoneos-version-min=17.0 -O2
  -I"$WINE/include" -I"$WINE/include/wine" -I"$WINE/build-macos/include"
  -I"$WINE/server" -I"$HERE" -I"$ROOT/build/ntdll-unix/shims"
  -I"$ROOT/build/madsync" -DHAVE_LINUX_NTSYNC_H=1
  -include "$HERE/config_ios.h" -include stdarg.h
  -include "$HERE/unicode_fix.h" -include "$HERE/wineserver_ios_kill.h"
  '-DBINDIR="/usr/local/bin"' '-DDATADIR="/usr/local/share"'
  -D__WINESRC__ -DWINE_IOS=1 -Dmain=wineserver_main
  -Wno-implicit-function-declaration )
for name in "${FILES[@]}"; do
    src="$WINE/server/$name"
    case "$name" in
      request.c) src="$HERE/request_ios.c";;
      main.c) src="$HERE/main_ios.c";;
      mach.c) src="$HERE/mach_ios.c";;
      unicode.c) src="$HERE/unicode_ios.c";;
      fd.c) src="$HERE/fd_ios.c";;
      mapping.c) src="$HERE/mapping_ios.c";;
      queue.c) src="$HERE/queue_ios.c";;
      window.c) src="$HERE/window_ios.c";;
    esac
    [[ -s "$src" ]] || { echo "ERROR: missing $src" >&2; exit 2; }
    echo "Compiling wineserver: $name"
    xcrun --sdk iphoneos clang "${flags[@]}" -c "$src" -o "$OBJ/${name%.c}.o"
done
xcrun --sdk iphoneos clang "${flags[@]}" -c "$HERE/wine_log_ios.c" -o "$OBJ/wine_log_ios.o"
xcrun --sdk iphoneos clang -arch arm64 -isysroot "$SDK" -miphoneos-version-min=17.0 -O2 \
  -I"$HERE" -DWINE_IOS=1 -Wno-implicit-function-declaration \
  -c "$HERE/wineserver_ios_kill.c" -o "$OBJ/wineserver_ios_kill.o"
objects=()
for name in "${FILES[@]}"; do objects+=("$OBJ/${name%.c}.o"); done
objects+=("$OBJ/wine_log_ios.o" "$OBJ/wineserver_ios_kill.o")
rm -f "$OUT"
xcrun --sdk iphoneos ar rcs "$OUT" "${objects[@]}"
xcrun --sdk iphoneos ar t "$OUT" | grep -Fxq 'request.o'
echo "Created candidate base archive: $OUT"
echo "Run build/wineserver/build.sh all to apply remaining patches and symbol renames."
echo "This is not proof of native iOS link or runtime compatibility."
