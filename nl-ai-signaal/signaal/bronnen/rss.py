"""RSS/Atom — labs, vendors en (los daarvan) Nederlandstalige media.

`verzamel_nl` is dezelfde logica met een ander brontype, zodat de scoring
Nederlandstalige bronnen zwaarder kan wegen zonder aparte code.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from ..model import Item
from .basis import haal_op, parse_feed, strip_html

# Feeds als Tweakers zijn breed; filter op AI-signaalwoorden zodat er geen
# telefoonreviews in de editie belanden.
AI_FILTER = (
    "ai", "a.i.", "kunstmatige intelligentie", "llm", "taalmodel", "chatbot",
    "machine learning", "openai", "anthropic", "claude", "gpt", "gemini",
    "algoritme", "algoritmes", "neuraal", "agent", "copilot", "mistral",
)


def _domein(url: str) -> str:
    netloc = urlsplit(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def _lees_feeds(feeds: list[str], brontype: str, filteren: bool) -> list[Item]:
    items: list[Item] = []
    for feed_url in feeds:
        xml = haal_op(feed_url)
        if not xml:
            continue
        for entry in parse_feed(xml):
            titel = strip_html(entry["titel"])
            samenvatting = strip_html(entry["samenvatting"])
            if filteren and not any(w in f"{titel} {samenvatting}".lower() for w in AI_FILTER):
                continue
            items.append(
                Item(
                    titel=titel,
                    url=entry["url"],
                    bron=_domein(feed_url),
                    brontype=brontype,
                    gepubliceerd=entry["gepubliceerd"],
                    samenvatting=samenvatting,
                )
            )
    return items


def verzamel(cfg: dict) -> list[Item]:
    # Labs/vendors publiceren alleen AI-nieuws; filteren zou onterecht snoeien.
    return _lees_feeds(cfg.get("feeds") or [], "rss", filteren=False)


def verzamel_nl(cfg: dict) -> list[Item]:
    return _lees_feeds(cfg.get("feeds") or [], "rss_nl", filteren=True)
