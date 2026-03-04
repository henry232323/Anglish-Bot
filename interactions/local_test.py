#!/usr/bin/env python3
"""
Run the Discord handler locally with a mock API Gateway event.
Set LOCAL_TEST=1 so signature verification is skipped.

  cd interactions && LOCAL_TEST=1 python local_test.py
  # Or with env from repo root:
  cd interactions && set -a && source ../.env && set +a && LOCAL_TEST=1 python local_test.py

Tests: PING (type 1), then optional /help (type 2) if --help is passed.
"""
import json
import os
import sys

# Ensure we can import handler and deps (run from interactions/ or repo root with path)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("LOCAL_TEST", "1")

from handler import handler


def make_ping_event():
    """Mock API Gateway HTTP API event with Discord PING (type 1). No real signature when LOCAL_TEST=1."""
    body = json.dumps({"type": 1, "version": 1})
    return {
        "requestContext": {},
        "headers": {
            "content-type": "application/json",
            "x-signature-ed25519": "00" * 32,
            "x-signature-timestamp": "1234567890",
        },
        "body": body,
        "isBase64Encoded": False,
    }


def make_help_event():
    """Mock event for /help slash command (type 2)."""
    body = json.dumps({
        "type": 2,
        "data": {
            "name": "help",
            "options": [],
        },
        "member": {
            "user": {
                "id": "123",
                "username": "TestUser",
                "avatar": None,
            },
        },
    })
    return {
        "requestContext": {},
        "headers": {
            "content-type": "application/json",
            "x-signature-ed25519": "00" * 32,
            "x-signature-timestamp": "1234567890",
        },
        "body": body,
        "isBase64Encoded": False,
    }


def main():
    run_help = "--help" in sys.argv
    print("LOCAL_TEST=1 (signature check skipped)")
    print("DISCORD_PUBLIC_KEY set:", bool(os.environ.get("DISCORD_PUBLIC_KEY")))
    print()

    # 1. PING
    print("--- PING (type 1) ---")
    event = make_ping_event()
    result = handler(event, None)
    print("Status:", result.get("statusCode"))
    print("Body:", result.get("body", "")[:200])
    if result.get("statusCode") != 200:
        print("FAIL: expected 200 for PING")
        sys.exit(1)
    body = json.loads(result.get("body", "{}"))
    if body.get("type") != 1:
        print("FAIL: expected type 1 (PONG)")
        sys.exit(1)
    print("OK: PONG returned\n")

    if run_help:
        print("--- /help (type 2) ---")
        event = make_help_event()
        result = handler(event, None)
        print("Status:", result.get("statusCode"))
        b = result.get("body", "{}")
        print("Body length:", len(b))
        if result.get("statusCode") == 200:
            data = json.loads(b)
            print("Response type:", data.get("type"))
            if "data" in data and "embeds" in data["data"]:
                print("OK: embeds in response")
        else:
            print("Body:", b[:300])
    print("\nDone.")


if __name__ == "__main__":
    main()
