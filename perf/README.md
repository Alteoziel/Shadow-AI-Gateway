# Gateway load smoke (Locust)

```
pip install locust
export GATEWAY_API_KEY=test-gateway-key
locust -f perf/locustfile.py --host http://127.0.0.1:8000
```

Upstream will fail without real keys / mocking — health check is the reliable smoke; chat may 401/502 depending on env.
