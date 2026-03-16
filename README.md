# apitest
API endpoint test runner with assertions, variable extraction, and chaining.
```json
{"base_url": "https://api.example.com", "tests": [
  {"name": "Get users", "method": "GET", "path": "/users", "expect": {"status": 200}},
  {"name": "Create user", "method": "POST", "path": "/users", "body": {"name": "test"},
   "expect": {"status": 201, "json": {"name": "test"}}, "extract": {"user_id": "id"}}
]}
```
```bash
python apitest.py tests.json -v
```
## Zero dependencies. Python 3.6+.
