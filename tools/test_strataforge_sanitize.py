#!/usr/bin/env python3
"""Small dependency-free safety checks for sanitized StrataForge logs."""
import importlib.util
from pathlib import Path

module = Path(__file__).with_name("strataforge_sanitize.py")
spec = importlib.util.spec_from_file_location("strataforge_sanitize", module)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
source = "password=abc123 session_token=abcd access_token=secret SteamGuard=123456 user@example.com 192.168.1.4"
out = m.sanitize(source)
for item in ("abc123","session_token=abcd","access_token=secret","SteamGuard=123456","user@example.com","192.168.1.4"):
    assert item not in out, f"sensitive text leaked: {item}"
assert len(m.sanitize("A"*(100*1024))) <= m.MAX_OUTPUT
print("StrataForge log-redaction and size-cap checks passed")
