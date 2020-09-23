""" Row formatting constants (Bot) """
letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
headers_base = ["Word", "Meaning", "Kind", "Forebear", "Whence", "🔨", "Notes"]
furls = [
    "https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit?gid=0&range={}{}", 
    "https://docs.google.com/spreadsheets/d/16f4aeFsNC4oHt3zt-XskiEzcQwU1u-rdh6P8rLCEDOM/edit#gid=1186039826&range={}{}", 
    "https://docs.google.com/spreadsheets/d/16f4aeFsNC4oHt3zt-XskiEzcQwU1u-rdh6P8rLCEDOM/edit#gid=1193230534&range={}{}"]
help_field = "Use /help for command usage. If the bot is typing it is still generating new results that the page number might not reflect"
statuses = ["In Wordbook", "Offered", "Rejected"]


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