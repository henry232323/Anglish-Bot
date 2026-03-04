DESCRIPTION = """
A bot for looking up words in the Anglish wordbook.
Invite: https://discordapp.com/oauth2/authorize?client_id=671065305681887238&permissions=19520&scope=bot
Wordbook: https://docs.google.com/spreadsheets/d/1y8_11RDvuCRyUK_MXj5K7ZjccgCUDapsPDI5PjaEkMw/edit

COMMANDS:

/help      --> how to use

/m <word>  --> exact match in all languages
/am <word> --> exact match in Anglish
/em <word> --> exact match in English

/f <word>  --> soft match in all languages
/af <word> --> soft match in Anglish
/ef <word> --> soft match in English

/ety <word> --> etymology search of exact match in all resources
Flags:
    -soft                       --> specifies soft match
    -r     wiki|etym|mec|bostol --> specifies resources to search as comma-separated list

What is a "soft match"?
Unlike a "hard match" (exact), a soft match (/f) will return all results that contain the query.
Ex: /f brook --> upbrook, abrook, brook

Bugs / Feedback? Mention @henry232323
"""


def handle_help_command() -> dict:
    """Return embed for /help."""
    return {
        "type": 4,
        "data": {
            "embeds": [{
                "color": 0xDD0000,
                "title": "Anglish Bot",
                "description": DESCRIPTION.strip(),
                "allowed_mentions": {"parse": []},
            }],
            "allowed_mentions": {"parse": []},
        },
    }
