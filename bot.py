import asyncio
import os
import sys
from pathlib import Path

# Load .env from repo root (required for DISCORD_BOT_TOKEN and GOOGLE_CREDENTIALS_JSON)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

import discord
import gspread_asyncio
from discord import app_commands
from discord.ext import commands
from oauth2client.service_account import ServiceAccountCredentials

# Reuse credential loading from interactions (env only)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from interactions.sheet_loader import _load_creds_dict

from cogs import Lookup, Etymology

# from cogs.admin import Admin

""" General Bot constants """
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
workbook_url = "https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?usp=sharing"
description = """
A bot for looking up words in the Anglish wordbook, made by @henry232323 (122739797646245899)
Invite: https://discordapp.com/oauth2/authorize?client_id=671065305681887238&permissions=19520&scope=bot
Wordbook: https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit
Discord: https://discordapp.com/invite/StjsRtP

If you appreciate what I do consider subscribing to my Patreon
https://www.patreon.com/henry232323



COMMANDS:

/help      --> how to use

/m <word>  --> exact match in all languages
/am <word> --> exact match in Anglish
/em <word> --> exact match in English

/f <word>  --> soft match in all languages
/af <word> --> soft match in Anglish
/ef <word> --> soft match in English


/ety <word> --> etymology search of exact match in all resources
Flags:
    -soft                       --> specifies soft match
    -r     wiki|etym|mec|bostol --> specifies resources to search as comma-separated list

What is a "soft match"?
Unlike a "hard match" (exact), a soft match (/f) will return all results that contain the query.
Ex: /f brook --> upbrook, abrook, brook
    /f use   --> outler, offcome



Bot is typing...?
Be patient! Your query is still being processed.
Please wait and more entries will load.



Bugs / Feedback / Requests?
Mention me and I'll try to respond :) (@henry232323)
"""

CLIENT_ID = 671065305681887238
intents = discord.Intents.default()  # No privileged intents (members, message_content)


class Bot(commands.Bot):
    manager = None
    client = None
    workbook = None
    sheet = None
    status_message = "/help for Anglish fun"
    desc = description

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            game=discord.Game(name=self.status_message),
            description=self.desc,
            command_prefix=["/", "!"],
            application_id=CLIENT_ID,
            **kwargs)

        # Token from env only (.env with DISCORD_BOT_TOKEN)
        self._auth = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
        if not self._auth:
            raise RuntimeError("Set DISCORD_BOT_TOKEN in .env (or export it)")

        # self.creds = ServiceAccountCredentials.from_json_keyfile_name(
        #     'resources/client_secret.json', scope
        # )

    async def setup_hook(self) -> None:
        asyncio.create_task(self.workbook_refresh())
        await self.add_cog(Lookup(self))
        await self.add_cog(Etymology(self))
        await bot.tree.sync()
        # self.add_cog(Admin())

    async def workbook_refresh(self):
        while True:
            creds_dict = _load_creds_dict()
            if not creds_dict:
                self.sheet = None
                self.workbook = None
                self.sheets = (None,)
                await asyncio.sleep(60 * 30)
                continue
            self.creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            self.manager = gspread_asyncio.AsyncioGspreadClientManager(lambda *args: self.creds)
            self.client = await self.manager.authorize()
            self.workbook = await self.client.open_by_url(workbook_url)
            self.sheet = await self.workbook.get_worksheet(0)
            self.sheets = (self.sheet,)
            await asyncio.sleep(60 * 30)

    def run(self):
        super().run(self._auth)


bot = Bot(intents=intents)
bot.run()
