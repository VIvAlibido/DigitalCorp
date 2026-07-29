"""Ontdubbelen: dezelfde gebeurtenis komt via meerdere bronnen binnen.

Een modelrelease staat tegelijk op Hacker News, op de vendor-blog en op
Tweakers. Dat is één feit, geen drie. We clusteren op URL en op titel-
gelijkenis en houden per cluster het item met de hoogste voorscore over,
maar bewaren wel welke bronnen erover schreven — dat is zelf een signaal.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from .model import Item

# Woorden die vrijwel elke AI-kop bevat en dus niets onderscheiden.
_STOPWOORDEN = {
    "the", "a", "an", "and", "or", "for", "with", "new", "introducing",
    "de", "het", "een", "en", "van", "voor", "met", "nieuwe", "nieuw",
    "ai", "model", "models", "llm",
}


def _tokens(titel: str) -> list[str]:
    zonder_leestekens = re.sub(r"[^\w\s]", " ", titel.lower())
    return [w for w in zonder_leestekens.split() if w not in _STOPWOORDEN and len(w) > 2]


def _normaliseer(titel: str) -> str:
    return " ".join(_tokens(titel))


def zelfde_woord(a: str, b: str) -> bool:
    """Tolerant vergelijken van Nederlandse verbuigingen.

    'contextvenster' en 'contextvensters' zijn hetzelfde woord; 'transformer' en
    'transparant' niet, ook al delen ze vijf letters, en 'productie' en
    'producent' niet, ook al delen ze er zes. Naast een minimale prefixlengte
    geldt daarom dat die prefix vrijwel het hele kortste woord moet beslaan.
    """
    if a == b:
        return True
    kortste = min(len(a), len(b))
    gedeeld = 0
    for teken_a, teken_b in zip(a, b):
        if teken_a != teken_b:
            break
        gedeeld += 1
    return gedeeld >= 5 and gedeeld / kortste >= 0.75


def _token_overlap(a: list[str], b: list[str]) -> float:
    """Aandeel van de kortste titel dat in de langste terugkomt."""
    if len(a) < 3 or len(b) < 3:
        return 0.0
    treffers = sum(1 for woord in a if any(zelfde_woord(woord, ander) for ander in b))
    # Eén gedeeld woord ('OpenAI', 'model') zegt niets over hetzelfde onderwerp.
    if treffers < 2:
        return 0.0
    return treffers / min(len(a), len(b))


def _gelijkenis(a: str, b: str) -> float:
    """Maximum van tekengelijkenis en woordoverlap.

    Tekenniveau vangt herformuleringen van dezelfde kop; woordniveau vangt
    vertalingen en verbuigingen die er als tekenreeks anders uitzien.
    """
    if not a or not b:
        return 0.0
    return max(
        SequenceMatcher(None, a, b).ratio(),
        _token_overlap(a.split(), b.split()),
    )


def ontdubbel(items: list[Item], drempel: float = 0.72) -> list[Item]:
    """Cluster items en geef één representant per cluster terug.

    Items moeten al gescoord zijn; de hoogste voorscore wint het cluster.
    """
    gesorteerd = sorted(items, key=lambda i: i.voorscore, reverse=True)

    gekozen: list[Item] = []
    genormaliseerd: list[str] = []
    gezien_urls: set[str] = set()

    for item in gesorteerd:
        if item.url in gezien_urls:
            continue

        norm = _normaliseer(item.titel)
        dubbel_van = None
        for index, bestaande_norm in enumerate(genormaliseerd):
            if _gelijkenis(norm, bestaande_norm) >= drempel:
                dubbel_van = index
                break

        if dubbel_van is not None:
            winnaar = gekozen[dubbel_van]
            # Meerdere onafhankelijke bronnen = sterker signaal.
            ook_gemeld = winnaar.metriek.setdefault("ook_gemeld_door", [])
            if item.bron != winnaar.bron and item.bron not in ook_gemeld:
                ook_gemeld.append(item.bron)
            gezien_urls.add(item.url)
            continue

        gekozen.append(item)
        genormaliseerd.append(norm)
        gezien_urls.add(item.url)

    return gekozen
