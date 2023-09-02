import re

import aiohttp
import asyncio
import async_timeout
import discord
from aioify import aioify
from discord.ext import commands
import disputils
import ety
from bs4 import BeautifulSoup
from wiktionaryparser import WiktionaryParser

RESOURCES = ['wiki', 'etym', 'mec', 'bostol']
props = {
    'etym': {
        'name': 'Etymonline',
        'list': {
            'url': "https://www.etymonline.com/search?q={}",
            'el': 'div',
            'class_': 'word--C9UPa word_4pc--2SZw8'}},
    'mec': {
        'name': 'Middle English Compendium',
        'list': {
            'url': "https://quod.lib.umich.edu/m/middle-english-dictionary/dictionary?utf8=%E2%9C%93&search_field=anywhere&q={}",
            'el': 'h3',
            'class_': 'document-title-heading'},
        'item': {
            'url': "https://quod.lib.umich.edu",
            'el': 'span',
            'class_': 'ETYM'}},
    'bostol': {
        'name': 'Bosworth Toller',
        'list': {
            'url': "https://bosworthtoller.com/search?q={}",
            'el': 'header',
            'class_': 'btd--search-entry-header'},
        'item': {
            'url': "https://bosworthtoller.com/",
            'el': 'section',
            'class_': 'btd--entry-etymology'}},
    'wiki': {
        'name': 'Wiktionary',
        'list': {
            'url': "https://en.wiktionary.org/wiki/{}#English"}}
}


class Etymology(commands.Cog):

    def __init__(self, bot=None):
        self.bot = bot

    @aioify
    def _wiktionaryparser(self, word):
        results = WiktionaryParser().fetch(word)
        fieldsets = []

        for etym in results:
            if 'etymology' in etym:
                parts = []
                for defn in etym['definitions']:
                    parts.append('**{pos}.**\n-{defs}'.format(pos=defn['partOfSpeech'], defs='\n-'.join(defn['text'])))
                defns = "\n".join(parts)

                fieldsets.append(
                    [
                        {'value': etym['etymology'], 'name': 'Etymology'},
                        {'value': defns, 'name': 'Definitions'},
                        {'value': '\n'.join(etym['pronunciations']['text']), 'name': 'Pronunciations'},
                    ]
                )

        return fieldsets


    @staticmethod
    def parse_entry(result, resource):
        if resource == 'etym':
            word, class_ = result.div.find('a').text.split()
            return {'word': word, 'class_': class_, 'id': None}
        elif resource == 'mec':
            return {
                'word': result.a.text.strip(),
                'class_': f"({(result.h3 or result).find('span', class_='index-pos').text})",
                'id': (result.h3 or result).find('a')['href'][1:]
            }
        elif resource == 'bostol':
            return {
                'word': (result.h3 or result).find('a').text.strip(),
                'class_': result.find('div').text.strip(),
                'id': (result.h3 or result).find('a')['href'][1:]
            }
        return {}

    async def scrape_fields(self, word, resource, is_soft=False):
        if resource == 'wiki':
            return await self._wiktionaryparser(word)
        tags = props[resource]
        url = tags['list']['url']
        url_item = tags.get('item', {}).get('url')
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url.format(word)) as resp1:
                soup1 = BeautifulSoup(await resp1.text())
                results = soup1.find_all(tags['list'].get('el'), class_=tags['list']['class_'])
                fields = []
                for result in results:
                    entry = self.parse_entry(result, resource)
                    if not is_soft and entry['word'] != word:
                        continue
                    if url_item:
                        async with sess.get(url_item + entry['id']) as resp2:
                            soup2 = BeautifulSoup(await resp2.text())
                            try:
                                value = soup2.find(tags['list'].get('el'), class_=tags['list']['class_']).get_text()
                            except (AttributeError, KeyError) as error:
                                print(error)
                                continue
                    else:
                        try:
                            value = result.div.section.find('p').text  # ETYMONLINE
                        except (AttributeError, KeyError) as error:
                            print(error)
                            continue
                    fields.append({'name': f"{entry['word']} {entry['class_']}", 'value': value})
                return [fields]

    @commands.command(aliases=["etymology"])
    async def ety(self, ctx, word, *flags):
        """Look up the etymology of a word. Add -soft to the end to look up words that are parts of other words. -r does something too I don't remember though"""
        is_soft = '-soft' in flags
        resources_ = flags[flags.index('-r') + 1:] if '-r' in flags else RESOURCES
        resources = [res.replace(',', '').strip() for res in resources_]

        def format_embed(fields, resource):
            embed = discord.Embed.from_dict({
                'color': 0xDD0000,
                'title': word,
                'author': {'name': props[resource]['name'], 'icon_url': str(ctx.author.avatar.url)},
                'url': props[resource]['list']['url'].format(word),
                'fields': fields
            })

            return embed

        async with ctx.typing():
            embeds = [format_embed([{'value': ety.tree(word).__str__(), 'name': word}], 'wiki')]

            for resource in resources:
                for fields in await self.scrape_fields(word, resource, is_soft):
                    embeds.append(format_embed(fields, resource))

            # from pprint import pprint
            # pprint([embed.to_dict() for embed in embeds])
            paginator = disputils.BotEmbedPaginator(ctx, embeds)
            ctx.bot.loop.create_task(paginator.run())
