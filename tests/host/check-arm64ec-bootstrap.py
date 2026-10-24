#!/usr/bin/env python3
"""Exercise Wine's ARM64EC bootstrap search with a local x64 CRT present.

The supplied COD log executes x64 ucrtbase DllMain bytes before FEX has a
thread state. This test compiles the pinned production load_arm64ec_module
and search_dll_file functions with host shims for NT file/registry/init APIs.
The file shim supplies distinct local-x64 and system-ARM64EC CRT fixtures.
It checks the bootstrap's chosen dependency search, normal app path order, and
failure when the native CRT is absent. It does not emulate FEX or an iPhone.

By default, apply the top-level Wine patch to a temporary source copy; the
pinned submodule is never changed. --unpatched runs the same cases against
the original source and should fail the local-CRT regression.
"""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "build/patches/wine-arm64ec-bootstrap-path.patch"


def function(source, declaration):
    start = source.index(declaration)
    return source[start:source.index("\n}\n", start) + 3]


PRELUDE = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include <setjmp.h>
typedef wchar_t WCHAR;
typedef const WCHAR *LPCWSTR;
typedef int32_t NTSTATUS;
typedef uint32_t DWORD, ULONG;
typedef int BOOL;
typedef void *HANDLE;
typedef struct { unsigned short Length, MaximumLength; WCHAR *Buffer; } UNICODE_STRING;
typedef struct { int unused; } OBJECT_ATTRIBUTES;
typedef struct { ULONG Type, DataLength; unsigned char Data[64]; } KEY_VALUE_PARTIAL_INFORMATION;
typedef struct { int unused; } SECTION_IMAGE_INFORMATION;
struct file_id { int unused; };
typedef struct { struct { void *DllBase, *DdagNode; UNICODE_STRING FullDllName; } ldr; } WINE_MODREF;
#define TRUE 1
#define FALSE 0
#define STATUS_SUCCESS 0
#define STATUS_DLL_NOT_FOUND ((NTSTATUS)0xc0000135)
#define STATUS_NO_MEMORY ((NTSTATUS)0xc0000017)
#define STATUS_NOT_SUPPORTED ((NTSTATUS)0xc00000bb)
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define RTL_CONSTANT_STRING(x) {sizeof(x)-sizeof(WCHAR), sizeof(x), (WCHAR *)(x)}
#define OBJ_CASE_INSENSITIVE 0
#define KEY_READ 0
#define KEY_WOW64_64KEY 0
#define KeyValuePartialInformation 0
#define REG_SZ 1
#define InitializeObjectAttributes(...) ((void)0)
#define TRACE(...) ((void)0)
#define ERR(...) ((void)0)
#define debugstr_w(x) (x)
#define min(a,b) ((a)<(b)?(a):(b))
static WCHAR *default_load_path = L"C:\\game;C:\\windows\\system32";
static WCHAR system_dir[] = L"C:\\windows\\system32";
static WINE_MODREF fixture_module;
static int native_farm, native_system, local_present, selected, attached, failures;
static NTSTATUS termination;
static jmp_buf terminated;
static void *GetProcessHeap(void) { return NULL; }
static void *RtlAllocateHeap(void *heap, int flags, size_t size) { return malloc(size); }
static void RtlFreeHeap(void *heap, int flags, void *ptr) { free(ptr); }
static NTSTATUS RtlDosPathNameToNtPathName_U_WithStatus(const WCHAR *name, UNICODE_STRING *out, void *a, void *b)
{
    out->Buffer = malloc((wcslen(name)+1)*sizeof(WCHAR));
    if (!out->Buffer) return STATUS_NO_MEMORY;
    wcscpy(out->Buffer, name);
    out->Length = wcslen(name)*sizeof(WCHAR);
    return 0;
}
static void RtlFreeUnicodeString(UNICODE_STRING *s) { free(s->Buffer); s->Buffer = NULL; }
static NTSTATUS open_dll_file(UNICODE_STRING *name, WINE_MODREF **wm, HANDLE *mapping,
                              SECTION_IMAGE_INFORMATION *info, struct file_id *id)
{
    int arch = 0;
    if (local_present && !wcscmp(name->Buffer, L"C:\\game\\ucrtbase.dll")) arch = 1;
    if (native_farm && !wcscmp(name->Buffer, L"C:\\windows\\sysx64\\ucrtbase.dll")) arch = 2;
    if (native_system && !wcscmp(name->Buffer, L"C:\\windows\\system32\\ucrtbase.dll")) arch = 2;
    *wm = NULL;
    if (!arch) return STATUS_DLL_NOT_FOUND;
    selected = arch;
    *wm = &fixture_module;
    return 0;
}
static NTSTATUS NtOpenKey(HANDLE *key, ULONG access, OBJECT_ATTRIBUTES *attr) { return STATUS_DLL_NOT_FOUND; }
static NTSTATUS NtQueryValueKey(HANDLE key, UNICODE_STRING *name, int klass,
                               void *buffer, ULONG size, ULONG *returned) { return STATUS_DLL_NOT_FOUND; }
static void NtClose(HANDLE handle) {}
static NTSTATUS arm64ec_process_init_dispatchers(void *module) { return 0; }
static NTSTATUS arm64ec_process_init(void *module) { return 0; }
static NTSTATUS process_attach(void *node, void *reserved) { attached++; return 0; }
static void NtTerminateProcess(HANDLE process, NTSTATUS status) { termination = status; longjmp(terminated, 1); }
static HANDLE GetCurrentProcess(void) { return (HANDLE)(intptr_t)-1; }
'''

# load_dll is the boundary with the rest of Wine's dependency mapper: the
# bootstrap supplies the path; the real production search below decides which
# file wins. Import recursion already forwards that same path in Wine.
LOAD_DLL = r'''
static NTSTATUS load_dll(const WCHAR *path, const WCHAR *name, DWORD flags, WINE_MODREF **wm, BOOL system)
{
    UNICODE_STRING nt_name = {0};
    HANDLE mapping = NULL;
    SECTION_IMAGE_INFORMATION info = {0};
    struct file_id id = {0};
    NTSTATUS status = search_dll_file(path, L"ucrtbase.dll", &nt_name, wm, &mapping, &info, &id);
    RtlFreeUnicodeString(&nt_name);
    return status;
}
'''

TESTS = r'''
static void expect(int condition, const char *label)
{
    printf("%s: %s\n", condition ? "PASS" : "FAIL", label);
    failures += !condition;
}
static void run_bootstrap(int farm, int system)
{
    native_farm = farm; native_system = system; local_present = 1;
    selected = attached = 0; termination = 0;
    if (!setjmp(terminated)) load_arm64ec_module();
}
int main(void)
{
    UNICODE_STRING nt_name = {0};
    WINE_MODREF *wm = NULL;
    HANDLE mapping = NULL;
    SECTION_IMAGE_INFORMATION info = {0};
    struct file_id id = {0};
    run_bootstrap(1, 0);
    expect(selected == 2 && attached == 1 && !termination,
           "bootstrap chooses native sysx64 CRT before application-local x64 CRT");
    run_bootstrap(0, 1);
    expect(selected == 2 && attached == 1 && !termination,
           "bootstrap supports native system32 when sysx64 farm is absent");
    run_bootstrap(0, 0);
    expect(selected == 0 && attached == 0 && termination == STATUS_DLL_NOT_FOUND,
           "missing native CRT fails bootstrap without attaching local x64 CRT");
    native_farm = native_system = local_present = 1; selected = 0;
    NTSTATUS status = search_dll_file(NULL, L"ucrtbase.dll", &nt_name, &wm, &mapping, &info, &id);
    expect(!status && selected == 1,
           "ordinary application search keeps local-first path ordering");
    RtlFreeUnicodeString(&nt_name);
    return failures ? 1 : 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unpatched", action="store_true")
    args = parser.parse_args()
    cc = os.environ.get("CC") or shutil.which("cc")
    if not cc:
        sys.exit("FAIL: a C compiler is required")
    source = ROOT / "wine/dlls/ntdll/loader.c"
    if not source.exists():
        sys.exit("FAIL: the pinned Wine submodule is required")
    original = subprocess.run(["git", "-C", str(ROOT / "wine"), "show",
                               "HEAD:dlls/ntdll/loader.c"], capture_output=True)
    if original.returncode:
        sys.exit("FAIL: cannot read the pinned Wine loader source")
    with tempfile.TemporaryDirectory(prefix="madeira-ec-bootstrap-") as temp:
        directory = Path(temp)
        copied = directory / "dlls/ntdll/loader.c"
        copied.parent.mkdir(parents=True)
        # Build scripts may already have applied the patch in their checkout.
        # Start from the pinned object so RED and GREEN stay reproducible there.
        copied.write_bytes(original.stdout)
        if not args.unpatched:
            if not PATCH.exists():
                sys.exit("FAIL: ARM64EC bootstrap patch is missing")
            for check in (True, False):
                command = ["git", "apply", "--directory=" + str(directory)]
                if check:
                    command.append("--check")
                command += ["--unsafe-paths", str(PATCH)]
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                if result.returncode:
                    sys.exit("FAIL: patch application: " + result.stderr)
        contents = copied.read_text()
        search = function(contents, "static NTSTATUS search_dll_file( LPCWSTR paths,")
        bootstrap = function(contents, "static void load_arm64ec_module(void)")
        harness = directory / "bootstrap.c"
        harness.write_text(PRELUDE + search + LOAD_DLL + bootstrap + TESTS)
        executable = directory / "bootstrap"
        result = subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-Wno-unused-parameter",
                                 "-Wno-unused-variable", "-o", str(executable), str(harness)],
                                capture_output=True, text=True)
        if result.returncode:
            sys.exit("FAIL: production bootstrap/search harness compilation:\n" + result.stderr)
        result = subprocess.run([str(executable)], capture_output=True, text=True)
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
