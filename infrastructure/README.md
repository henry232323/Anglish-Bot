# Anglish Bot – CDK Deployment (Discord Interactions + Lambda)

This directory contains AWS CDK code to deploy the Anglish bot as a **Discord Interactions** endpoint: Discord sends HTTP POSTs to API Gateway, which invokes a Lambda that handles slash commands and button clicks. The Lambda uses a **code asset** (interactions/) plus an optional **dependency layer** (PyNaCl, gspread, etc.).

**You do not need the Server Members (or Message Content) privileged intent** for this setup. The Lambda only uses the `member`/`user` Discord includes in each interaction payload.

## Deploy via GitHub Actions (recommended)

The workflow builds the Lambda layer (Linux-compatible, including PyNaCl) then deploys the stack.

1. **Secrets** (Settings → Secrets and variables → Actions):  
   `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `DISCORD_PUBLIC_KEY`, `DISCORD_APPLICATION_ID`.  
   Optional: `GOOGLE_CREDENTIALS_JSON` for wordbook/etymology; `DISCORD_BOT_TOKEN` so lookup/ety can respond within 3s (defer + follow-up).

2. Push to `main`/`master` or run the **Build and Deploy** workflow manually. It runs `build_layer.sh` (Docker on the runner), then `cdk deploy`.

3. After deploy, register slash commands (from your machine):  
   `DISCORD_BOT_TOKEN=... python interactions/register_commands.py`

## Local deploy

**Prerequisites:** AWS CLI configured, Node.js 18+, Python 3.10. For the layer, Docker (recommended) or pip with `--platform manylinux2014_x86_64`.

1. **Build the dependency layer** (from repo root):  
   `./infrastructure/build_layer.sh`  
   This populates `infrastructure/lambda_layer/python` with Linux-compatible packages (PyNaCl, gspread, etc.). The stack attaches it only if that directory exists.

2. **Set env and deploy:**  
   `export DISCORD_PUBLIC_KEY=...` (and optionally `DISCORD_APPLICATION_ID`, `GOOGLE_CREDENTIALS_JSON`, `DISCORD_BOT_TOKEN` for defer+follow-up)  
   From repo root: `./infrastructure/deploy.sh`  
   Or from `infrastructure/`: `pip install -r requirements.txt` then `npx aws-cdk deploy`.

3. **Slash commands:**  
   From repo root: `DISCORD_BOT_TOKEN=... python interactions/register_commands.py`

## Configure Discord

1. Open [Discord Developer Portal](https://discord.com/developers/applications) → your application.
2. **General Information** → copy **Public Key** (for `DISCORD_PUBLIC_KEY`).
3. **Interactions** → set **Interactions Endpoint URL** to the stack output `InteractionsEndpointUrl` (e.g. `https://xxxxxx.execute-api.region.amazonaws.com`).

## Stack contents

- **Lambda**: Python 3.10, code from `../interactions`, optional dependency layer from `lambda_layer/` (build with `build_layer.sh`).
- **API Gateway HTTP API**: Single `POST /` route → Lambda (payload format 2.0).
- **Output**: `InteractionsEndpointUrl` – set this in the Discord app’s Interactions settings.
