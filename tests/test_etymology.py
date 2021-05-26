import unittest
import asyncio
from ..cogs import Etymology

class TestEtymology(unittest.TestCase):
  ety = Etymology()
  def test_scrape_fields(self):
    self.assertEqual(asyncio.run(ety.scrape_fields('book', 'etym')), [
      { 'name': 'book (n.)', 
        'value': 'Old English boc "book, writing, written document," generally referred (despite phonetic difficulties) to Proto-Germanic *bōk(ō)-, from *bokiz "beech" (source also of German Buch "book" Buche "beech;" see beech), the notion being of beechwood tablets on which runes were inscribed; but it may be from the tree itself (people still carve initials in them).' },
      { 'name': 'book (v.)',
        'value': 'Old English bocian "to grant or assign by charter," from book (n.). Meaning "to enter into a book, record" is early 13c. Meaning "to register a name for a seat or place; issue (railway) tickets" is from 1841; "to engage a performer as a guest" is from 1872. U.S. student slang meaning "to depart hastily, go fast" is by 1977, of uncertain signification. Related: Booked; booking.'}])
    self.assertEqual(asyncio.run(ety.scrape_fields('drinken', 'mec')), [
      { 'value': 'OE drincan; sg. 3 drincþ, drinceþ; p. dranc, dronc; pl. druncon; ppl. druncen & gedrincan.' }])
    self.assertEqual(asyncio.run(ety.scrape_fields('boga', 'bostol')), [
      { 'name': 'boga (n.)',
        'value': '[Wyc. bowe, bouwe: Laym. boȝe, bowe; O. Sax. bogo, m: Frs. boage: O. Frs. boga, m: Dut. boog, m: Ger. boge, bogen, m: M. H. Ger. boge, m: O. H. Ger. bogo, m: Dan. bue, c: Swed. båge, m: Icel. bogi, m. arcus.]'}])


if __name__ == '__main__':
  unittest.main()