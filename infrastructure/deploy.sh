#!/usr/bin/env bash
# Build Lambda layer, deploy stack, then sync slash commands. Run from repo root.
# Requires: DISCORD_PUBLIC_KEY, DISCORD_BOT_TOKEN (for the sync step).
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -f "$REPO_ROOT/.env" ]; then
  set -a
  source "$REPO_ROOT/.env"
  set +a
  echo "Sourced $REPO_ROOT/.env"
fi
cd "$REPO_ROOT"
echo "Building Lambda layer..."
bash "$SCRIPT_DIR/build_layer.sh"
cd "$SCRIPT_DIR"
echo "Deploying stack..."
npx aws-cdk deploy "$@"
cd "$REPO_ROOT"
if [ -z "$DISCORD_BOT_TOKEN" ]; then
  echo "Skipping slash command sync (DISCORD_BOT_TOKEN not set). Run manually: python interactions/register_commands.py"
  exit 0
fi
echo "Syncing slash commands..."
python interactions/register_commands.py
