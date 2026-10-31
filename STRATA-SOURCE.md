# Madeira install/update source for Strata

Source URL: https://raw.githubusercontent.com/R347H4CK3R/madeira/main/apps.json

This is an AltStore-compatible JSON feed. Paste the URL in Strata's Sources feature **only if your Strata release accepts AltStore-style sources**. Some Strata releases may require a different format.

## Publishing an app
1. Compile Madeira into a valid iOS IPA. A source repository or `.zip` is not an installable app.
2. Publish a non-draft GitHub Release and attach the `.ipa` file.
3. The `Update Madeira IPA source` workflow inspects the IPA's `Info.plist` for bundle ID/version and updates `apps.json`.
4. Refresh the source in Strata. Keep the same bundle identifier if you need app updates to preserve data.

The feed deliberately contains zero apps until an IPA has been published and checked. The workflow does not compile Madeira. It does not repair JIT or Wineserver. GitHub release assets need to be publicly downloadable for the source to function.

If the workflow cannot push `apps.json`, set Actions → General → Workflow permissions to read and write. Do not disable branch protection solely to make this work.
