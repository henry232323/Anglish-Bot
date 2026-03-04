"""
Discord interaction verification and HTTP response helpers.
Verifies X-Signature-Ed25519 using the application's public key.
"""
import json
import os
from typing import Any

# Signature verification (ed25519) - matches Discord docs exactly
try:
    from nacl.signing import VerifyKey
    from nacl.exceptions import BadSignatureError
    HAS_NACL = True
except ImportError:
    HAS_NACL = False
    BadSignatureError = Exception  # noqa: A001


def verify_signature(body: bytes, signature: str, timestamp: str) -> bool:
    """Verify Discord interaction signature. Message = (timestamp + body).encode() per Discord docs."""
    if not HAS_NACL:
        print("[verify] fail: HAS_NACL=False (nacl not installed)")
        return False
    if not signature or not timestamp:
        print(f"[verify] fail: empty sig or ts sig_len={len(signature)} ts_len={len(timestamp)}")
        return False
    public_key = os.environ.get("DISCORD_PUBLIC_KEY", "").strip()
    if not public_key:
        print("[verify] fail: DISCORD_PUBLIC_KEY empty or unset")
        return False
    try:
        verify_key = VerifyKey(bytes.fromhex(public_key))
        body_str = body.decode("utf-8")
        message = f"{timestamp}{body_str}".encode("utf-8")
        sig_bytes = bytes.fromhex(signature)
        verify_key.verify(message, sig_bytes)
        return True
    except BadSignatureError:
        print(f"[verify] fail: BadSignatureError (sig invalid) body_len={len(body)} ts_len={len(timestamp)} msg_len={len(message)} key_len={len(public_key)}")
        return False
    except ValueError as e:
        print(f"[verify] fail: ValueError {e!r} sig_len={len(signature)} sig_hex_ok={all(c in '0123456789abcdefABCDEF' for c in signature)}")
        return False
    except TypeError as e:
        print(f"[verify] fail: TypeError {e!r}")
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


# Response type constants
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
    data = {"allowed_mentions": {"parse": []}}
    if content is not None:
        data["content"] = content
    if embeds:
        data["embeds"] = embeds
    if components:
        data["components"] = components
    return {"type": CHANNEL_MESSAGE, "data": data}


def response_deferred() -> dict:
    return {"type": DEFERRED_CHANNEL_MESSAGE, "data": {"flags": 0}}


def response_update_message(
    embeds: list[dict] | None = None,
    components: list[dict] | None = None,
) -> dict:
    data = {}
    if embeds:
        data["embeds"] = embeds
    if components:
        data["components"] = components
    return {"type": UPDATE_MESSAGE, "data": data}


def pagination_buttons(custom_id_prefix: str, page: int, total_pages: int) -> list[dict]:
    """Build action row with prev/next (and first/last if needed). custom_id max 100 chars."""
    buttons = []
    # First
    buttons.append({
        "type": 2,
        "style": 1,
        "label": "First",
        "custom_id": f"{custom_id_prefix}:0",
        "disabled": page <= 0,
    })
    # Prev
    buttons.append({
        "type": 2,
        "style": 1,
        "label": "Prev",
        "custom_id": f"{custom_id_prefix}:{max(0, page - 1)}",
        "disabled": page <= 0,
    })
    # Next
    buttons.append({
        "type": 2,
        "style": 1,
        "label": "Next",
        "custom_id": f"{custom_id_prefix}:{min(total_pages - 1, page + 1)}",
        "disabled": page >= total_pages - 1,
    })
    # Last
    buttons.append({
        "type": 2,
        "style": 1,
        "label": "Last",
        "custom_id": f"{custom_id_prefix}:{total_pages - 1}",
        "disabled": page >= total_pages - 1,
    })
    return [{"type": 1, "components": buttons}]
