#!/usr/bin/env python3
"""apitest - API endpoint test runner from JSON specs."""
import urllib.request, urllib.error, json, argparse, sys, time, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def run_test(test, base_url='', variables=None):
    variables = variables or {}
    url = base_url + test['path']
    for k, v in variables.items():
        url = url.replace(f'{{{k}}}', str(v))
    
    method = test.get('method', 'GET')
    headers = test.get('headers', {})
    body = test.get('body')
    if body and isinstance(body, (dict, list)):
        body = json.dumps(body).encode()
        headers.setdefault('Content-Type', 'application/json')
    elif body:
        body = body.encode()
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=test.get('timeout', 10), context=ctx) as r:
            resp_body = r.read().decode(errors='replace')
            elapsed = (time.time() - start) * 1000
            status = r.status
            resp_headers = dict(r.headers)
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode(errors='replace')
        elapsed = (time.time() - start) * 1000
        status = e.code
        resp_headers = dict(e.headers)
    except Exception as e:
        return {'name': test.get('name', url), 'pass': False, 'error': str(e), 'ms': 0}
    
    # Assertions
    errors = []
    expect = test.get('expect', {})
    if 'status' in expect and status != expect['status']:
        errors.append(f"status: got {status}, expected {expect['status']}")
    if 'body_contains' in expect and expect['body_contains'] not in resp_body:
        errors.append(f"body missing: {expect['body_contains'][:50]}")
    if 'json' in expect:
        try:
            resp_json = json.loads(resp_body)
            for k, v in expect['json'].items():
                if resp_json.get(k) != v:
                    errors.append(f"json.{k}: got {resp_json.get(k)!r}, expected {v!r}")
        except: errors.append("response is not valid JSON")
    if 'max_ms' in expect and elapsed > expect['max_ms']:
        errors.append(f"too slow: {elapsed:.0f}ms > {expect['max_ms']}ms")
    
    # Extract variables
    extracts = {}
    if 'extract' in test:
        try:
            resp_json = json.loads(resp_body)
            for var, path in test['extract'].items():
                extracts[var] = resp_json.get(path, '')
        except: pass
    
    return {
        'name': test.get('name', f'{method} {test["path"]}'),
        'pass': len(errors) == 0, 'status': status, 'ms': elapsed,
        'errors': errors, 'extracts': extracts
    }

def main():
    p = argparse.ArgumentParser(description='API test runner')
    p.add_argument('config', help='JSON test config')
    p.add_argument('-b', '--base-url', default='')
    p.add_argument('-v', '--verbose', action='store_true')
    p.add_argument('--stop-on-fail', action='store_true')
    args = p.parse_args()

    with open(args.config) as f: config = json.load(f)
    tests = config if isinstance(config, list) else config.get('tests', [])
    base = args.base_url or (config.get('base_url', '') if isinstance(config, dict) else '')
    
    variables = config.get('variables', {}) if isinstance(config, dict) else {}
    passed = failed = 0
    
    print(f"Running {len(tests)} tests against {base or '(inline URLs)'}\n")
    for test in tests:
        result = run_test(test, base, variables)
        variables.update(result.get('extracts', {}))
        
        icon = '✓' if result['pass'] else '✗'
        status = result.get('status', 'ERR')
        print(f"  {icon} {result['name']:<40} {status} {result['ms']:.0f}ms")
        
        if not result['pass']:
            failed += 1
            for err in result.get('errors', []):
                print(f"    → {err}")
            if result.get('error'):
                print(f"    → {result['error']}")
            if args.stop_on_fail: break
        else:
            passed += 1
    
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)

if __name__ == '__main__':
    main()
