#!/usr/bin/env python3
"""Sanitize and bound crash telemetry BEFORE any repository upload.

Fails closed on secrets; never sends data itself. Accepts UTF-8 log input.
"""
import argparse
import json
from pathlib import Path
import re
import sys

MAX_INPUT = 2 * 1024 * 1024
MAX_OUTPUT = 48 * 1024
PATTERNS = [
    (re.compile(r"(?i)\b(authorization\s*[:=]\s*(?:bearer|basic)\s+)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\b((?:access_token|refresh_token|session_token|password|passwd|secret|cookie|set-cookie|steamguard|steam_guard)\s*[:=]\s*)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\b(gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]+)\b"), "[REDACTED_TOKEN]"),
    (re.compile(r"(?i)(?:[A-Z]:\\\\Users\\\\|/Users/|/home/)[^/\\\\\s]+"), "[USER_HOME]"),
    (re.compile(r"(?i)\b([\w.+-]+@[\w.-]+\.[A-Z]{2,})\b"), "[EMAIL]"),
    (re.compile(r"(?i)\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP_ADDRESS]"),
]
def sanitize(raw: str) -> str:
    for pattern, replacement in PATTERNS:
        raw = pattern.sub(replacement, raw)
    return raw[-MAX_OUTPUT:]

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args=p.parse_args()
    if args.input.stat().st_size > MAX_INPUT:
        print("Input exceeds 2 MiB cap; refuse unbounded file",file=sys.stderr)
        return 2
    cleaned=sanitize(args.input.read_text(encoding="utf-8",errors="replace"))
    report={"schema":1,"kind":"strataforge-redacted-diagnostics","byteLimit":MAX_OUTPUT,
            "log":cleaned,"warning":"Manual privacy review still required before upload."}
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(f"Sanitized report written: {args.output} ({args.output.stat().st_size} bytes)")
    return 0
if __name__=="__main__":raise SystemExit(main())
