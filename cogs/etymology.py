import re
import aiohttp
import asyncio
import async_timeout
import discord
from discord.ext import commands
import disputils
import ety
from bs4 import BeautifulSoup

RESOURCES = ['wiki', 'etym', 'mec', 'bostol']

class Etymology(commands.Cog):

  async def __int__(self, bot):
    self.bot = bot

  def _get_embed(**kwargs):
    return discord.Embed.from_dict({
      'color': 0xDD0000,
      'title': kwargs.word,
      'author': { 'name': kwargs.name, 'icon_url': kwargs.ctx.author.avatar_url },
      'url': kwargs.url.format(kwargs.word),
      'fields': kwargs.fields
    })

  def _wiktionary(self, ctx, word, is_soft):
    return self._get_embed({ 
      'ctx': ctx,
      'word': word, 
      'url': "https://en.wiktionary.org/wiki/{}#English",
      'name': 'Wiktionary',
      'fields': [{ 'value': ety.tree(word).__str__() }] 
    })

  async def _etymonline(self, ctx, word, is_soft):
    url = "https://www.etymonline.com/search?q={}"
    async with aiohttp.ClientSession() as sess:
      async with sess.get(url.format(word)) as resp:
        soup = BeautifulSoup(await resp.text())
        results = soup.find_all('div', class_='word--C9UPa word_4pc--2SZw8')
        fields = []
        for result in results:
          entry_word, word_class = result.div.find('a').text.split(' ')
          if not is_soft and entry_word != word:
            continue
          value = result.div.section.find('p').text
          fields.append({ 'name': f'{entry_word} {word_class}', 'value': value })
    
    return self._get_embed({
      'ctx': ctx, 'word': word, 'url': url, 
      'name': 'Etymonline', 'fields': fields
    })

  async def _middle_english_compendium(self, ctx, word, is_soft):
    url = "https://quod.lib.umich.edu/m/middle-english-dictionary/dictionary?utf8=%E2%9C%93&search_field=anywhere&q={}"
    async with aiohttp.ClientSession() as sess:
      async with sess.get(url.format(word)) as resp1:
        soup1 = BeautifulSoup(await resp1.text())
        results = soup1.find_all('h3', class_='document-title-heading')
        fields = []
        for result in results:
          entry_word = result.a.text.strip()
          if not is_soft and entry_word != word:
            continue
          word_id = result.h3.find('a')['href'][1:]
          word_class = f'({result.h3.find('span', class_='index-pos').text})'
          async with sess.get("https://quod.lib.umich.edu" + word_id) as resp2:
            soup2 = BeautifulSoup(await resp2.text())
            value = soup2.find('span', class_='ETYM').text
            fields.append({ 'name': f'{entry_word} {word_class}', 'value': value })
    
    return self._get_embed({
      'ctx': ctx, 'word': word, 'url': url, 
      'name': 'Middle English Compendium', 'fields': fields
    })

  async def _bosworth_toller(self, ctx, word, is_soft):
    url = "https://bosworthtoller.com/search?q={}"
    async with aiohttp.ClientSession() as sess:
      async with sess.get(url.format(word)) as resp1:
        soup1 = BeautifulSoup(await resp1.text())
        results = soup1.find_all('header', class_='btd--search-entry-header')
        fields = []
        for result in results:
          entry_word = result.h3.find('a').text.strip()
          if not is_soft and entry_word != word:
            continue
          word_id = result.h3.find('a')['href'][1:]
          word_class = result.find('div').text.strip()
          async with sess.get("https://bosworthtoller.com/" + word_id) as resp2:
            soup2 = BeautifulSoup(await resp2.text())
            value = soup2.find('section', class_='btd--entry-etymology').text
            fields.append({ 'name': f'{entry_word} {word_class}', 'value': value })
          
    return self._get_embed({
      'ctx': ctx, 'word': word, 'url': url, 
      'name': 'Bosworth Toller', 'fields': fields
    })

  @commands.command()
  async def ety(self, ctx, word, *flags):
    is_soft = '-soft' in flags
    resources_ = flags[flags.index('-r') + 1:] if '-r' in flags else RESOURCES
    resources = [res.replace(',', '').strip() for res in resources_]

    resource_searcher_switch = {
      'wiki': self._wiktionary,
      'etym': self._etymonline,
      'mec': self._middle_english_compendium,
      'bostol': self._bosworth_toller}

    async with ctx.typing():
      for resource in resources:
        embed = await resource_searcher_switch.get(resource)(ctx, word, is_soft)
        paginator = disputils.BotEmbedPaginator(ctx, embed)
        self.bot.loop.create_task(paginator.run())
        


    