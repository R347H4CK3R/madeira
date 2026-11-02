# StrataForge JIT, memory, and diagnostics integration

## What Strata can provide
Strata (LiveContainer-based iOS launcher) documents a **host-side** JIT preparation flow:
1. Sign/install Strata using a legitimate signing profile, enable iOS Developer Mode.
2. Import a valid pairing record into Strata, enable its required LocalDevVPN helper, and run **JIT > Prepare Device**.
3. Import the correctly compiled StrataForge guest via Strata's source and select **Launch with JIT**.
4. Use device logs and a translated-code self-test to verify JIT **inside the guest's actual executing process**. Host-side "prepared" alone is insufficient.

For RAM: Strata documents a capability request for installed host and guest App IDs, followed by re-signing/refreshing. Requesting the capability does not guarantee a higher memory limit. Check the actual guest process's resident memory and termination behavior, not a launcher RAM label.

## Runtime integration gates
- Wire `StrataForgeDiagnostics.beginSession()` at the *actual* app entry point (not the standalone probe).
- Emit short phase markers around JIT, FEX translated-code execution, Wine server startup/handshake, DXMT/Metal, Steam login initiation, game launch and teardown.
- Emit measured resident-size readings and memory-warning events, never raw URLs, tokens, credentials, Steam Guard values, user paths or logins.
- Create a bounded preflight of executable JIT memory; **do not** request unsupported entitlements, bypass signing or assert that a writable mapping implies executable permission.
- Implement bounded caches with explicit user-configurable limits and release idle shader/translation caches on memory pressure, benchmarking any impact on stutter.
- On next launch detect previous-session log; present a privacy preview, an explicit **Send sanitized report** action, and **Delete report**.
- Send only scrubbed failure codes and selected diagnostic fields to a dedicated authenticated backend or a GitHub issue via an expiring scoped credential. **Never embed a GitHub write token in the IPA or push a report automatically without the user's opt-in.**
- A crash may prevent uploads until next successful launch; complete device-terminated reports require iOS diagnostic logs obtained by the user/Strata.

## Honest status
The added `strataforge-runtime/StrataForgeDiagnostics.swift` is a **standalone, not-yet-integrated implementation**. It is not part of the current Madeira Xcode app target. No automatic GitHub crash upload is deployed. The `tools/strataforge_sanitize.py` script performs an additional host-side redaction pass and is not an iOS networking client. The runtime remains unverified in Strata.

## Links
Strata host setup: https://github.com/huzaifahshahid71-ops/Strata
Apple JIT entitlement docs: https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.cs.allow-jit
