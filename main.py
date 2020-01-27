import asyncio
import re

import discord
import gspread_asyncio
from oauth2client.service_account import ServiceAccountCredentials

# use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('resources/client_secret.json', scope)


# Find a workbook by name and open the first sheet
# Make sure you use the right name here.


class Bot(discord.Client):
    status_message = "//help"

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         game=discord.Game(name=self.status_message),
                         **kwargs)

        with open("resources/auth") as af:
            self._auth = af.read()

    def run(self):
        super().run(self._auth)

    async def format_row(self, message, cell, query):
        headers = ["Word", "Meaning", "Kind", "Forebear", "Whence", "🔨", "Notes"]
        furl = "https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?gid=0&range={}{}"
        embed = discord.Embed(color=0xDD0000, title=(await self.sheet.cell(cell.row, 1)).value, url=furl.format(cell.col, cell.row))
        embed.set_author(name=query, icon_url=message.author.avatar_url)
        for col, h in enumerate(headers):
            c = (await self.sheet.cell(cell.row, col + 1)).value
            if h == "🔨":
                c = str(bool(c))
            if c:
                embed.add_field(name=h, value=c)

        return embed

    async def on_ready(self):
        self.manager = gspread_asyncio.AsyncioGspreadClientManager(lambda *args: creds)
        self.client = await self.manager.authorize()
        self.workbook = await self.client.open_by_url("https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?usp=sharing")
        self.sheet = await self.workbook.get_worksheet(0)

    async def on_message(self, message):
        if message.content.startswith("/help"):
            await message.channel.send("Do /f <word> to look up a word, Anglish, English, or Old English")
        elif message.content.startswith("/f"):
            word = message.content.strip("/f ")
            cells = await self.sheet.findall(re.compile(rf".*({word}).*", re.RegexFlag.IGNORECASE))
            reduced = {cell.row: cell for cell in cells}
            embeds = []
            for i, cell in enumerate(reduced.values()):
                if i == 10:
                    break
                embed = await self.format_row(message, cell, word)
                embeds.append(embed)
                await message.channel.send(embed=embed)
            if not embeds:
                await message.channel.send("Query not found!")


bot = Bot()
bot.run()
