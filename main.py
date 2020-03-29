import asyncio
import re

import async_timeout
import discord
from discord.ext import commands
import disputils
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

    async def send_results(self, ctx, cells, word):
        reduced = {cell.row: cell for cell in cells if cell.row != 1}
        embeds = []
        try:
            async with ctx.typing():
                async with async_timeout.timeout(300):
                    for i, cell in enumerate(reduced.values()):
                        # print(i, cell)
                        embed = await self.bot.format_row(ctx, cell, word)
                        embeds.append(embed)

                        if i == (0 if len(reduced) == 1 else 1):
                            paginator = disputils.BotEmbedPaginator(ctx, embeds)
                            self.bot.loop.create_task(paginator.run())
        except asyncio.TimeoutError:
            pass

        if not embeds:
            await ctx.send("Query not found!")

    @commands.command(aliases=["am"])
    async def amatch(self, ctx, *, word):
        """ See the match command, exact same syntax except it searches only the Anglish column """
        rex = re.compile(rf"^({word})$", re.RegexFlag.IGNORECASE)
        cells = await self.bot.sheet.findall(rex)
        cells = (x for x in cells if x.col == 1)
        await self.send_results(ctx, cells, word)

    @commands.command(aliases=["a"])
    async def anglish(self, ctx, *, word):
        """ See the find command, exact same syntax except it searches only the Anglish column """
        rex = re.compile(rf"({word})", re.RegexFlag.IGNORECASE)
        cells = await self.bot.sheet.findall(rex)
        cells = (x for x in cells if x.col == 1)
        await self.send_results(ctx, cells, word)

    @commands.command(aliases=["em"])
    async def ematch(self, ctx, *, word):
        """ See the match command, exact same syntax except it searches only the English meaning column """
        rex = re.compile(rf"^({word})$", re.RegexFlag.IGNORECASE)
        cells = await self.bot.sheet.findall(rex)
        cells = (x for x in cells if x.col == 2)
        await self.send_results(ctx, cells, word)

    @commands.command(aliases=["e"])
    async def english(self, ctx, *, word):
        """ See the find command, exact same syntax except it searches only the English meaning column """
        rex = re.compile(rf"({word})", re.RegexFlag.IGNORECASE)
        cells = await self.bot.sheet.findall(rex)
        cells = (x for x in cells if x.col == 2)
        await self.send_results(ctx, cells, word)

    @commands.command(aliases=["m"])
    async def match(self, ctx, *, word):
        """Find entries in the Anglish Wordbook looking for exact matches. Search with Anglish, English, or Old English
        Example:
            - /m brook -> brook
            - /m use -> brook
            - /m to use -> brook, benoot, upbrook, spurn
        Ideal for looking up Anglish words to English, or specific English words' translations
        https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?usp=sharing
        """
        cells = await self.bot.sheet.findall(re.compile(rf"^({word})$", re.RegexFlag.IGNORECASE))
        await self.send_results(ctx, cells, word)

    @commands.command(aliases=["f"])
    async def find(self, ctx, *, word):
        """Find entries in the Anglish Wordbook with soft matches. Search with Anglish, English, or Old English
        Examples:
            - /f brook -> upbrook, abrook, brook
            - /f use -> outler, offcome
        Better if you aren't quite sure, but looking for more broad answers
        https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?usp=sharing
        """
        rex = re.compile(rf"({word})", re.RegexFlag.IGNORECASE)
        cells = await self.bot.sheet.findall(rex)
        await self.send_results(ctx, cells, word)


class Bot(commands.Bot):
    manager = None
    client = None
    workbook = None
    sheet = None
    status_message = "/help for Anglish fun"
    desc = \
        """
A bot for looking up words in the Anglish wordbook, made by @Henry#8808 (122739797646245899)
Invite: https://discordapp.com/oauth2/authorize?client_id=671065305681887238&permissions=19520&scope=bot
Wordbook: https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit
Discord: https://discordapp.com/invite/StjsRtP

If you appreciate what I do consider subscribing to my Patreon
https://www.patreon.com/henry232323
        
Bot is pretty easy y'all, use `/help` if you ever forget how to use the bot. \
`/m <word>` (e.g. /m brook) to look up a word by exact match, this will search any word \
(Anglish, English, OE, anywhere in the document), but only exact matches. \
`/m <word>` will likely only return the exact entry for brook. \
`/f <word>` is a little more broad, it will match anything containing the word, \
for example `/f <word>` will give brook, upbrook, and others. \
You'll likely want to use this when you're looking for an Anglish word from English. \
`/m` is best for when you know the exact Anglish word you're wanting info on. \
These commands include equivalents for if you want to search specific columns. \
To search an existing Anglish term use `/a <word>` or `/am <word>` for `/m` functionality, \
and equivalently for searching existing English words use `/e <word>` and `/em <word>`. \
If the bot is typing, that means it is still processing your query, so wait and more entries will load. \
See full descriptions with /help <command>. Good luck y'all, if you have any bugs to report or requests, mention me
"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         game=discord.Game(name=self.status_message),
                         description=self.desc,
                         command_prefix="/",
                         **kwargs)

        with open("resources/auth") as af:
            self._auth = af.read()

        self.loop.create_task(self.workbook_refresh())

    async def workbook_refresh(self):
        while True:
            self.manager = gspread_asyncio.AsyncioGspreadClientManager(lambda *args: creds)
            self.client = await self.manager.authorize()
            self.workbook = await self.client.open_by_url(
                "https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?usp=sharing")
            self.sheet = await self.workbook.get_worksheet(0)
            await asyncio.sleep(60 * 30)

    def run(self):
        super().run(self._auth)

    async def format_row(self, message, cell, query):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        headers = ["Word", "Meaning", "Kind", "Forebear", "Whence", "🔨", "Notes"]
        furl = "https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?gid=0&range={}{}"
        embed = discord.Embed(color=0xDD0000, title=(await self.sheet.cell(cell.row, 1)).value,
                              url=furl.format(letters[cell.col], cell.row))
        embed.set_author(name=query, icon_url=message.author.avatar_url)
        for h, c in zip(headers, await self.sheet.row_values(cell.row)):
            if h == "🔨":
                c = str(bool(c))
            if c:
                embed.add_field(name=h, value=c)

        embed.add_field(name="Help",
            value="Use /help for command usage. If the bot is typing it is still generating new results that the page number might not reflect")

        return embed

    async def on_ready(self):
        self.add_cog(Commands(self))


bot = Bot()
bot.run()
