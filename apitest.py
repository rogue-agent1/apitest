#!/usr/bin/env python3
"""apitest - HTTP API test runner from YAML-like specs.

Define test suites, run assertions, report results. Zero dependencies.
"""

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
import time


def parse_spec(path):
    """Parse simple test spec format."""
    tests = []
    current = None
    with open(path) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.strip().startswith("#"):
                continue
            if line.startswith("---"):
                if current:
                    tests.append(current)
                current = {"name": "", "method": "GET", "url": "", "headers": {},
                           "body": None, "expect_status": 200, "expect_body": None,
                           "expect_contains": None, "expect_json": None}
                continue
            if not current:
                current = {"name": "", "method": "GET", "url": "", "headers": {},
                           "body": None, "expect_status": 200, "expect_body": None,
                           "expect_contains": None, "expect_json": None}
            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip()
            if key == "name":
                current["name"] = val
            elif key == "method":
                current["method"] = val.upper()
            elif key == "url":
                current["url"] = val
            elif key == "header":
                hk, _, hv = val.partition(":")
                current["headers"][hk.strip()] = hv.strip()
            elif key == "body":
                current["body"] = val
            elif key == "expect_status" or key == "status":
                current["expect_status"] = int(val)
            elif key == "expect_contains" or key == "contains":
                current["expect_contains"] = val
            elif key == "expect_json" or key == "json_path":
                current["expect_json"] = val
    if current:
        tests.append(current)
    return tests


def run_test(test, base_url="", verbose=False):
    url = (base_url.rstrip("/") + "/" + test["url"].lstrip("/")) if base_url and not test["url"].startswith("http") else test["url"]
    headers = test["headers"].copy()
    body = test["body"].encode() if test["body"] else None
    if body and "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=test["method"])
    errors = []
    start = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        status = resp.status
        resp_body = resp.read().decode()
    except urllib.error.HTTPError as e:
        status = e.code
        resp_body = e.read().decode()
    except Exception as e:
        return {"name": test["name"], "pass": False, "errors": [str(e)], "ms": 0}

    ms = (time.time() - start) * 1000

    if test["expect_status"] and status != test["expect_status"]:
        errors.append(f"status: expected {test['expect_status']}, got {status}")
    if test["expect_contains"] and test["expect_contains"] not in resp_body:
        errors.append(f"body missing: {test['expect_contains']!r}")
    if test["expect_json"]:
        try:
            path, _, expected = test["expect_json"].partition("=")
            data = json.loads(resp_body)
            val = data
            for key in path.strip().split("."):
                if key.isdigit():
                    val = val[int(key)]
                else:
                    val = val[key]
            if expected and str(val) != expected.strip():
                errors.append(f"json {path}: expected {expected.strip()!r}, got {str(val)!r}")
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
            errors.append(f"json path error: {e}")

    return {"name": test["name"], "pass": len(errors) == 0, "errors": errors,
            "ms": ms, "status": status}


def cmd_run(args):
    tests = parse_spec(args.spec)
    if not tests:
        print("No tests found")
        sys.exit(1)

    passed = failed = 0
    results = []
    for t in tests:
        result = run_test(t, base_url=args.base or "", verbose=args.verbose)
        results.append(result)
        icon = "✓" if result["pass"] else "✗"
        name = result["name"] or t["url"]
        print(f"  {icon} {name} ({result.get('status', '?')} {result['ms']:.0f}ms)")
        if not result["pass"]:
            for e in result["errors"]:
                print(f"      → {e}")
            failed += 1
        else:
            passed += 1

    print(f"\n  {passed} passed, {failed} failed, {len(tests)} total")
    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump(results, f, indent=2)
    if failed:
        sys.exit(1)


def cmd_init(args):
    sample = """# API Test Suite
---
name: Health check
method: GET
url: /api/health
status: 200
contains: ok

---
name: Create user
method: POST
url: /api/users
header: Content-Type: application/json
body: {"name": "Alice", "email": "alice@example.com"}
status: 201
json_path: name=Alice

---
name: Get users
method: GET
url: /api/users
status: 200
contains: Alice
"""
    out = args.output or "tests.api"
    with open(out, "w") as f:
        f.write(sample)
    print(f"Created: {out}")


def cmd_lint(args):
    tests = parse_spec(args.spec)
    issues = 0
    for i, t in enumerate(tests):
        name = t["name"] or f"test #{i+1}"
        if not t["url"]:
            print(f"  ⚠ {name}: missing URL")
            issues += 1
        if not t["expect_status"] and not t["expect_contains"] and not t["expect_json"]:
            print(f"  ⚠ {name}: no assertions")
            issues += 1
    if issues == 0:
        print(f"✓ {len(tests)} tests, no issues")
    else:
        print(f"\n{issues} issues in {len(tests)} tests")


def main():
    p = argparse.ArgumentParser(description="HTTP API test runner")
    sub = p.add_subparsers(dest="cmd")

    rp = sub.add_parser("run", help="Run test suite")
    rp.add_argument("spec", help="Test spec file")
    rp.add_argument("-b", "--base", help="Base URL")
    rp.add_argument("-v", "--verbose", action="store_true")
    rp.add_argument("-o", "--json-output", help="JSON results file")

    sub.add_parser("init", help="Create sample spec").add_argument("-o", "--output", default="tests.api")

    lp = sub.add_parser("lint", help="Validate test spec")
    lp.add_argument("spec")

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        sys.exit(1)
    {"run": cmd_run, "init": cmd_init, "lint": cmd_lint}[args.cmd](args)


if __name__ == "__main__":
    main()
