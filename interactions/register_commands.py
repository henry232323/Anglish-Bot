#!/usr/bin/env python3
"""
Register slash commands with Discord's API so they show up when users type /.

Run once after deploying the Lambda (or when you add/change commands).
Requires: DISCORD_BOT_TOKEN, optional DISCORD_APPLICATION_ID.

  export DISCORD_BOT_TOKEN="your_bot_token"
  python register_commands.py

Uses PUT /applications/{id}/commands to overwrite global commands.
"""
import os
import sys

try:
    import requests
except ImportError:
    print("Install requests: pip install requests", file=sys.stderr)
    sys.exit(1)

DISCORD_API = "https://discord.com/api/v10"
APPLICATION_ID = os.environ.get("DISCORD_APPLICATION_ID", "671065305681887238")


def get_headers():
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        print("Set DISCORD_BOT_TOKEN (your bot token from Discord Developer Portal).", file=sys.stderr)
        sys.exit(1)
    return {"Authorization": f"Bot {token}", "Content-Type": "application/json"}


# Command definitions matching what the Lambda handler expects (name + options).
# Option type 3 = STRING.
COMMANDS = [
    {
        "name": "help",
        "description": "How to use the Anglish bot",
        "type": 1,
        "options": [],
    },
    {
        "name": "m",
        "description": "Exact match in all languages (wordbook)",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "match",
        "description": "Exact match in all languages (wordbook)",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "f",
        "description": "Soft match in all languages (wordbook)",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "find",
        "description": "Soft match in all languages (wordbook)",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "am",
        "description": "Exact match in Anglish only",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "amatch",
        "description": "Exact match in Anglish only",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "af",
        "description": "Soft match in Anglish only",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "anglish",
        "description": "Soft match in Anglish only",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "a",
        "description": "Soft match in Anglish only",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "em",
        "description": "Exact match in English only",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "ematch",
        "description": "Exact match in English only",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "ef",
        "description": "Soft match in English only",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "english",
        "description": "Soft match in English only",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "e",
        "description": "Soft match in English only",
        "type": 1,
        "options": [{"name": "word", "description": "Word to look up", "type": 3, "required": True}],
    },
    {
        "name": "ety",
        "description": "Etymology search. Use -soft for soft match, -r wiki,etym,mec,bostol for resources.",
        "type": 1,
        "options": [
            {"name": "word", "description": "Word to look up", "type": 3, "required": True},
            {"name": "flags", "description": "Optional: -soft, -r wiki,etym,mec,bostol", "type": 3, "required": False},
        ],
    },
    {
        "name": "etymology",
        "description": "Etymology search. Use -soft for soft match, -r for resources.",
        "type": 1,
        "options": [
            {"name": "word", "description": "Word to look up", "type": 3, "required": True},
            {"name": "flags", "description": "Optional: -soft, -r wiki,etym,mec,bostol", "type": 3, "required": False},
        ],
    },
]


def main():
    url = f"{DISCORD_API}/applications/{APPLICATION_ID}/commands"
    headers = get_headers()
    r = requests.put(url, headers=headers, json=COMMANDS)
    if not r.ok:
        print(f"Discord API error: {r.status_code} {r.reason}", file=sys.stderr)
        print(r.text, file=sys.stderr)
        sys.exit(1)
    count = len(r.json())
    print(f"Registered {count} slash command(s). Users can now use /help, /m, /f, /ety, etc.")


if __name__ == "__main__":
    main()
