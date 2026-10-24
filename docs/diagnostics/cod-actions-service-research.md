# GitHub Actions execution gate — evidence and supported next step

Checked 2026-10-24. Repository: R347H4CK3R/madeira (public fork).

## What is established

The owner/admin's authenticated dispatch to workflow376920855 is rejected HTTP422 with `Actions has been disabled for this repository.` No new run is created. The repository policy API returns enabled=true, allowed_actions=all; the workflow state is active. The documented repository-enable PUT and workflow-enable PUT each return204, yet dispatch still returns the same422. Token scope/admin checks were completed. These are session observations reported by the coordinator; the research agent did not repeat mutations.

This proves a GitHub execution gate is rejecting the request before a runner starts. It does **not** establish the hidden reason, a GitHub Trust & Safety action, an account-wide restriction, a billing failure, or a defect in the new build script.

## Official explanation for the apparent contradiction

GitHub's repository settings documentation has a separate note about disabled repository/account messages:

> the repository or account may be in a separate GitHub-controlled disabled state, and changing these settings won't restore access. Contact GitHub Support for review.

[Official GitHub documentation — Managing GitHub Actions settings for a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository#managing-github-actions-permissions-for-your-repository)

The important qualifier is **may**. This documents a supported explanation and review route; it does not identify the actual reason for this repository. Successful settings updates do not prove that the separate execution gate is open. The permissions endpoint returns repository policy, and workflow-enable sets the workflow state to active. [Permissions API](https://docs.github.com/en/rest/actions/permissions#get-github-actions-permissions-for-a-repository), [Workflow API](https://docs.github.com/en/rest/actions/workflows#enable-a-workflow)

## Other documented gates, distinguished from this evidence

| Gate | Evidence here / appropriate diagnostic |
|---|---|
| Fork opt-in | GitHub says fork workflows require enabling in the fork's Actions tab. The66 old runs prove prior execution, but do not show the current owner-only page state. The native-app screenshot lists history; it does not establish whether a browser shows an opt-in/disabled banner. Inspect the owner-signed-in web Actions page once; use its enable control only if that specific prompt appears. |
| Manually disabled workflow | API says active, and enable already succeeded. Repeating it has no additional diagnostic value. |
| Organization/enterprise policy | GitHub documents higher-level policies overriding repository settings. This is a personally owned public fork; no applicable organization/enterprise policy was established. |
| Billing/budget/storage | GitHub documents billing errors and budgets as a separate troubleshooting category. Standard GitHub-hosted runners in public repositories are free, including this standard macos-15 job. No billing error was observed; do not claim minutes exhaustion or change billing blindly. |
| GitHub-controlled repository/account state | Explicitly documented; consistent with the rejected execution despite enabled policy. Only GitHub can confirm whether this is the operative state and why. |
| Service incident | GitHub Status reported Actions operational when checked. This does not rule out a repository-specific service defect. |

Sources: [Fork workflow opt-in](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflows-in-forked-repositories), [Troubleshooting](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows), [Public runner billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [GitHub Status](https://www.githubstatus.com/).

A closely matching public-fork report exists in [GitHub Community discussion210042](https://github.com/orgs/community/discussions/210042). Its reporter describes enabled settings plus the identical422. The reply's claim about abuse/compute flags is unverified community speculation, not an official finding and not evidence about this account.

## Supported repair/escalation

1. Preserve the exact failed response, UTC timestamp, X-GitHub-Request-Id response header, repository ID/name, workflow ID/path, branch/ref and commit SHA, enabled-policy JSON, active-workflow JSON, and successful204 settings responses. Redact Authorization headers and credentials. Record explicitly that no run ID or runner logs exist because queue admission failed.
2. Check the owner-signed-in browser Actions page once. If it shows a normal fork opt-in prompt, complete that supported enable action. If it instead shows GitHub-controlled disablement, or shows no repairable prompt and dispatch remains rejected, follow the documentation's Support review route.
3. Submit a review request through [GitHub Support](https://support.github.com/contact). The owner chooses what account/repository information to share. No support ticket, community post, email, or other external message has been sent by this research task. [Official Actions support guidance](https://docs.github.com/en/actions/how-tos/get-support)

Do not keep toggling permissions, retrying unchanged requests, changing branches/workflow filenames, or adding self-hosted runners as a purported fix. Those actions do not establish or remove a repository execution gate. Do not create another repository/account to evade a possible restriction. Building locally on an already authorized macOS machine is a separate execution option; it does not repair GitHub's state.

## Ready-to-review support text

Subject: Actions dispatch rejected as repository disabled despite enabled policy and active workflow

GitHub Actions on R347H4CK3R/madeira is rejecting workflow dispatch with HTTP422 and message `Actions has been disabled for this repository.` No new workflow run is created. The authenticated owner has repository admin access. GET /repos/R347H4CK3R/madeira/actions/permissions reports enabled=true and allowed_actions=all. The workflow state is active. The documented repository permissions PUT and workflow enable PUT both return204, but dispatch remains rejected.

Please review whether this repository or its owner is in a separate GitHub-controlled disabled state or has another execution-admission issue, and identify the supported restoration step. We are not asserting a policy/abuse/billing cause. I can provide the exact UTC request timestamps, request IDs, redacted API responses, workflow file, target commit/ref, and owner-visible Actions page details. There are no new run URLs/logs because admission fails before a run is created.
