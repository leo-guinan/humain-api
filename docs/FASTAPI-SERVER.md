# Maintained resolver server

The maintained adapter is `humain_api.fastapi_service:create_app`, served by uvicorn through `run_fastapi.py`.

```bash
HUMAIN_RESOLVER_MODE=production \
HUMAIN_PUBLISHER_KEY_REF=did:key:publisher \
HUMAIN_PUBLISHER_PRIVATE_KEY_B64='[secret from a mode-600 file]' \
HUMAIN_AGENT_KEY_REF=did:key:agent \
HUMAIN_AGENT_PUBLIC_KEY_B64='[public key]' \
HUMAIN_STATE_PATH=/var/lib/humain-api/state.sqlite \
uvicorn run_fastapi:app --host 127.0.0.1 --port 8787 --workers 2 --timeout-keep-alive 5
```

Production mode fails closed when signing or verification configuration is absent. The systemd unit in `deploy/humain-resolver.service` binds only to loopback, runs as a non-root service account, restarts on failure, and protects the filesystem. It is a deployment template, not a deployment receipt; the host still needs a real user, secret file, TLS proxy, migration/backup process, and health-gated cutover.

The FastAPI adapter preserves the core resolver's transport-neutral API and exposes `/healthz`, `/readyz`, and `/v1/resolve`. The older `ThreadingHTTPServer` adapter remains available for reference fixtures.
