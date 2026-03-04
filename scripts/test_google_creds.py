#!/usr/bin/env python3
"""
Test Google credentials locally before deploy.
Loads .env from repo root (python-dotenv if available), then validates GOOGLE_CREDENTIALS_JSON or file.
Run from repo root: python scripts/test_google_creds.py
"""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"


def _load_env() -> None:
    """Load .env: use python-dotenv if installed, else minimal parser."""
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
        return
    except ImportError:
        pass
    if not ENV_FILE.exists():
        return
    with open(ENV_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, rest = line.partition("=")
            key, val = key.strip(), rest.strip()
            if val.startswith("'") and "'" in val[1:]:
                val = val[1 : val.rindex("'")].replace("\\'", "'")
            elif val.startswith('"') and '"' in val[1:]:
                val = val[1 : val.rindex('"')].replace('\\"', '"')
            os.environ[key] = val


def main() -> int:
    _load_env()
    sys.path.insert(0, str(REPO_ROOT / "interactions"))
    from sheet_loader import _load_creds_dict, get_sheet

    print("Loading credentials from GOOGLE_CREDENTIALS_JSON...")
    try:
        creds = _load_creds_dict()
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    if not creds:
        print("GOOGLE_CREDENTIALS_JSON not set. Set it in .env (base64 or single-line JSON).")
        return 0
    print("Credentials parsed OK (dict with keys:", list(creds.keys()), ")")
    print("Trying get_sheet() (will hit Google)...")
    try:
        sheet = get_sheet()
        if sheet is None:
            print("get_sheet() returned None.")
            return 1
        print("get_sheet() OK — first row sample:", sheet.row_values(1)[:3] if sheet.row_values(1) else "(empty)")
    except Exception as e:
        print(f"get_sheet() failed: {e}")
        return 1
    print("All good. For Lambda use base64: GOOGLE_CREDENTIALS_JSON=$(base64 -w 0 resources/client_secret.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
