#!/usr/bin/env python3
"""
Load .env with python-dotenv and test parsing GOOGLE_CREDENTIALS_JSON.
Run from repo root: pip install python-dotenv && python scripts/test_env_json.py
"""
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"

try:
    from dotenv import load_dotenv
except ImportError:
    print("Install python-dotenv: pip install python-dotenv", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    if not ENV_FILE.exists():
        print(f"No .env at {ENV_FILE}", file=sys.stderr)
        return 1
    load_dotenv(ENV_FILE)
    raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
    if not raw:
        print("GOOGLE_CREDENTIALS_JSON not set in .env")
        return 0
    print(f"GOOGLE_CREDENTIALS_JSON length: {len(raw)}")
    print(f"First 80 chars: {raw[:80]!r}")
    if "\n" in raw or "\r" in raw:
        print("(contains literal newlines / CR — will try normalized parse)")
    try:
        data = json.loads(raw)
        print("json.loads(raw) OK, keys:", list(data.keys()) if isinstance(data, dict) else type(data))
        return 0
    except json.JSONDecodeError as e:
        print(f"json.loads(raw) failed: {e}")
        normalized = raw.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")
        try:
            data = json.loads(normalized)
            print("json.loads(normalized) OK, keys:", list(data.keys()))
            return 0
        except json.JSONDecodeError:
            pass
        try:
            import ast
            data = ast.literal_eval(raw)
            print("ast.literal_eval(raw) OK (Python literal in .env), keys:", list(data.keys()) if isinstance(data, dict) else type(data))
            return 0
        except (ValueError, SyntaxError) as e2:
            print(f"ast.literal_eval also failed: {e2}")
        if "Expecting property name" in str(e):
            print("\nYour .env value is not valid JSON (keys need double quotes). Rewrite with:")
            print("  printf 'GOOGLE_CREDENTIALS_JSON=%s\\n' \"'$(jq -c . resources/client_secret.json)'\" >> .env")
            print("Or use base64:  export GOOGLE_CREDENTIALS_JSON=$(base64 < resources/client_secret.json | tr -d '\\n')")
        return 1


if __name__ == "__main__":
    sys.exit(main())
