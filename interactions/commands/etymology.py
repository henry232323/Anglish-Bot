"""
Etymology command: /ety with -soft and -r flags.
Sync HTTP and sync wiktionary for Lambda.
"""
import re
from typing import Any

import requests
from bs4 import BeautifulSoup
from wiktionaryparser import WiktionaryParser

from discord_utils import pagination_buttons

RESOURCES = ["wiki", "etym", "mec", "bostol"]
PROPS = {
    "etym": {
        "name": "Etymonline",
        "list": {
            "url": "https://www.etymonline.com/search?q={}",
            "el": "div",
            "class_": "word--C9UPa word_4pc--2SZw8",
        },
    },
    "mec": {
        "name": "Middle English Compendium",
        "list": {
            "url": "https://quod.lib.umich.edu/m/middle-english-dictionary/dictionary?utf8=%E2%9C%93&search_field=anywhere&q={}",
            "el": "h3",
            "class_": "document-title-heading",
        },
        "item": {"url": "https://quod.lib.umich.edu", "el": "span", "class_": "ETYM"},
    },
    "bostol": {
        "name": "Bosworth Toller",
        "list": {
            "url": "https://bosworthtoller.com/search?q={}",
            "el": "header",
            "class_": "btd--search-entry-header",
        },
        "item": {"url": "https://bosworthtoller.com/", "el": "section", "class_": "btd--entry-etymology"},
    },
    "wiki": {
        "name": "Wiktionary",
        "list": {"url": "https://en.wiktionary.org/wiki/{}#English"},
    },
}


def _wiktionaryparser(word: str) -> list:
    results = WiktionaryParser().fetch(word)
    fieldsets = []
    for etym in results:
        if "etymology" not in etym:
            continue
        parts = []
        for defn in etym.get("definitions", []):
            text = defn.get("text", [])
            parts.append(
                "**{}.**\n-{}".format(defn.get("partOfSpeech", ""), "\n-".join(text))
            )
        defns = "\n".join(parts)
        prons = "\n".join(etym.get("pronunciations", {}).get("text", []))
        fieldsets.append(
            [
                {"value": etym["etymology"], "name": "Etymology"},
                {"value": defns, "name": "Definitions"},
                {"value": prons, "name": "Pronunciations"},
            ]
        )
    return fieldsets


def _parse_entry(result, resource: str) -> dict:
    try:
        if resource == "etym":
            a = result.div.find("a")
            if not a:
                return {}
            word, class_ = a.text.split(None, 1) if a.text else ("", "")
            return {"word": word, "class_": class_, "id": None}
        if resource == "mec":
            a = result.find("a")
            h3 = result.find("h3") or result
            span = h3.find("span", class_="index-pos")
            link = h3.find("a", href=True)
            return {
                "word": a.text.strip() if a else "",
                "class_": f"({span.text})" if span else "",
                "id": link["href"].lstrip("/") if link else "",
            }
        if resource == "bostol":
            h3 = result.find("h3") or result
            a = h3.find("a")
            div = result.find("div")
            return {
                "word": a.text.strip() if a else "",
                "class_": div.text.strip() if div else "",
                "id": (a.get("href") or "").lstrip("/"),
            }
    except Exception:
        pass
    return {}


def _scrape_fields_sync(word: str, resource: str, is_soft: bool = False) -> list:
    if resource == "wiki":
        return _wiktionaryparser(word)
    tags = PROPS[resource]
    url = tags["list"]["url"].format(word)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    el = tags["list"].get("el")
    class_ = tags["list"].get("class_")
    results = soup.find_all(el, class_=class_) if el and class_ else []
    if not results and el:
        results = soup.find_all(el)
    fields = []
    url_item = tags.get("item", {}).get("url")
    for result in results:
        entry = _parse_entry(result, resource)
        if not entry or not entry.get("word"):
            continue
        if not is_soft and entry["word"].lower() != word.lower():
            continue
        if url_item and entry.get("id"):
            item_url = url_item.rstrip("/") + "/" + entry["id"].lstrip("/")
            r2 = requests.get(item_url, timeout=15)
            r2.raise_for_status()
            soup2 = BeautifulSoup(r2.text, "html.parser")
            el2 = tags["item"].get("el")
            class2 = tags["item"].get("class_")
            node = soup2.find(el2, class_=class2)
            value = node.get_text() if node else ""
        else:
            try:
                value = result.div.section.find("p").text
            except (AttributeError, KeyError):
                continue
        name = f"{entry['word']} {entry.get('class_', '')}".strip()
        fields.append({"name": name[:256], "value": (value or "")[:1024]})
    return [fields] if fields else []


def run_etymology(word: str, flags_str: str, author_avatar: str) -> list[dict]:
    """Build list of embed dicts for /ety."""
    is_soft = "-soft" in (flags_str or "")
    resources_str = ""
    if flags_str and "-r" in flags_str:
        idx = flags_str.index("-r") + 2
        resources_str = flags_str[idx:].strip()
    resources = [r.strip().replace(",", "") for r in resources_str.split()] if resources_str else RESOURCES

    embeds = []
    # ety.tree(word) for first wiki embed
    try:
        import ety
        tree_str = str(ety.tree(word))
    except Exception:
        tree_str = "Etymology tree unavailable."
    wiki_url = PROPS["wiki"]["list"]["url"].format(word)
    embeds.append({
        "color": 0xDD0000,
        "title": word,
        "author": {"name": "Wiktionary", "icon_url": author_avatar},
        "url": wiki_url,
        "fields": [{"name": word, "value": tree_str[:1024]}],
    })

    for res in resources:
        if res not in PROPS:
            continue
        for fields in _scrape_fields_sync(word, res, is_soft):
            if not fields:
                continue
            embeds.append({
                "color": 0xDD0000,
                "title": word,
                "author": {"name": PROPS[res]["name"], "icon_url": author_avatar},
                "url": PROPS[res]["list"]["url"].format(word),
                "fields": fields,
            })
    return embeds


# custom_id for ety pagination: "E:{word}:{flags}:{page}" - flags may be long; use short codes
def _ety_flags_encode(flags_str: str) -> str:
    s = (flags_str or "").replace(" ", "_")[:30]
    return s or "."


def _ety_flags_decode(s: str) -> str:
    return (s or ".").replace("_", " ") if s != "." else ""


def parse_ety_custom_id(custom_id: str) -> dict | None:
    """E:word:flags_encoded:page -> {word, flags, page}."""
    parts = custom_id.split(":")
    if len(parts) < 4 or parts[0] != "E":
        return None
    return {"word": parts[1], "flags": _ety_flags_decode(parts[2]), "page": int(parts[3])}


def build_ety_custom_id(word: str, flags_str: str, page: int) -> str:
    # custom_id max 100 chars
    w = (word or "")[:35]
    encoded = _ety_flags_encode(flags_str)
    return f"E:{w}:{encoded}:{page}"


def handle_ety_command(interaction: dict, author_avatar: str) -> dict:
    """Handle /ety. Returns response with embeds + buttons."""
    from discord_utils import response_message

    data = interaction.get("data", {})
    options = {o["name"]: o.get("value") for o in data.get("options", [])}
    word = (options.get("word") or "").strip()
    flags = (options.get("flags") or "") if isinstance(options.get("flags"), str) else ""
    if not word:
        return response_message(content="Please provide a word.")

    embeds = run_etymology(word, flags, author_avatar)
    if not embeds:
        return response_message(content="No etymology results found.")

    total = len(embeds)
    for i, emb in enumerate(embeds):
        emb.setdefault("footer", {})["text"] = f"({i + 1}/{total})"

    if total == 1:
        return response_message(embeds=[embeds[0]])

    base = build_ety_custom_id(word, flags, 0).rsplit(":", 1)[0]
    components = pagination_buttons(base, 0, total)
    return response_message(embeds=[embeds[0]], components=components)


def handle_ety_pagination(custom_id: str, author_avatar: str) -> dict | None:
    """Handle ety button click. Re-runs etymology and returns UPDATE_MESSAGE."""
    from discord_utils import response_update_message

    parsed = parse_ety_custom_id(custom_id)
    if not parsed:
        return None
    embeds = run_etymology(parsed["word"], parsed["flags"], author_avatar)
    total = len(embeds)
    page = max(0, min(parsed["page"], total - 1))
    emb = embeds[page]
    emb.setdefault("footer", {})["text"] = f"({page + 1}/{total})"
    base = build_ety_custom_id(parsed["word"], parsed["flags"], page).rsplit(":", 1)[0]
    components = pagination_buttons(base, page, total)
    return response_update_message(embeds=[emb], components=components)
