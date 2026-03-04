"""
Lambda handler for Discord Interactions (slash commands + component buttons).
Receives POST from API Gateway, verifies Discord signature, routes by type and command.
"""
import json
import os

from discord_utils import (
    verify_signature,
    response_pong,
    get_user,
    avatar_url,
)
from sheet_loader import get_sheet
from commands.lookup import (
    handle_lookup_command,
    handle_pagination_component,
)
from commands.etymology import (
    handle_ety_command,
    handle_ety_pagination,
    parse_ety_custom_id,
)
from commands.help import handle_help_command

# Slash command names we handle
LOOKUP_NAMES = {"m", "match", "f", "find", "am", "amatch", "af", "anglish", "a", "em", "ematch", "ef", "english", "e"}


def _get_body(event: dict) -> bytes:
    """Raw body for signature verification. API Gateway HTTP API v2 passes body as string."""
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        import base64
        return base64.b64decode(body)
    return body.encode("utf-8") if isinstance(body, str) else body


def _route_app_command(interaction: dict) -> dict:
    """Handle type 2 APPLICATION_COMMAND. Returns response payload."""
    data = interaction.get("data", {})
    name = (data.get("name") or "").strip().lower()
    user = get_user(interaction)
    author_avatar = avatar_url(user)

    if name == "help":
        return handle_help_command()

    if name in LOOKUP_NAMES:
        sheet = get_sheet()
        return handle_lookup_command(interaction, sheet, name)

    if name in ("ety", "etymology"):
        return handle_ety_command(interaction, author_avatar)

    return {"type": 4, "data": {"content": f"Unknown command: {name}", "allowed_mentions": {"parse": []}}}


def _route_message_component(interaction: dict) -> dict | None:
    """Handle type 3 MESSAGE_COMPONENT (button click). Returns response or None."""
    data = interaction.get("data", {})
    custom_id = (data.get("custom_id") or "").strip()
    if not custom_id:
        return None
    user = get_user(interaction)
    author_avatar = avatar_url(user)

    if custom_id.startswith("L:"):
        sheet = get_sheet()
        return handle_pagination_component(interaction, sheet, custom_id)
    if custom_id.startswith("E:"):
        return handle_ety_pagination(custom_id, author_avatar)
    return None


def _normalize_headers(event: dict) -> dict:
    """API Gateway HTTP API may pass headers as dict (lowercase) or list of {name, value}."""
    headers = event.get("headers") or {}
    if isinstance(headers, list):
        return {h.get("name", "").lower(): (h.get("value") or "") for h in headers}
    return {k.lower(): (v if isinstance(v, str) else (v[0] if v else "")) for k, v in headers.items()}


def _response(status: int, body: str, content_type: str = "application/json") -> dict:
    return {"statusCode": status, "headers": {"Content-Type": content_type}, "body": body}


def handler(event: dict, context: object) -> dict:
    """
    Lambda entrypoint. Expects API Gateway HTTP API (or REST) POST with Discord interaction body.
    Returns response for API Gateway (statusCode + body).
    """
    headers = _normalize_headers(event)
    sig = headers.get("x-signature-ed25519", "")
    ts = headers.get("x-signature-timestamp", "")

    body_bytes = _get_body(event)
    # Skip signature verification when testing locally (LOCAL_TEST=1)
    if not os.environ.get("LOCAL_TEST"):
        # Debug: what we received (no raw body/sig in logs)
        is_b64 = event.get("isBase64Encoded", False)
        header_keys = list(headers.keys()) if isinstance(headers, dict) else []
        sig_keys = [k for k in header_keys if "signature" in k.lower()]
        print(f"[discord] body_len={len(body_bytes)} is_base64={is_b64} sig_len={len(sig)} ts_len={len(ts)} header_sig_keys={sig_keys}")
        ok = verify_signature(body_bytes, sig, ts)
        print(f"[discord] verify_ok={ok}")
        if not ok:
            return _response(401, "")

    try:
        body = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        return _response(400, "")

    interaction_type = body.get("type")

    if interaction_type == 1:
        return _response(200, json.dumps(response_pong()))

    if interaction_type == 2:
        payload = _route_app_command(body)
        return _response(200, json.dumps(payload))

    if interaction_type == 3:
        payload = _route_message_component(body)
        if payload is not None:
            return _response(200, json.dumps(payload))
        return _response(200, json.dumps({"type": 4, "data": {"content": "Unknown component.", "allowed_mentions": {"parse": []}}}))

    return _response(200, json.dumps({"type": 4, "data": {"content": "Unhandled interaction type.", "allowed_mentions": {"parse": []}}}))
