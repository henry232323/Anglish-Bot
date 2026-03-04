#!/usr/bin/env python3
import os
import aws_cdk as cdk
from anglish_bot_stack import AnglishBotStack

app = cdk.App()
AnglishBotStack(
    app,
    "AnglishBotStack",
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION"),
    ),
    description="Discord Anglish bot via Interactions webhook (Lambda + API Gateway)",
)
app.synth()
