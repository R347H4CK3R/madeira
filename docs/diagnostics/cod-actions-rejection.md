# GitHub Actions execution rejection

This is a service rejection before job creation, not a compiler or YAML failure.

Repository: R347H4CK3R/madeira. Working branch: fix/cod-1938090-ipa-20261024.
Build source tested for dispatch: 3b058011b8b14dc9329db7f8404f1ab291d0a6b4.
Registered workflow: .github/workflows/cod-fix-build.yml, ID 376920855.

## Verified state

- Authenticated owner login, repository admin/maintain/push permissions.
- Existing credential broker used only for GitHub authentication; no credential values printed or persisted.
- Credential scopes include repo and workflow.
- Repository public, fork=true, archived=false, disabled=false.
- Actions permissions endpoint: enabled=true, allowed_actions=all.
- Registered workflow state active; exact branch and workflow file readable through API.
- No new workflow runs or check suites were created by source pushes.

## Supported repairs attempted

1. New filename dispatch returned 404 (unregistered workflow). Build recipe moved to the existing registered filename on the working branch; main unchanged.
2. Explicit dispatch of registered workflow returned HTTP 422, message: "Actions has been disabled for this repository."
3. PUT repository actions/permissions with ONLY enabled=true returned 204. Readback confirmed existing action-selection policy unchanged. Dispatch still returned 422.
4. PUT workflow 376920855/enable returned 204; workflow readback active, updated timestamp changed. Dispatch still returned 422.

Latest rejection at 2026-10-24 04:49:07 UTC:
GitHub request ID C71C:1993EC:3210991:A2EA90A:6ADC38C3.
Earlier rejection at 04:47:24 UTC: C6F2:ABC1B:3238990:A37BB42:6ADC385B.

The runs API returned total_count=0 for the working branch. There is no run ID, run URL, build log, IPA artifact, size or checksum from a new build.

## Remaining diagnostic boundary

GitHub accepted both documented enable operations but still refuses execution. The exact account/service restriction is not exposed by the available repository APIs. Account billing endpoints returned 404 and advertise a user scope unavailable to the existing credential; this does NOT prove a billing problem. The anonymous Actions page displays no explanatory warning.

Do not attribute this to YAML, missing workflow write scope, a missing branch, or billing without further evidence. A signed-in owner-visible notice at https://github.com/R347H4CK3R/madeira/actions or GitHub support using the request ID is needed to identify and clear the remaining service restriction. No support message was sent, no credential scopes were changed, and no alternate repository/account was used to evade it.
