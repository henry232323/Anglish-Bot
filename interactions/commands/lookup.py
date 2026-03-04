"""
Lookup commands: match, find, amatch, anglish, ematch, english.
Uses shared sheet instance; returns list of embed dicts for pagination.

Pagination is stateless: each button encodes L:cmd:word:col:page in custom_id.
Clicking a button sends a new interaction; we re-run lookup and return UPDATE_MESSAGE
with that page. No server-side session.
"""
import re
from typing import Any

from discord_utils import pagination_buttons

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
HEADERS = ["Word", "Unswayed", "Meaning", "Kind", "Forebear", "Whence", "🔨", "Notes", "Who?", "Source"]
FURL = "https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?gid=0&range={}{}"
HELP_FIELD = "Use /help for command usage. If the bot is typing it is still generating new results."


def _format_row(sheet, cell, word: str, author_avatar: str) -> dict:
    """Build embed dict for one row. sheet is gspread Worksheet."""
    title_cell = sheet.cell(cell.row, 1)
    title = title_cell.value
    url = FURL.format(LETTERS[cell.col - 1], cell.row)
    row_vals = sheet.row_values(cell.row)
    fields = []
    for header, val in zip(HEADERS, row_vals):
        if header == "🔨":
            value = str(bool(val))
        else:
            value = val
        if value:
            fields.append({"name": header, "value": str(value)[:1024]})
    fields.append({"name": "Help", "value": HELP_FIELD})
    return {
        "color": 0xDD0000,
        "title": title,
        "url": url,
        "author": {"name": word, "icon_url": author_avatar},
        "fields": fields,
    }


def _findall_cells(sheet, regex_pattern: str, col: int | None = None) -> list:
    """Find all cells matching regex. col 1-based or None for any."""
    rex = re.compile(regex_pattern, re.IGNORECASE)
    cells = sheet.findall(rex)
    if col is not None:
        cells = [c for c in cells if c.col == col]
    return [c for c in cells if c.row != 1]


def run_lookup(sheet, word: str, hard: bool, col: int | None, author_avatar: str) -> list[dict]:
    """Run lookup and return list of embed dicts. sheet is gspread Worksheet."""
    if sheet is None:
        return []
    regex = rf"\b({re.escape(word)})\b" if hard else rf"({re.escape(word)})"
    cells = _findall_cells(sheet, regex, col=col)
    # Dedupe by row (one embed per row)
    seen = set()
    unique = []
    for c in cells:
        if c.row not in seen:
            seen.add(c.row)
            unique.append(c)
    embeds = []
    for cell in unique:
        embeds.append(_format_row(sheet, cell, word, author_avatar))
    return embeds


# custom_id format for pagination: "L:{cmd}:{word}:{col}:{page}" (col can be "" for None)
def parse_pagination_custom_id(custom_id: str) -> dict | None:
    """Parse custom_id like L:m:brook:1:2 -> {cmd, word, col, page}."""
    parts = custom_id.split(":")
    if len(parts) < 5 or parts[0] != "L":
        return None
    cmd, word, col_str, page_str = parts[1], parts[2], parts[3], parts[4]
    col = int(col_str) if col_str else None
    page = int(page_str)
    return {"cmd": cmd, "word": word, "col": col, "page": page}


def build_pagination_custom_id(cmd: str, word: str, col: int | None, page: int) -> str:
    # Discord custom_id max 100 chars; keep word under 40
    w = (word or "")[:40]
    return f"L:{cmd}:{w}:{col or ''}:{page}"


def handle_lookup_command(
    interaction: dict,
    sheet: Any,
    cmd_name: str,
) -> dict:
    """
    Handle /m, /f, /am, /af, /em, /ef.
    Returns response dict: either deferred (then caller sends follow-up) or direct message.
    """
    from discord_utils import get_user, avatar_url, response_message

    data = interaction.get("data", {})
    options = {o["name"]: o.get("value") for o in data.get("options", [])}
    word = (options.get("word") or "").strip()
    if not word:
        return response_message(content="Please provide a word.")

    user = get_user(interaction)
    author_avatar = avatar_url(user)

    # Map slash command name to (hard, col)
    # m=hard all, f=soft all, am=hard col1, af=soft col1, em=hard col3, ef=soft col3
    lookup_params = {
        "m": (True, None),
        "match": (True, None),
        "f": (False, None),
        "find": (False, None),
        "am": (True, 1),
        "amatch": (True, 1),
        "af": (False, 1),
        "anglish": (False, 1),
        "a": (False, 1),
        "em": (True, 3),
        "ematch": (True, 3),
        "ef": (False, 3),
        "english": (False, 3),
        "e": (False, 3),
    }
    hard, col = lookup_params.get(cmd_name, (True, None))
    embeds = run_lookup(sheet, word, hard=hard, col=col, author_avatar=author_avatar)

    if not embeds:
        return response_message(content="Query not found!")

    # Add footer with page info
    total = len(embeds)
    for i, emb in enumerate(embeds):
        emb.setdefault("footer", {})["text"] = f"({i + 1}/{total})"

    if total == 1:
        return response_message(embeds=[embeds[0]])

    base = build_pagination_custom_id(cmd_name, word, col, 0).rsplit(":", 1)[0]
    components = pagination_buttons(base, 0, total)
    return response_message(embeds=[embeds[0]], components=components)


def handle_pagination_component(
    interaction: dict,
    sheet: Any,
    custom_id: str,
) -> dict | None:
    """Handle button click for lookup pagination. Returns UPDATE_MESSAGE response or None."""
    from discord_utils import get_user, avatar_url, response_update_message

    parsed = parse_pagination_custom_id(custom_id)
    if not parsed:
        return None
    user = get_user(interaction)
    author_avatar = avatar_url(user)
    embeds = run_lookup(
        sheet,
        parsed["word"],
        hard=parsed["cmd"] in ("m", "match", "am", "amatch", "em", "ematch"),
        col=parsed["col"],
        author_avatar=author_avatar,
    )
    total = len(embeds)
    page = max(0, min(parsed["page"], total - 1))
    emb = embeds[page]
    emb.setdefault("footer", {})["text"] = f"({page + 1}/{total})"
    base = build_pagination_custom_id(parsed["cmd"], parsed["word"], parsed["col"], page).rsplit(":", 1)[0]
    components = pagination_buttons(base, page, total)
    return response_update_message(embeds=[emb], components=components)
