"""
Lambda handler for Discord Interactions (slash commands + component buttons).
Receives POST from API Gateway, verifies Discord signature, routes by type and command.

Pagination is stateless: page index (and word, command, col) are encoded in button custom_id
(e.g. L:m:word:col:page). Each button click is a new request; we re-run lookup and return
UPDATE_MESSAGE with the chosen page. No server-side session required.
"""
import json
import os

from discord_utils import (
    verify_signature,
    response_pong,
    response_deferred,
    get_user,
    avatar_url,
    edit_followup,
    INTERACTION_PING,
    INTERACTION_APPLICATION_COMMAND,
    INTERACTION_MESSAGE_COMPONENT,
    CHANNEL_MESSAGE,
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

    return {"type": CHANNEL_MESSAGE, "data": {"content": f"Unknown command: {name}", "allowed_mentions": {"parse": []}}}


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


def _handle_follow_up(interaction: dict) -> dict:
    """Async path: do the work and PATCH the deferred message with the result."""
    payload = _route_app_command(interaction)
    if payload.get("type") == CHANNEL_MESSAGE and "data" in payload:
        app_id = str(interaction.get("application_id", ""))
        token = (interaction.get("token") or "").strip()
        if app_id and token:
            channel = interaction.get("channel") or {}
            ch_type = channel.get("type")
            thread_id = str(interaction["channel_id"]) if ch_type in (11, 12) else None
            edit_followup(app_id, token, payload["data"], thread_id=thread_id)
    return _response(200, "{}")


def _invoke_follow_up(context: object, interaction: dict) -> None:
    """Invoke this Lambda asynchronously to do the work and send follow-up (edit deferred message)."""
    try:
        import boto3
        fn = getattr(context, "function_name", None) or os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "")
        if not fn:
            return
        boto3.client("lambda").invoke(
            FunctionName=fn,
            InvocationType="Event",
            Payload=json.dumps({"follow_up": True, "interaction": interaction}),
        )
    except Exception as e:
        print(f"[invoke_follow_up] {e}")


def handler(event: dict, context: object) -> dict:
    """
    Lambda entrypoint. Expects API Gateway HTTP API (or REST) POST with Discord interaction body.
    Returns response for API Gateway (statusCode + body).
    """
    # Async follow-up: we invoked ourselves after returning deferred; do the work and edit the message
    if event.get("follow_up") and "interaction" in event:
        return _handle_follow_up(event["interaction"])

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

    if interaction_type == INTERACTION_PING:
        return _response(200, json.dumps(response_pong()))

    if interaction_type == INTERACTION_APPLICATION_COMMAND:
        data = body.get("data") or {}
        name = (data.get("name") or "").strip().lower()
        # Lookup and ety: defer (<3s) then async invoke does work and PATCH follow-up (needs DISCORD_BOT_TOKEN)
        if (name in LOOKUP_NAMES or name in ("ety", "etymology")) and os.environ.get("DISCORD_BOT_TOKEN", "").strip():
            _invoke_follow_up(context, body)
            return _response(200, json.dumps(response_deferred()))
        payload = _route_app_command(body)
        return _response(200, json.dumps(payload))

    if interaction_type == INTERACTION_MESSAGE_COMPONENT:
        payload = _route_message_component(body)
        if payload is not None:
            return _response(200, json.dumps(payload))
        return _response(200, json.dumps({"type": CHANNEL_MESSAGE, "data": {"content": "Unknown component.", "allowed_mentions": {"parse": []}}}))

    return _response(200, json.dumps({"type": CHANNEL_MESSAGE, "data": {"content": "Unhandled interaction type.", "allowed_mentions": {"parse": []}}}))
