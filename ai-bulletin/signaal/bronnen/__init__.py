"""Bronnen leveren kandidaat-items aan de pijplijn.

Elke bron exporteert `verzamel(cfg) -> list[Item]` en mag falen zonder de run
te breken; de pijplijn logt en gaat door met wat er wél binnenkwam.
"""

from __future__ import annotations

import logging

from . import arxiv, github, hackernews, huggingface, instagram, rss

log = logging.getLogger(__name__)

# Sleutel komt overeen met de blokken onder `bronnen:` in config.yaml.
REGISTER = {
    "arxiv": arxiv.verzamel,
    "github": github.verzamel,
    "huggingface": huggingface.verzamel,
    "hackernews": hackernews.verzamel,
    "rss": rss.verzamel,
    "rss_nl": rss.verzamel_nl,
    "instagram": instagram.verzamel,
}

__all__ = ["REGISTER", "verzamel_alles"]


def verzamel_alles(config: dict) -> list:
    """Draai elke geactiveerde bron en plak de resultaten aan elkaar."""
    items = []
    for naam, bron_cfg in (config.get("bronnen") or {}).items():
        if not (bron_cfg or {}).get("actief"):
            continue
        functie = REGISTER.get(naam)
        if functie is None:
            log.warning("onbekende bron in config: %s", naam)
            continue
        try:
            nieuw = functie(bron_cfg)
        except Exception:  # noqa: BLE001 - één kapotte bron mag de run niet stoppen
            log.exception("bron %s faalde", naam)
            continue
        log.info("bron %s leverde %d items", naam, len(nieuw))
        items.extend(nieuw)
    return items
