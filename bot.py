from discord.ext import commands
import gspread_asyncio
import asyncio
from oauth2client.service_account import ServiceAccountCredentials

from cogs import Lookup


""" General Bot constants """
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
workbook_url = "https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?usp=sharing"
offerbook_url = "https://docs.google.com/spreadsheets/d/16f4aeFsNC4oHt3zt-XskiEzcQwU1u-rdh6P8rLCEDOM/edit?usp=sharing"
description = """
A bot for looking up words in the Anglish wordbook, made by @Henry#8808 (122739797646245899)
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

Want to search the offerings page too?
Append an -o to the command string!
Ex: /emo <word> --> exact match in English in wordbook & offerings
    /afo <word> --> soft match in Anglish in wordbook & offerings



What is a "soft match"?
Unlike a "hard match" (exact), a soft match (/f) will return all results that contain the query.
Ex: /f brook --> upbrook, abrook, brook
    /f use   --> outler, offcome



Bot is typing...?
Be patient! Your query is still being processed.
Please wait and more entries will load.



Bugs / Feedback / Requests?
Mention me and I'll try to respond :) (@Henry#8808)
"""



class Bot(commands.Bot):
    manager = None
    client = None
    workbook = None
    sheet = None
    offersheet1 = None
    offersheet2 = None
    status_message = "/help for Anglish fun"
    desc = description

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            game=discord.Game(name=self.status_message),
            description=self.desc,
            command_prefix="/",
            **kwargs)

        with open("resources/auth") as af:
            self._auth = af.read()

        self.creds = ServiceAccountCredentials.from_json_keyfile_name(
            'resources/client_secret.json', scope)
        self.loop.create_task(self.workbook_refresh())
        self.add_cog(Lookup(self))

    async def workbook_refresh(self):
        while True:
            self.manager = gspread_asyncio.AsyncioGspreadClientManager(lambda *args: self.creds)
            self.client = await self.manager.authorize()
            self.workbook = await self.client.open_by_url(workbook_url)
            self.sheet = await self.workbook.get_worksheet(0)
            self.offerworkbook = await self.client.open_by_url(offerbook_url)
            self.offersheet1 = await self.offerworkbook.get_worksheet(0)
            self.offersheet2 = await self.offerworkbook.get_worksheet(1)
            self.sheets = (self.sheet, self.offersheet1, self.offersheet2)
            await asyncio.sleep(60 * 30)

    def run(self):
        super().run(self._auth)


bot = Bot()
bot.run()