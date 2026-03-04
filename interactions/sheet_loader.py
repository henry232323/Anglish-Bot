"""
Load Google Sheet once per Lambda instance (reused across invocations).
Credentials only from GOOGLE_CREDENTIALS_JSON env (JSON, base64-encoded JSON, or single-line JSON).
Sheet data is cached in memory (one bulk read per container) to avoid Sheets API quota (429).
"""
import base64
import json
import os
import re

_sheet = None
_workbook = None
_cached_grid = None  # list[list[str]]: rows from get_all_values(), 0-based


class _CachedCell:
    def __init__(self, row: int, col: int, value: str):
        self.row = row
        self.col = col
        self.value = value or ""


def _load_creds_dict() -> dict | None:
    """Load credentials from GOOGLE_CREDENTIALS_JSON env only. Returns dict or None if unset."""
    creds_raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
    if not creds_raw:
        return None
    try:
        creds_json = base64.b64decode(creds_raw).decode("utf-8")
    except Exception:
        creds_json = creds_raw
    creds_dict = None
    try:
        creds_dict = json.loads(creds_json)
    except json.JSONDecodeError as e:
        if "control character" in str(e).lower():
            try:
                normalized = creds_json.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")
                creds_dict = json.loads(normalized)
            except json.JSONDecodeError:
                pass
        if creds_dict is None:
            try:
                import ast
                creds_dict = ast.literal_eval(creds_json)
            except (ValueError, SyntaxError):
                raise ValueError(
                    "GOOGLE_CREDENTIALS_JSON is not valid JSON (and not valid base64). "
                    "Use single-line JSON with \\n in private_key, or base64-encode the JSON."
                ) from None
    if isinstance(creds_dict, str):
        creds_dict = json.loads(creds_dict)
    if not isinstance(creds_dict, dict):
        raise ValueError("GOOGLE_CREDENTIALS_JSON must be a JSON object (dict).")
    return creds_dict


def _ensure_grid():
    """Fetch full sheet once and cache. _sheet and _cached_grid must be set together."""
    global _sheet, _workbook, _cached_grid
    if _cached_grid is not None:
        return
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    workbook_url = "https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?usp=sharing"
    creds_dict = _load_creds_dict()
    if not creds_dict:
        return
    from oauth2client.service_account import ServiceAccountCredentials
    import gspread
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    _workbook = client.open_by_url(workbook_url)
    _sheet = _workbook.get_worksheet(0)
    # One bulk read per container to avoid 429 (Read requests per minute)
    _cached_grid = _sheet.get_all_values()


class CachedSheet:
    """Thin wrapper over cached grid so lookup code can use same interface (findall, cell, row_values)."""

    def __init__(self, grid: list):
        self._grid = grid or []

    def findall(self, regex, col: int | None = None) -> list:
        """Return list of _CachedCell matching regex. col 1-based or None for any. Skip header row."""
        if not self._grid:
            return []
        rex = regex if hasattr(regex, "search") else re.compile(regex, re.IGNORECASE)
        out = []
        for r in range(1, len(self._grid)):
            row_vals = self._grid[r]
            for c in range(len(row_vals)):
                if col is not None and (c + 1) != col:
                    continue
                val = row_vals[c] if c < len(row_vals) else ""
                if rex.search(val):
                    out.append(_CachedCell(r + 1, c + 1, val))
        return out

    def cell(self, row: int, col: int) -> _CachedCell:
        """1-based row, col. Returns _CachedCell."""
        r, c = row - 1, col - 1
        val = ""
        if 0 <= r < len(self._grid) and 0 <= c < len(self._grid[r]):
            val = self._grid[r][c]
        return _CachedCell(row, col, val)

    def row_values(self, row: int) -> list:
        """1-based row. Returns list of values (same length as HEADERS by padding empty)."""
        r = row - 1
        if r < 0 or r >= len(self._grid):
            return []
        return list(self._grid[r])


def get_sheet():
    """Return CachedSheet for the wordbook. Loads and caches full sheet on first call (one API bulk read)."""
    _ensure_grid()
    if _cached_grid is None:
        return None
    return CachedSheet(_cached_grid)
