"""
Discord interaction verification and HTTP response helpers.
Uses discord-interactions for verify_key and response-type enums; requests for follow-up PATCH.
"""
import os
from typing import Any, TypedDict

try:
    from discord_interactions import (
        verify_key as _verify_key_lib,
        InteractionType,
        InteractionResponseType,
        InteractionResponseFlags,
    )
    _HAS_DISCORD_INTERACTIONS = True
except ImportError:
    _HAS_DISCORD_INTERACTIONS = False
    InteractionType = None  # type: ignore
    InteractionResponseType = None  # type: ignore
    InteractionResponseFlags = None  # type: ignore


def verify_signature(body: bytes, signature: str, timestamp: str) -> bool:
    """Verify Discord interaction signature via discord-interactions or nacl fallback."""
    if not signature or not timestamp:
        print(f"[verify] fail: empty sig or ts sig_len={len(signature)} ts_len={len(timestamp)}")
        return False
    public_key = os.environ.get("DISCORD_PUBLIC_KEY", "").strip()
    if not public_key:
        print("[verify] fail: DISCORD_PUBLIC_KEY empty or unset")
        return False
    if _HAS_DISCORD_INTERACTIONS:
        try:
            return _verify_key_lib(body, signature, timestamp, public_key)
        except Exception as e:
            print(f"[verify] fail (discord_interactions): {e}")
            return False
    try:
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError
    except ImportError:
        print("[verify] fail: neither discord_interactions nor nacl available")
        return False
    try:
        vk = VerifyKey(bytes.fromhex(public_key))
        message = timestamp.encode("utf-8") + body
        vk.verify(message, bytes.fromhex(signature))
        return True
    except BadSignatureError:
        print("[verify] fail: BadSignatureError (sig invalid)")
        return False
    except (ValueError, TypeError) as e:
        print(f"[verify] fail: {e!r}")
        return False


def get_option(interaction_data: dict, name: str) -> Any:
    """Get option value from interaction data.options by name."""
    options = (interaction_data.get("data") or {}).get("options") or []
    for opt in options:
        if opt.get("name") == name:
            return opt.get("value")
    return None


def get_user(interaction: dict) -> dict:
    """Get user from interaction (member.user or user). Discord includes this in every interaction;
    we do not need the Server Members privileged intent."""
    member = interaction.get("member") or {}
    if member.get("user"):
        return member["user"]
    return interaction.get("user") or {}


def avatar_url(user: dict) -> str:
    """Discord CDN avatar URL for user."""
    uid = user.get("id", "")
    avatar = user.get("avatar")
    if avatar:
        ext = "gif" if avatar.startswith("a_") else "png"
        return f"https://cdn.discordapp.com/avatars/{uid}/{avatar}.{ext}"
    default = (int(uid) >> 22) % 6
    return f"https://cdn.discordapp.com/embed/avatars/{default}.png"


# Interaction type constants (for routing)
if _HAS_DISCORD_INTERACTIONS and InteractionType is not None:
    INTERACTION_PING = InteractionType.PING
    INTERACTION_APPLICATION_COMMAND = InteractionType.APPLICATION_COMMAND
    INTERACTION_MESSAGE_COMPONENT = InteractionType.MESSAGE_COMPONENT
else:
    INTERACTION_PING = 1
    INTERACTION_APPLICATION_COMMAND = 2
    INTERACTION_MESSAGE_COMPONENT = 3

# Response type constants (from discord_interactions or numeric fallback)
if _HAS_DISCORD_INTERACTIONS and InteractionResponseType is not None:
    PONG = InteractionResponseType.PONG
    CHANNEL_MESSAGE = InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE
    DEFERRED_CHANNEL_MESSAGE = InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE
    DEFERRED_UPDATE_MESSAGE = InteractionResponseType.DEFERRED_UPDATE_MESSAGE
    UPDATE_MESSAGE = InteractionResponseType.UPDATE_MESSAGE
else:
    PONG = 1
    CHANNEL_MESSAGE = 4
    DEFERRED_CHANNEL_MESSAGE = 5
    DEFERRED_UPDATE_MESSAGE = 6
    UPDATE_MESSAGE = 7


def response_pong() -> dict:
    return {"type": PONG}


def response_message(
    content: str | None = None,
    embeds: list[dict] | None = None,
    components: list[dict] | None = None,
) -> dict:
    """Response visible to everyone (flags=0, not ephemeral)."""
    data = {"allowed_mentions": {"parse": []}, "flags": 0}
    if content is not None:
        data["content"] = content
    if embeds:
        data["embeds"] = embeds
    if components:
        data["components"] = components
    return {"type": CHANNEL_MESSAGE, "data": data}


def response_deferred() -> dict:
    """Ack within 3s; real message sent via edit_followup (visible to everyone)."""
    return {"type": DEFERRED_CHANNEL_MESSAGE, "data": {"flags": 0}}


def response_update_message(
    embeds: list[dict] | None = None,
    components: list[dict] | None = None,
) -> dict:
    """Update message (e.g. pagination); visible to everyone."""
    data = {"flags": 0}
    if embeds:
        data["embeds"] = embeds
    if components:
        data["components"] = components
    return {"type": UPDATE_MESSAGE, "data": data}


class EditWebhookMessagePayload(TypedDict, total=False):
    """Payload for PATCH /webhooks/{id}/{token}/messages/@original (Edit Webhook Message)."""
    content: str
    embeds: list[dict]
    components: list[dict]
    flags: int
    allowed_mentions: dict


def _build_edit_payload(data_payload: dict) -> EditWebhookMessagePayload:
    """Build payload with only fields Discord accepts for Edit Webhook Message."""
    payload: EditWebhookMessagePayload = {
        "allowed_mentions": data_payload.get("allowed_mentions") or {"parse": []},
        "flags": 0,
    }
    if data_payload.get("content") is not None:
        payload["content"] = data_payload["content"]
    embeds = data_payload.get("embeds")
    if embeds and len(embeds) > 0:
        payload["embeds"] = embeds
    comps = data_payload.get("components")
    if comps and len(comps) > 0:
        payload["components"] = comps
    if "content" not in payload and "embeds" not in payload and "components" not in payload:
        payload["content"] = ""
    return payload


def edit_followup(
    application_id: str,
    token: str,
    data_payload: dict,
    *,
    thread_id: str | None = None,
) -> bool:
    """
    PATCH the original interaction response (after defer) with the real message.
    Uses requests; tries Bearer (interaction token) then Bot token.
    Pass thread_id when the interaction is in a thread (channel type 11 or 12).
    """
    import requests
    base = f"https://discord.com/api/v10/webhooks/{application_id}/{token}/messages/@original"
    params: dict[str, str | bool] = {}
    if thread_id:
        params["thread_id"] = thread_id
    if data_payload.get("components"):
        params["with_components"] = True
    payload = _build_edit_payload(data_payload)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (https://github.com/anglish-bot, 1.0)",
    }

    def do_request(auth_header: str) -> requests.Response:
        return requests.patch(
            base,
            params=params or None,
            json=payload,
            headers={**headers, "Authorization": auth_header},
            timeout=15,
        )

    try:
        r = do_request(f"Bearer {token}")
        if 200 <= r.status_code < 300:
            if r.text:
                print(f"[edit_followup] response body: {r.text[:500]}")
            return True
        if r.status_code == 403:
            print(f"[edit_followup] 403 body: {r.text[:800]}")
            bot_token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
            if bot_token:
                r2 = do_request(f"Bot {bot_token}")
                if 200 <= r2.status_code < 300:
                    if r2.text:
                        print(f"[edit_followup] response body: {r2.text[:500]}")
                    return True
                print(f"[edit_followup] Bot {r2.status_code}: {r2.text[:800]}")
            return False
        if r.status_code == 400:
            print(f"[edit_followup] 400 body: {r.text[:800]}")
        return False
    except Exception as e:
        print(f"[edit_followup] error: {e}")
        return False


def pagination_buttons(base_prefix: str, page: int, total_pages: int) -> list[dict]:
    """Build action row with First/Prev/Next/Last. base_prefix has no page (e.g. L:cmd:word:col or E:word:flags).
    Each custom_id is base:target_page:suffix so Discord sees unique ids and we still encode the target page."""
    first_page = 0
    last_page = max(0, total_pages - 1)
    prev_page = max(first_page, page - 1)
    next_page = min(last_page, page + 1)
    buttons = [
        {"type": 2, "style": 1, "label": "First", "custom_id": f"{base_prefix}:{first_page}:first", "disabled": page <= 0},
        {"type": 2, "style": 1, "label": "Prev", "custom_id": f"{base_prefix}:{prev_page}:prev", "disabled": page <= 0},
        {"type": 2, "style": 1, "label": "Next", "custom_id": f"{base_prefix}:{next_page}:next", "disabled": page >= last_page},
        {"type": 2, "style": 1, "label": "Last", "custom_id": f"{base_prefix}:{last_page}:last", "disabled": page >= last_page},
    ]
    return [{"type": 1, "components": buttons}]
