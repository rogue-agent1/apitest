#!/usr/bin/env python3
"""apitest - HTTP API tester with assertions and test suites.

Single-file, zero-dependency CLI.
"""

import sys
import argparse
import json
import time
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


def make_request(method, url, headers=None, body=None, timeout=10):
    hdrs = {"User-Agent": "apitest/1.0"}
    if headers:
        for h in headers:
            k, v = h.split(":", 1)
            hdrs[k.strip()] = v.strip()
    data = body.encode() if body else None
    if data and "Content-Type" not in hdrs:
        hdrs["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=hdrs, method=method.upper())
    start = time.time()
    try:
        resp = urlopen(req, timeout=timeout)
        elapsed = (time.time() - start) * 1000
        body_bytes = resp.read()
        return {
            "status": resp.status, "headers": dict(resp.headers),
            "body": body_bytes.decode(errors="replace"), "time_ms": elapsed, "error": None
        }
    except HTTPError as e:
        elapsed = (time.time() - start) * 1000
        body_bytes = e.read() if hasattr(e, 'read') else b""
        return {
            "status": e.code, "headers": dict(e.headers),
            "body": body_bytes.decode(errors="replace"), "time_ms": elapsed, "error": None
        }
    except (URLError, OSError) as e:
        elapsed = (time.time() - start) * 1000
        return {"status": 0, "headers": {}, "body": "", "time_ms": elapsed, "error": str(e)}


def cmd_request(args):
    resp = make_request(args.method, args.url, args.header, args.data, args.timeout)
    if resp["error"]:
        print(f"  ✗ Error: {resp['error']}")
        return 1
    emoji = "✅" if 200 <= resp["status"] < 300 else "⚠️" if resp["status"] < 400 else "❌"
    print(f"  {emoji} {resp['status']} ({resp['time_ms']:.0f}ms)")
    if args.verbose:
        for k, v in resp["headers"].items():
            print(f"  {k}: {v}")
        print()
    if resp["body"]:
        try:
            parsed = json.loads(resp["body"])
            print(json.dumps(parsed, indent=2)[:2000])
        except json.JSONDecodeError:
            print(resp["body"][:500])
    # Assertions
    if args.status and resp["status"] != args.status:
        print(f"\n  ✗ ASSERT: expected status {args.status}, got {resp['status']}")
        return 1
    if args.contains and args.contains not in resp["body"]:
        print(f"\n  ✗ ASSERT: body missing '{args.contains}'")
        return 1
    if args.max_time and resp["time_ms"] > args.max_time:
        print(f"\n  ✗ ASSERT: too slow ({resp['time_ms']:.0f}ms > {args.max_time}ms)")
        return 1


def cmd_suite(args):
    """Run test suite from JSON file."""
    with open(args.file) as f:
        tests = json.load(f)
    passed, failed = 0, 0
    for test in tests:
        name = test.get("name", test["url"])
        resp = make_request(
            test.get("method", "GET"), test["url"],
            test.get("headers"), test.get("body"),
        )
        checks = []
        if "status" in test:
            checks.append(resp["status"] == test["status"])
        if "contains" in test:
            checks.append(test["contains"] in resp["body"])
        if "max_time" in test:
            checks.append(resp["time_ms"] <= test["max_time"])
        ok = all(checks) if checks else resp["error"] is None
        if ok:
            print(f"  ✅ {name} ({resp['status']}, {resp['time_ms']:.0f}ms)")
            passed += 1
        else:
            print(f"  ❌ {name} ({resp['status']}, {resp['time_ms']:.0f}ms)")
            failed += 1
    print(f"\n  {passed} passed, {failed} failed")
    return 1 if failed else 0


def cmd_health(args):
    """Quick health check on multiple URLs."""
    for url in args.urls:
        resp = make_request("GET", url, timeout=args.timeout)
        if resp["error"]:
            print(f"  💀 {url}: {resp['error']}")
        elif 200 <= resp["status"] < 300:
            print(f"  🟢 {url}: {resp['status']} ({resp['time_ms']:.0f}ms)")
        else:
            print(f"  🔴 {url}: {resp['status']} ({resp['time_ms']:.0f}ms)")


def main():
    p = argparse.ArgumentParser(prog="apitest", description="HTTP API tester")
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("request", aliases=["req", "r"], help="Make HTTP request")
    s.add_argument("method", choices=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
    s.add_argument("url"); s.add_argument("-H", "--header", action="append")
    s.add_argument("-d", "--data"); s.add_argument("-v", "--verbose", action="store_true")
    s.add_argument("-t", "--timeout", type=int, default=10)
    s.add_argument("--status", type=int); s.add_argument("--contains")
    s.add_argument("--max-time", type=float)
    s = sub.add_parser("suite", help="Run test suite from JSON")
    s.add_argument("file")
    s = sub.add_parser("health", aliases=["h"], help="Health check URLs")
    s.add_argument("urls", nargs="+"); s.add_argument("-t", "--timeout", type=int, default=5)
    args = p.parse_args()
    if not args.cmd: p.print_help(); return 1
    cmds = {"request": cmd_request, "req": cmd_request, "r": cmd_request,
            "suite": cmd_suite, "health": cmd_health, "h": cmd_health}
    return cmds[args.cmd](args) or 0


if __name__ == "__main__":
    sys.exit(main())
