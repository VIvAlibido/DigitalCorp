"""Hacker News — via Algolia, want die API laat filteren op punten én datum.

HN is de snelste indicator van wat engineers vandaag daadwerkelijk bespreken;
de officiële Firebase-API kan niet filteren, Algolia wel.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..model import Item
from .basis import haal_op

API = "https://hn.algolia.com/api/v1/search_by_date"
ZOEKTERMEN = "AI OR LLM OR OpenAI OR Anthropic OR Claude OR GPT OR transformer OR agent"


def verzamel(cfg: dict) -> list[Item]:
    sinds = int((datetime.now(timezone.utc) - timedelta(days=2)).timestamp())
    data = haal_op(
        API,
        params={
            "query": ZOEKTERMEN,
            "tags": "story",
            "numericFilters": f"created_at_i>{sinds},points>{cfg.get('min_punten', 60)}",
            "hitsPerPage": cfg.get("max", 30),
        },
        accept_json=True,
    )
    if not data:
        return []

    items = []
    for hit in data.get("hits", []):
        discussie = f"https://news.ycombinator.com/item?id={hit['objectID']}"
        items.append(
            Item(
                titel=hit.get("title") or "",
                # Ask HN / Show HN zonder externe link: val terug op de draad zelf.
                url=hit.get("url") or discussie,
                bron="Hacker News",
                brontype="hackernews",
                gepubliceerd=datetime.fromtimestamp(hit["created_at_i"], tz=timezone.utc),
                samenvatting=(hit.get("story_text") or "")[:600],
                metriek={
                    "punten": hit.get("points", 0),
                    "reacties": hit.get("num_comments", 0),
                    "discussie": discussie,
                },
            )
        )
    return items
