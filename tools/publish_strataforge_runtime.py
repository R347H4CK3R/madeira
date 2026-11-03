#!/usr/bin/env python3
"""Publish a *compiled* full Madeira Wine/Steam runtime to the Strata source."""
import datetime, json, pathlib, sys
tag, build, filename, feedname = sys.argv[1:]
if not tag.startswith("strataforge-runtime-") or not build.isdigit() or filename != "StrataForge-Wine-Steam.ipa":
    raise SystemExit("Invalid full-runtime release arguments")
ipa = pathlib.Path(filename)
size = ipa.stat().st_size
if size < 1000000:
    raise SystemExit("Runtime IPA suspiciously small: not publishing")
feed = pathlib.Path(feedname)
source = json.loads(feed.read_text())
url = f"https://github.com/R347H4CK3R/madeira/releases/download/{tag}/{filename}"
version = {"version": f"0.2.{build}", "buildVersion": build,
           "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "localizedDescription": "Compiled Madeira Wine/FEX/Steam runtime candidate; Strata compatibility not yet device verified.",
           "downloadURL": url, "size": size, "minOSVersion": "17.0"}
app = {"name": "StrataForge Wine + Steam", "bundleIdentifier": "com.r347h4ck3r.madeira",
       "developerName": "R347H4CK3R", "subtitle": "Experimental Wine/FEX Windows game runtime",
       "localizedDescription": "Contains upstream Madeira Steam game-library/download integration; Steam login and Strata gameplay require real-device verification.",
       "versions": [version], "version": version["version"], "versionDate": version["date"],
       "downloadURL": url, "size": size, "iconURL": source.get("iconURL", "https://github.githubassets.com/favicons/favicon.png"),
       "tintColor": "4065B5", "category": "games", "appPermissions": {"entitlements": [], "privacy": {}}}
source["apps"] = [app] + [a for a in source.get("apps", []) if a.get("bundleIdentifier") != app["bundleIdentifier"]]
feed.write_text(json.dumps(source, indent=2) + "\n")
print("Published compiled runtime candidate", tag)
