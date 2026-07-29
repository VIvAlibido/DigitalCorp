"""Leesbaarheid van Nederlandse tekst volgens Flesch-Douma.

Flesch-Douma is de Nederlandse aanpassing van de Flesch-formule: Douma trok
van beide constanten tien procent af, omdat Nederlands meer woorden nodig
heeft dan Engels en Nederlandse woorden gemiddeld meer lettergrepen tellen.

    leesgemak = 206,835 − 0,93 × (woorden/zin) − 77 × (lettergrepen/woord)

Waarschuwing die bij deze formule hoort en die we hier expliciet maken:
leesbaarheidsformules zijn zwakke voorspellers van begrip. Ze meten
zinslengte en woordlengte, meer niet. Een tekst vol korte, betekenisloze
woorden scoort uitstekend. Gebruik de score om uitschieters te vinden, nooit
als bewijs dat een tekst goed is.
"""

from __future__ import annotations

import re

# Klinkercombinaties die in het Nederlands één lettergreep vormen.
_TWEEKLANKEN = (
    "aai", "ooi", "oei", "eeu", "ieu",
    "aa", "ee", "oo", "uu", "ei", "ij", "ou", "au", "ui", "oe", "ie", "eu",
)
_KLINKERS = set("aeiouy")


def tel_lettergrepen(woord: str) -> int:
    """Benadering: tel klinkergroepen, met tweeklanken als één groep.

    Niet perfect — 'zee-egel' en 'reageren' worden misgeteld — maar de fout
    middelt uit over een zin en dat is voldoende voor een indexcijfer.
    """
    woord = re.sub(r"[^a-zà-ÿ]", "", woord.lower())
    if not woord:
        return 0

    # Vervang tweeklanken door één markering zodat ze als één groep tellen.
    for tweeklank in _TWEEKLANKEN:
        woord = woord.replace(tweeklank, "@")

    groepen = 0
    vorige_was_klinker = False
    for teken in woord:
        is_klinker = teken == "@" or teken in _KLINKERS
        if is_klinker and not vorige_was_klinker:
            groepen += 1
        vorige_was_klinker = is_klinker

    return max(groepen, 1)


def _zinnen(tekst: str) -> int:
    return max(len([z for z in re.split(r"[.!?…]+", tekst) if z.strip()]), 1)


def _woorden(tekst: str) -> list[str]:
    return re.findall(r"[\w'-]+", tekst)


def flesch_douma(tekst: str) -> float:
    """Leesgemak: hoger is makkelijker. Boven de 60 leest vlot."""
    woorden = _woorden(tekst)
    if not woorden:
        return 0.0
    lettergrepen = sum(tel_lettergrepen(w) for w in woorden)
    return round(
        206.835
        - 0.93 * (len(woorden) / _zinnen(tekst))
        - 77 * (lettergrepen / len(woorden)),
        1,
    )


def niveau(score: float) -> str:
    """Vertaalt de score naar het taalniveau dat er ongeveer bij hoort."""
    if score >= 80:
        return "A2 — heel eenvoudig"
    if score >= 60:
        return "B1 — begrijpelijk voor een breed publiek"
    if score >= 40:
        return "B2 — vraagt aandacht"
    if score >= 20:
        return "C1 — moeilijk"
    return "C2 — zeer moeilijk"
