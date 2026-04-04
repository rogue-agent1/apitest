# apitest

HTTP API test runner from simple spec files.

## Usage

```bash
python3 apitest.py init                         # create sample spec
python3 apitest.py run tests.api -b http://localhost:8080
python3 apitest.py run tests.api -o results.json
python3 apitest.py lint tests.api
```

## Spec Format

```
---
name: Get users
method: GET
url: /api/users
header: Authorization: Bearer token123
status: 200
contains: Alice
json_path: 0.name=Alice
```

## Features

- Simple text spec format (no YAML dependency)
- Status code, body content, and JSON path assertions
- Custom headers and request bodies
- Base URL support
- Response timing
- JSON results export
- Spec linting
- Zero dependencies
