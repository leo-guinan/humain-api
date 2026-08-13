# Durable resolver state

Status: local reference adapter, 2026-08-12. PostgreSQL remains required for the private pilot.

`SQLiteStateStore` provides the smallest executable proof that security state does not disappear when the resolver process restarts:

- `(requester, nonce)` is a unique durable key;
- revocations survive resolver replacement;
- resolution receipts are append-only rows containing response hashes and signed response references;
- SQLite's uniqueness constraint arbitrates concurrent duplicate requests.

```python
from humain_api import SQLiteStateStore, Resolver

store = SQLiteStateStore("/tmp/humain-state.sqlite")
resolver = Resolver(..., state_store=store)
```

The resolver uses the store when supplied. Without it, the existing in-process reference behavior remains available for old fixtures and local examples.

## Production boundary

This adapter is deliberately not called a production database layer. The pilot still requires a PostgreSQL implementation with:

- transactionally consumed nonces and a unique `(requester, nonce)` constraint;
- durable capability revocations and key-status records;
- durable sessions, projections, and receipts;
- connection pooling, migrations, encrypted backups, and restore evidence;
- read-after-write behavior across resolver instances.

Redis may accelerate bounded TTL/idempotency checks, but it cannot be the only receipt or revocation store. A dictionary that survives only until the next process restart is not durable state; it is a temporary opinion.
