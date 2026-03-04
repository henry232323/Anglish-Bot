#!/usr/bin/env bash
# Deploy stack then sync slash commands locally. Run from repo root.
# Requires: DISCORD_PUBLIC_KEY, DISCORD_BOT_TOKEN (for the sync step).
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"
echo "Deploying stack..."
cdk deploy "$@"
cd "$REPO_ROOT"
if [ -z "$DISCORD_BOT_TOKEN" ]; then
  echo "Skipping slash command sync (DISCORD_BOT_TOKEN not set). Run manually: python interactions/register_commands.py"
  exit 0
fi
echo "Syncing slash commands..."
python interactions/register_commands.py
