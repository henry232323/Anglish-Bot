# Anglish Bot – Interactions (Lambda)

This directory contains the Discord Interactions handler (slash commands + button pagination) that runs on AWS Lambda behind API Gateway.

## Registering slash commands

Discord does not discover commands from the endpoint; they must be registered via the API. The easiest way is to use the deploy script from the repo root (it runs `cdk deploy` then syncs commands locally):

```bash
export DISCORD_PUBLIC_KEY="..."
export DISCORD_BOT_TOKEN="your_bot_token"
./infrastructure/deploy.sh
```

Or run the sync step only after deploy:

```bash
export DISCORD_BOT_TOKEN="your_bot_token"
python interactions/register_commands.py
```

See `../infrastructure/README.md` for full deploy and Discord setup.
