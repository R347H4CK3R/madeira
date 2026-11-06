# Microsoft Visual C++ x64 runtime — user-owned guest setup

The public StrataForge IPA intentionally contains **no Microsoft VC++ DLLs**. Microsoft limits redistribution to eligible licensees under its software terms. The runtime is installed into each user's Wine guest from their own Windows environment instead.

## Prepare on Windows

1. Install the latest [official Microsoft x64 VC++ Redistributable](https://aka.ms/vc14/vc_redist.x64.exe) on Windows if the x64 DLLs are not already installed.
2. From PowerShell on that Windows PC, run `tools/prepare-vc-runtime.ps1` in a checkout of this repository. The script collects only locally installed DLLs, checks the x64 PE machine type, checks the Windows Authenticode publisher signature, and writes to `vc-runtime-x64` on your Desktop. It **does not** upload files or include Microsoft binaries in a public GitHub artifact.
3. Copy the `vc-runtime-x64` directory into the StrataForge/Madeira app's **On My iPhone** Documents location using Apple's Files app or device file sharing. The app's `UIFileSharingEnabled` and `LSSupportsOpeningDocumentsInPlace` are already enabled.
4. Launch a Wine session. `ContentView.stagePersonalVCRuntime()` validates the x64 PE machine field and copies missing approved DLL names into `Documents/wine/drive_c/windows/system32`. Existing runtime DLLs are not overwritten.

The minimum set is `vcruntime140.dll` and `msvcp140.dll`; the script also collects other installed v14 runtime components if present. This handles guest runtime staging **without running the VC++ redistributable EXE under the iOS Wine guest**, which is important because some installers use 32-bit bootstrap components and the current guest supports x64 only.

## Validation and limits

- Authenticode validation runs on the Windows PC, **not on the iPhone**. The iPhone validates PE x64 architecture and expected filenames, not publisher signatures.
- DLLs are for the x64 Windows guest and must never be linked as iOS ARM64 native libraries.
- A program may require additional redistributable components or the universal CRT. Merely staging these files is not proof that the Steam client or a game can launch.
- Some license terms may restrict copying or installing files outside Microsoft-supported Windows systems. Confirm your own rights and the target application's license before using the files.
- D3D12 graphics support is a separate feature and must be validated in the DXMT build and on device.
