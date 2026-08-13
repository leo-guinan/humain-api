"""Durable resolver security state adapters.

SQLite is the local reference implementation. Production pilots should provide
an equivalent transactional PostgreSQL adapter.
"""
from __future__ import annotations

import json
import sqlite3
from threading import Lock
from typing import Any


class SQLiteStateStore:
    def __init__(self, path: str):
        self.path = path
        self._init_lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._init_lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS consumed_nonces (
                    requester TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    consumed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (requester, nonce)
                );
                CREATE TABLE IF NOT EXISTS revoked_capabilities (
                    capability_id TEXT PRIMARY KEY,
                    revoked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS resolution_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    requester TEXT NOT NULL,
                    audience TEXT NOT NULL,
                    pointer TEXT NOT NULL,
                    capability_ids TEXT NOT NULL,
                    resolution_state TEXT NOT NULL,
                    response_hash TEXT NOT NULL,
                    response_signature_ref TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    response_json TEXT NOT NULL
                );
                """
            )

    def consume_nonce(self, requester: str, nonce: str) -> bool:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO consumed_nonces(requester, nonce) VALUES (?, ?)",
                    (requester, nonce),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def revoke(self, capability_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO revoked_capabilities(capability_id) VALUES (?)",
                (capability_id,),
            )

    def is_revoked(self, capability_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM revoked_capabilities WHERE capability_id = ?",
                (capability_id,),
            ).fetchone()
        return row is not None

    def record_receipt(self, receipt: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO resolution_receipts
                (receipt_id, requester, audience, pointer, capability_ids,
                 resolution_state, response_hash, response_signature_ref,
                 created_at, response_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt["receipt_id"], receipt["requester"], receipt["audience"],
                    receipt["pointer"], json.dumps(receipt["capability_ids"], separators=(",", ":")),
                    receipt["resolution_state"], receipt["response_hash"],
                    receipt.get("response_signature_ref"), receipt["created_at"],
                    json.dumps(receipt["response"], sort_keys=True, separators=(",", ":")),
                ),
            )

    def receipts(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM resolution_receipts ORDER BY created_at, receipt_id"
            ).fetchall()
        return [
            {
                "receipt_id": row["receipt_id"], "requester": row["requester"],
                "audience": row["audience"], "pointer": row["pointer"],
                "capability_ids": json.loads(row["capability_ids"]),
                "resolution_state": row["resolution_state"],
                "response_hash": row["response_hash"],
                "response_signature_ref": row["response_signature_ref"],
                "created_at": row["created_at"],
                "response": json.loads(row["response_json"]),
            }
            for row in rows
        ]
