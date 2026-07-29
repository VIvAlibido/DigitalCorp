"""Voorselectie: goedkoop filteren voordat de dure LLM-jury aan zet komt.

Deze score bepaalt niet wat er in de editie komt — dat doet de LLM. Hij bepaalt
alleen welke ~40 van de ~200 kandidaten de LLM überhaupt te zien krijgt.
"""

from __future__ import annotations

import math

from .model import Item


def _recency(item: Item, halfwaardetijd: float) -> float:
    """Exponentieel verval: 1.0 nu, 0.5 na één halfwaardetijd."""
    return math.pow(0.5, item.leeftijd_uren / max(halfwaardetijd, 1.0))


def _engagement(item: Item) -> float:
    """Log-geschaald, zodat één viral item de rest niet wegdrukt."""
    m = item.metriek
    ruw = 0.0
    if item.brontype == "github":
        ruw = m.get("sterren_per_dag", 0) * 10
    elif item.brontype == "hackernews":
        ruw = m.get("punten", 0) + m.get("reacties", 0) * 2
    elif item.brontype == "huggingface":
        ruw = m.get("likes", 0) * 5 + m.get("downloads", 0) / 100
    elif item.brontype == "instagram":
        ruw = m.get("likes", 0) / 10 + m.get("reacties", 0)
    return math.log1p(max(ruw, 0.0))


def is_nl_relevant(item: Item, signaalwoorden: list[str]) -> bool:
    tekst = f"{item.titel} {item.samenvatting} {item.bron}".lower()
    return any(woord in tekst for woord in signaalwoorden)


def scoor(items: list[Item], config: dict) -> list[Item]:
    """Zet `voorscore` en `nl_relevant` op elk item. Muteert en retourneert."""
    scoring = config.get("scoring", {})
    gewichten = scoring.get("brontype_gewicht", {})
    halfwaardetijd = scoring.get("recency_halfwaardetijd_uren", 18)
    nl_bonus = scoring.get("nl_relevantie_bonus", 2.5)
    signaalwoorden = [w.lower() for w in config.get("nl_signaalwoorden", [])]

    for item in items:
        item.nl_relevant = is_nl_relevant(item, signaalwoorden)

        basis = gewichten.get(item.brontype, 1.0)
        score = basis * (2.0 * _recency(item, halfwaardetijd) + _engagement(item))
        if item.nl_relevant:
            score += nl_bonus
        # Meerdere bronnen over hetzelfde onderwerp: zie dedupe.py.
        score += 0.8 * len(item.metriek.get("ook_gemeld_door", []))

        item.voorscore = round(score, 3)

    return items


def filter_op_leeftijd(items: list[Item], max_uren: float) -> list[Item]:
    return [i for i in items if i.leeftijd_uren <= max_uren]


def shortlist(items: list[Item], n: int) -> list[Item]:
    """Top-n op voorscore, met een gegarandeerde plek voor NL-relevante items.

    Zonder dit quotum verdrinken Nederlandse items in de internationale
    volumes — en juist die zijn het bestaansrecht van deze nieuwsbrief.
    """
    gesorteerd = sorted(items, key=lambda i: i.voorscore, reverse=True)
    nl_quotum = max(n // 4, 1)

    nl_items = [i for i in gesorteerd if i.nl_relevant][:nl_quotum]
    gekozen = list(nl_items)
    for item in gesorteerd:
        if len(gekozen) >= n:
            break
        if item not in gekozen:
            gekozen.append(item)

    return sorted(gekozen, key=lambda i: i.voorscore, reverse=True)
