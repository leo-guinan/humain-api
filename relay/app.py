"""Low-value HumAIn rendezvous relay.

This service is authoritative for short-lived rendezvous state. It is not a
proxy and does not hold an OpenHome API key or private signing key.
"""
from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from humain_api.rendezvous import Participant, RendezvousBroker

app = FastAPI(title="HumAIn Rendezvous Relay", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://story.markets", "https://www.story.markets"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

BROKER = RendezvousBroker(require_observation=True)


def _openhome() -> Participant | None:
    key_ref = os.environ.get("RELAY_OPENHOME_KEY_REF", "")
    public_key = os.environ.get("RELAY_OPENHOME_PUBLIC_KEY_B64", "")
    if not key_ref or not public_key:
        return None
    return Participant(role="openhome", key_ref=key_ref, public_key_b64=public_key)


def _authorized(request: Request) -> bool:
    expected = os.environ.get("RELAY_DEVKIT_TOKEN", "")
    supplied = request.headers.get("authorization", "")
    return bool(expected) and hmac.compare_digest(supplied, "Bearer " + expected)


def _error(status: int, code: str, message: str):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message[:200]}})


async def _body(request: Request) -> dict[str, Any]:
    value = await request.json()
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


@app.get("/health")
def health():
    return {"ok": True, "service": "humain-rendezvous-relay", "openhome_identity_configured": _openhome() is not None, "private_context": False}


@app.post("/v1/rendezvous/start")
async def start(request: Request):
    try:
        openhome = _openhome()
        if openhome is None:
            return _error(503, "rendezvous_not_configured", "OpenHome public identity is not provisioned")
        data = await _body(request)
        browser_data = data.get("browser") if isinstance(data.get("browser"), dict) else data
        browser_data = browser_data or {}
        browser_key_ref = browser_data.get("key_ref", data.get("browser_key_ref", ""))
        browser_public_key = browser_data.get("public_key_b64", data.get("browser_public_key_b64", ""))
        browser = Participant(role="browser", key_ref=str(browser_key_ref), public_key_b64=str(browser_public_key))
        if not browser.key_ref or not browser.public_key_b64:
            return _error(400, "browser_identity_required", "browser public identity is required")
        return BROKER.start(origin=str(data.get("origin", "")), pathname=str(data.get("pathname", "")), event_id=str(data.get("event_id", "")), browser=browser, openhome=openhome)
    except (ValueError, KeyError) as exc:
        return _error(400, "invalid_rendezvous", str(exc))
    except Exception as exc:
        return _error(500, "relay_error", str(exc))


@app.post("/v1/rendezvous/pending")
async def pending(request: Request):
    if not _authorized(request):
        return _error(401, "unauthorized", "DevKit relay authorization required")
    try:
        data = await _body(request)
        return {"schema": "humain.rendezvous.pending.v1", "rendezvous": BROKER.pending_for_openhome(str(data.get("key_ref", "")))}
    except Exception as exc:
        return _error(400, "invalid_pending_request", str(exc))


@app.post("/v1/rendezvous/observation")
async def observation(request: Request):
    if not _authorized(request):
        return _error(401, "unauthorized", "DevKit relay authorization required")
    try:
        data = await _body(request)
        return BROKER.submit_observation(rendezvous_id=str(data.get("rendezvous_id", "")), scanner=str(data.get("scanner", "")), observed_at=str(data.get("observed_at", "")), service_uuid=str(data.get("service_uuid", "")), advertisement_commitment=str(data.get("advertisement_commitment", "")), commitment_quality=str(data.get("commitment_quality", "payload")), rssi_bucket=data.get("rssi_bucket"), sample_count=int(data.get("sample_count", 1)))
    except PermissionError as exc:
        return _error(403, "observation_rejected", str(exc))
    except (ValueError, KeyError) as exc:
        return _error(400, "invalid_observation", str(exc))


@app.post("/v1/rendezvous/claim")
async def claim(request: Request):
    return await _signed_action(request, "claim")


@app.post("/v1/rendezvous/ping")
async def ping(request: Request):
    try:
        data = await _body(request)
        return BROKER.issue_ping(str(data.get("rendezvous_id", "")))
    except Exception as exc:
        return _error(403, "ping_rejected", str(exc))


@app.post("/v1/rendezvous/answer-ping")
async def answer_ping(request: Request):
    return await _signed_action(request, "answer-ping")


@app.post("/v1/rendezvous/receipt")
async def receipt(request: Request):
    return await _signed_action(request, "receipt")


@app.post("/v1/rendezvous/bind")
async def bind(request: Request):
    try:
        data = await _body(request)
        return BROKER.bind(rendezvous_id=str(data.get("rendezvous_id", "")), binding_code=str(data.get("binding_code", "")))
    except Exception as exc:
        return _error(403, "binding_rejected", str(exc))


@app.post("/v1/rendezvous/grant")
async def grant(request: Request):
    try:
        data = await _body(request)
        return BROKER.issue_grant(str(data.get("rendezvous_id", "")))
    except Exception as exc:
        return _error(403, "grant_rejected", str(exc))


async def _signed_action(request: Request, action: str):
    try:
        data = await _body(request)
        if action == "claim":
            return BROKER.submit_claim(rendezvous_id=str(data.get("rendezvous_id", "")), role=str(data.get("role", "")), nonce=str(data.get("nonce", "")), signature=data.get("signature") or {}, observed_at=str(data.get("observed_at", "")))
        if action == "answer-ping":
            return BROKER.answer_ping(rendezvous_id=str(data.get("rendezvous_id", "")), role=str(data.get("role", "")), ping_id=str(data.get("ping_id", "")), nonce=str(data.get("nonce", "")), signature=data.get("signature") or {}, observed_at=str(data.get("observed_at", "")))
        return BROKER.submit_shared_receipt(rendezvous_id=str(data.get("rendezvous_id", "")), role=str(data.get("role", "")), receipt_hash=str(data.get("receipt_hash", "")), signature=data.get("signature") or {})
    except Exception as exc:
        return _error(403, "signed_action_rejected", str(exc))
