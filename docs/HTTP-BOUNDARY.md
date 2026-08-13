# HTTP boundary

The resolver transport now exposes a small, explicit application boundary:

- `GET /healthz` reports process liveness only;
- `GET /readyz` reports resolver readiness and production signing configuration;
- `POST /v1/resolve` enforces `Content-Length`, a configurable body limit, and a standard request ID;
- every response includes `X-Request-ID`;
- errors contain a stable error class and request ID, never the request body.

```python
server = make_server(
    "127.0.0.1", 8787, resolver, projections,
    max_body_bytes=1_048_576,
)
```

This is the application-layer contract. It is not a claim that `ThreadingHTTPServer` is the final public deployment. The private pilot still needs a maintained process server, loopback binding behind TLS termination, request/header timeout limits, rate limiting, graceful draining, structured redacted access logs, and health-gated deployment.

`/healthz` must remain cheap and independent of database readiness. `/readyz` is the gate a deployment should use before accepting traffic; it must eventually include PostgreSQL, key registry, and issuer freshness checks when those adapters exist.
