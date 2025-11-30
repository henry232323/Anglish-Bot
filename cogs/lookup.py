import re
import asyncio
import async_timeout
import discord
from discord.ext import commands
import disputils

""" Row formatting constants """
letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
headers = ["Word", "Unswayed", "Meaning", "Kind", "Forebear", "Whence", "🔨", "Notes", "Who?", "Source"]
furls = [
    "https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?gid=0&range={}{}"
]
help_field = "Use /help for command usage. If the bot is typing it is still generating new results that the page number might not reflect"
statuses = ["In Wordbook", "Seen"]


class Lookup(commands.Cog):
    """Commands for Lookup of Anglish Words"""

    def __init__(self, bot):
        self.bot = bot

    async def _format_row(self, ctx, cell, word):
        title = (await ctx.bot.sheets[0].cell(cell.row, 1)).value
        url = furls[0].format(letters[cell.col], cell.row)
        author = {'name': word, 'icon_url': str(ctx.author.avatar.url)}
        fields = [
            {'name': header, 'value': value}
            for header, val in zip(headers, await ctx.bot.sheet.row_values(cell.row))
            if (value := str(bool(val)) if header == "🔨" else val)
        ]
        fields += [{'name': "Help", 'value': help_field}]

        return discord.Embed.from_dict(
            {'color': 0xDD0000, 'title': title, 'url': url, 'author': author, 'fields': fields}
        )

    async def _send_results(self, ctx, cells, word):
        reduced = [{cell.row: cell for cell in cells[0] if cell.row != 1}]
        embeds = []
        for chunk in reduced:
            for i, cell in enumerate(chunk.values()):
                embeds.append(
                    await self._format_row(ctx, cell, word))
                if i == (0 if len(chunk) == 1 else 1):
                    paginator = disputils.BotEmbedPaginator(ctx, embeds)
                    ctx.bot.loop.create_task(paginator.run())
        # print([embed.to_dict() for embed in embeds])

        if not embeds:
            await ctx.send("Query not found!")

    async def _findall_in_worksheets(self, ctx, regex, word, *, sheets=None, col=None):
        """ Private helper function containing sheet search logic """
        try:
            async with ctx.typing():
                async with async_timeout.timeout(300):
                    if sheets is None:
                        sheets = (self.bot.sheet,)
                    rex = re.compile(regex, re.RegexFlag.IGNORECASE)
                    cells = [await sheet.findall(rex) for sheet in sheets]
                    if col is not None:
                        cells = list(map(lambda cell: filter(lambda x: x.col == col, cell), cells))
                    await self._send_results(ctx, cells, word)
        except asyncio.TimeoutError:
            pass

    @commands.hybrid_command(aliases=["m"])
    async def match(self, ctx, *, word, hard=True, col=None):
        """ HARD match """
        regex = rf"\b({word})\b" if hard else rf"({word})"
        await self._findall_in_worksheets(ctx, regex, word, col=col)

    @commands.hybrid_command(aliases=["f"])
    async def find(self, ctx, *, word, col=None):
        """ SOFT match """
        await self.match(ctx, word=word, hard=False, col=col)

    @commands.hybrid_command(aliases=["am"])
    async def amatch(self, ctx, *, word):
        """ Anglish-only HARD match """
        await self.match(ctx, word=word, col=1)

    @commands.hybrid_command(aliases=["af", "a"])
    async def anglish(self, ctx, *, word):
        """ Anglish-only SOFT match """
        await self.find(ctx, word=word, col=1)

    @commands.hybrid_command(aliases=["em"])
    async def ematch(self, ctx, *, word):
        """ English-only HARD match """
        await self.match(ctx, word=word, col=3)

    @commands.hybrid_command(aliases=["ef", "e"])
    async def english(self, ctx, *, word):
        """ English-only SOFT match """
        await self.find(ctx, word=word, col=3)

