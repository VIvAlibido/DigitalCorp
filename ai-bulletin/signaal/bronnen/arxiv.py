"""arXiv — nieuwe preprints in de AI-categorieën."""

from __future__ import annotations

from ..model import Item
from .basis import haal_op, parse_feed, strip_html

API = "http://export.arxiv.org/api/query"


def verzamel(cfg: dict) -> list[Item]:
    categorieen = cfg.get("categorieen") or ["cs.AI"]
    query = " OR ".join(f"cat:{c}" for c in categorieen)
    xml = haal_op(
        API,
        params={
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": cfg.get("max", 60),
        },
    )
    if not xml:
        return []

    items = []
    for entry in parse_feed(xml):
        items.append(
            Item(
                titel=entry["titel"],
                url=entry["url"],
                bron="arXiv",
                brontype="arxiv",
                gepubliceerd=entry["gepubliceerd"],
                samenvatting=strip_html(entry["samenvatting"]),
                metriek={"categorieen": categorieen},
            )
        )
    return items
