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


class AnglishBotStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        repo_root = Path(__file__).resolve().parent.parent
        lambda_dir = repo_root / "interactions"
        application_id = os.environ.get("DISCORD_APPLICATION_ID", "671065305681887238")

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
                "DISCORD_PUBLIC_KEY": os.environ.get("DISCORD_PUBLIC_KEY", ""),
                "DISCORD_APPLICATION_ID": application_id,
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
        google_creds = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if google_creds:
            discord_handler.add_environment("GOOGLE_CREDENTIALS_JSON", google_creds)
        bot_token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
        if bot_token:
            discord_handler.add_environment("DISCORD_BOT_TOKEN", bot_token)

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
