import re

import discord
from discord.ext import commands
import gspread_asyncio
from oauth2client.service_account import ServiceAccountCredentials

# use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('resources/client_secret.json', scope)


# Find a workbook by name and open the first sheet
# Make sure you use the right name here.
class Commands(commands.Cog):
    """Commands for Lookup of Anglish Words"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["m"])
    async def match(self, ctx, *, word):
        """Find entries in the Anglish Wordbook looking for exact matches. Search with Anglish, English, or Old English
        Example:
            - /m brook -> brook
            - /m use -> brook
            - /m to use -> brook, benoot, upbrook, spurn
        Ideal for looking up Anglish words to English, or specific English words' translations
        """
        cells = await self.bot.sheet.findall(re.compile(rf"^({word})$", re.RegexFlag.IGNORECASE))
        reduced = {cell.row: cell for cell in cells if cell.row != 1}
        embeds = []
        for i, cell in enumerate(reduced.values()):
            if i == 10:
                break
            embed = await self.bot.format_row(ctx, cell, word)
            embeds.append(embed)
            await ctx.send(embed=embed)

        if not embeds:
            await ctx.send("Query not found!")

    @commands.command(aliases=["f"])
    async def find(self, ctx, *, word):
        """Find entries in the Anglish Wordbook with soft matches. Search with Anglish, English, or Old English
        Examples:
            - /f brook -> upbrook, abrook, brook
            - /f use -> outler, offcome
        Better if you aren't quite sure, but looking for more broad answers
        """
        rex = re.compile(rf"({word})", re.RegexFlag.IGNORECASE)
        cells = await self.bot.sheet.findall(rex)
        reduced = {cell.row: cell for cell in cells if cell.row != 1}
        embeds = []
        for i, cell in enumerate(reduced.values()):
            if i == 10:
                break
            embed = await self.bot.format_row(ctx, cell, word)
            embeds.append(embed)
            await ctx.send(embed=embed)

        if not embeds:
            await ctx.send("Query not found!")


class Bot(commands.Bot):
    status_message = "/help for Anglish fun"

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         game=discord.Game(name=self.status_message),
                         description="A bot for looking up words in the Anglish wordbook, made by @Henry#8808 (122739797646245899)",
                         command_prefix="/",
                         **kwargs)

        with open("resources/auth") as af:
            self._auth = af.read()

    def run(self):
        super().run(self._auth)

    async def format_row(self, message, cell, query):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        headers = ["Word", "Meaning", "Kind", "Forebear", "Whence", "🔨", "Notes"]
        furl = "https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?gid=0&range={}{}"
        embed = discord.Embed(color=0xDD0000, title=(await self.sheet.cell(cell.row, 1)).value,
                              url=furl.format(letters[cell.col], cell.row))
        embed.set_author(name=query, icon_url=message.author.avatar_url)
        for col, h in enumerate(headers):
            c = (await self.sheet.cell(cell.row, col + 1)).value
            if h == "🔨":
                c = str(bool(c))
            if c:
                embed.add_field(name=h, value=c)

        return embed

    async def on_ready(self):
        self.add_cog(Commands(self))
        self.manager = gspread_asyncio.AsyncioGspreadClientManager(lambda *args: creds)
        self.client = await self.manager.authorize()
        self.workbook = await self.client.open_by_url(
            "https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?usp=sharing")
        self.sheet = await self.workbook.get_worksheet(0)


bot = Bot()
bot.run()
