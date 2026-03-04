"""
CDK Stack: Lambda + API Gateway for Discord Interactions endpoint.
Lambda uses code asset (interactions/) + optional dependency layer. Build the layer before deploy (see build_layer.sh).
Slash commands are synced locally after deploy (see deploy script).
"""
import os
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as apigw_integrations
from aws_cdk import aws_lambda
from constructs import Construct


REQUIRED_ENV = [
    "DISCORD_PUBLIC_KEY",
    "DISCORD_APPLICATION_ID",
    "DISCORD_BOT_TOKEN",
    "GOOGLE_CREDENTIALS_JSON",
]


def _validate_env() -> None:
    missing = [k for k in REQUIRED_ENV if not (os.environ.get(k) or "").strip()]
    if missing:
        raise ValueError(
            f"Missing required env var(s): {', '.join(missing)}. "
            "Set them in .env (deploy.sh sources it) or export before deploy."
        )


class AnglishBotStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        _validate_env()
        super().__init__(scope, id, **kwargs)

        repo_root = Path(__file__).resolve().parent.parent
        lambda_dir = repo_root / "interactions"
        application_id = os.environ["DISCORD_APPLICATION_ID"].strip()

        # Optional: dependency layer (run build_layer.sh or pip install -r interactions/requirements.txt -t infrastructure/lambda_layer/python)
        layer_dir = repo_root / "infrastructure" / "lambda_layer"
        layer = None
        if (layer_dir / "python").exists():
            layer = aws_lambda.LayerVersion(
                self,
                "DepsLayer",
                code=aws_lambda.Code.from_asset(str(layer_dir)),
                compatible_runtimes=[aws_lambda.Runtime.PYTHON_3_10],
            )

        discord_handler = aws_lambda.Function(
            self,
            "DiscordHandler",
            runtime=aws_lambda.Runtime.PYTHON_3_10,
            handler="handler.handler",
            code=aws_lambda.Code.from_asset(str(lambda_dir)),
            timeout=cdk.Duration.seconds(30),
            memory_size=256,
            layers=[layer] if layer else [],
            environment={
                "DISCORD_PUBLIC_KEY": os.environ["DISCORD_PUBLIC_KEY"].strip(),
                "DISCORD_APPLICATION_ID": application_id,
                "GOOGLE_CREDENTIALS_JSON": os.environ["GOOGLE_CREDENTIALS_JSON"].strip(),
                "DISCORD_BOT_TOKEN": os.environ["DISCORD_BOT_TOKEN"].strip(),
            },
        )
        # Self-invoke for defer+follow-up: allow Lambda's role to invoke this function (resource-based, no role change)
        aws_lambda.CfnPermission(
            self,
            "SelfInvokePermission",
            action="lambda:InvokeFunction",
            function_name=discord_handler.function_name,
            principal=discord_handler.role.role_arn,
        )

        # HTTP API (API Gateway v2) - single POST route for Discord
        api = apigwv2.HttpApi(
            self,
            "AnglishBotApi",
            description="Discord Interactions endpoint for Anglish bot",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[apigwv2.CorsHttpMethod.POST, apigwv2.CorsHttpMethod.OPTIONS],
                allow_headers=["Content-Type", "X-Signature-Ed25519", "X-Signature-Timestamp"],
            ),
        )

        integration = apigw_integrations.HttpLambdaIntegration(
            "DiscordIntegration",
            discord_handler,
            payload_format_version=apigwv2.PayloadFormatVersion.VERSION_2_0,
        )

        api.add_routes(
            path="/",
            methods=[apigwv2.HttpMethod.POST],
            integration=integration,
        )

        # Output: set this URL as "Interactions Endpoint URL" in Discord Developer Portal
        cdk.CfnOutput(
            self,
            "InteractionsEndpointUrl",
            value=api.url or "",
            description="Set this as your Discord app's Interactions Endpoint URL",
            export_name="AnglishBotInteractionsEndpointUrl",
        )
