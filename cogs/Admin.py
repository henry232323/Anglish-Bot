import discord
from discord.ext import commands


class Admin(commands.Cog):
    name_blacklist = ["twitter.com/h0nde"]

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        for name in self.name_blacklist:
            if name in member.name:
                await member.ban()
                return
   