#!/usr/bin/env python3
"""Publish a released unsigned StrataForge probe IPA into a Strata-compatible source feed."""
import datetime
import json
import pathlib
import sys

tag, build, filename, feed_name = sys.argv[1:]
if not tag.startswith("strataforge-probe-") or not build.isdigit():
    raise SystemExit("Invalid release tag or build number")
if filename != "StrataForgeProbe-unsigned.ipa":
    raise SystemExit("Only the verified minimal probe IPA can be published")
asset = pathlib.Path(filename)
size = asset.stat().st_size
if not 10000 < size < 100000000:
    raise SystemExit("Probe IPA outside expected size limits")
feed = pathlib.Path(feed_name)
source = json.loads(feed.read_text())
url = f"https://github.com/R347H4CK3R/madeira/releases/download/{tag}/{filename}"
version = {
    "version": f"0.1.{build}",
    "buildVersion": str(build),
    "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "localizedDescription": "StrataForge capability probe ONLY; Wine, FEX, Steam and Windows games are not included or verified.",
    "downloadURL": url,
    "size": size,
    "minOSVersion": "17.0",
}
app = {
    "name": "StrataForge Probe",
    "bundleIdentifier": "com.r347h4ck3r.strataforge.probe",
    "developerName": "R347H4CK3R",
    "subtitle": "Strata compatibility diagnostics",
    "localizedDescription": "An unsigned iPhone preflight app, not a Windows emulator. No Steam sign-in yet.",
    "versions": [version],
    "version": version["version"],
    "versionDate": version["date"],
    "downloadURL": url,
    "size": size,
    "iconURL": source.get("iconURL", "https://github.githubassets.com/favicons/favicon.png"),
    "tintColor": "4065B5",
    "category": "developer",
    "appPermissions": {"entitlements": [], "privacy": {}},
}
other = [a for a in source.get("apps", []) if a.get("bundleIdentifier") != app["bundleIdentifier"]]
source["apps"] = [app] + other
feed.write_text(json.dumps(source, indent=2) + "\n")
print(f"Updated {feed} with {tag} ({size} bytes)")
