from discord.ext import commands
import gspread_asyncio
import asyncio
import discord
from oauth2client.service_account import ServiceAccountCredentials

# local imports
from constants import letters, furls, statuses, help_field
from cog import Commands

class Bot(commands.Bot):
    manager = None
    client = None
    workbook = None
    sheet = None
    offersheet1 = None
    offersheet2 = None
    status_message = "/help for Anglish fun"
    desc = constants.description

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
            'resources/client_secret.json', constants.scope)
        self.loop.create_task(self.workbook_refresh())
        self.add_cog(Commands(self))

    async def workbook_refresh(self):
        while True:
            self.manager = gspread_asyncio.AsyncioGspreadClientManager(lambda *args: self.creds)
            self.client = await self.manager.authorize()
            self.workbook = await self.client.open_by_url(constants.workbook_url)
            self.sheet = await self.workbook.get_worksheet(0)
            self.offerworkbook = await self.client.open_by_url(constants.offerbook_url)
            self.offersheet1 = await self.offerworkbook.get_worksheet(0)
            self.offersheet2 = await self.offerworkbook.get_worksheet(1)
            self.sheets = (self.sheet, self.offersheet1, self.offersheet2)
            await asyncio.sleep(60 * 30)

    def run(self):
        super().run(self._auth)

    async def format_row(self, message, cell, query, chunk_idx=0, mixed=False):
        headers = constants.headers + ["Who?", "Source"] if mixed else constants.headers
        title = (await self.sheets[chunk_idx].cell(cell.row, 1)).value
        url = furls[chunk_idx].format(letters[cell.col], cell.row)
        author = dict(name=query, icon_url=message.author.avatar_url)
        fields = [
            dict(name=header, value=val) \
            for header, val in zip(headers, await self.sheet.row_values(cell.row)) \
            if (val := str(bool(val)) if header == "🔨" else val)]
        fields += [dict(name="Status", value=statuses[chunk_idx])] if mixed
        fields += [dict(name="Help", value=help_field)]

        return discord.Embed.from_dict(dict(
            color=0xDD0000, title=title, url=url, author=author, fields=fields))
