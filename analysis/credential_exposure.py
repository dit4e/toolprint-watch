#!/usr/bin/env python3
"""Finding: MCP servers authenticate at tools/call, not tools/list.

The watch configures credential-requiring servers with a PLACEHOLDER key
(servers.json: ${WATCH_PLACEHOLDER}, fc-…, xoxb-…). This reports how many of them
still served their full tools/list — i.e., handed over every tool name,
description and schema to a key that is not real.

    python3 analysis/credential_exposure.py [findings/<date>.json]
"""
import json, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def main():
    fpath = sys.argv[1] if len(sys.argv) > 1 else sorted(
        __import__("glob").glob(os.path.join(ROOT, "findings", "*.json")))[-1]
    d = json.load(open(fpath))
    cfg = json.load(open(os.path.join(ROOT, "servers.json")))["mcpServers"]
    needs_key = {n for n, c in cfg.items() if (c.get("env") or {})}
    served = []
    for s in d.get("servers", []):
        base = (s.get("name") or "").split("@")[0]
        if base in needs_key and s.get("fetch_status") == "ok" and (s.get("tool_count") or 0) > 0:
            served.append((base, s.get("tool_count")))
    print(f"source: {os.path.basename(fpath)}")
    print(f"credential-requiring servers: {len(needs_key)}")
    print(f"served full tools/list to a placeholder key: {len(served)}")
    for b, n in sorted(served): print(f"  {b:18} {n} tools")
if __name__ == "__main__":
    main()
