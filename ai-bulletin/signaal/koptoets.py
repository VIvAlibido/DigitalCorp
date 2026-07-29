"""Automatische controle op koppen.

De kop bepaalt of een bericht gelezen wordt, en koppen falen vrijwel altijd op
hetzelfde: ze zijn wel waar, maar zeggen niets. Onderzoek naar wat koppen laat
converteren wijst consistent één ding aan — specificiteit draagt zijn eigen
bewijs, vaagheid roept scepsis op. "52,7% hoger dan de norm" verslaat "meer dan
50%", en "bijna driekwart van de aanvallen" verslaat niets.

Deze module toetst dat mechanisch. Hij kan niet beoordelen of een kop goed is,
alleen of hij aantoonbaar slecht is — dat scheelt de helft van het werk.
"""

from __future__ import annotations

import re

MAX_TEKENS = 70

# Vage hoeveelheden: het getal is er wel, maar zonder scherpte.
VAGE_TERMEN = (
    "bijna driekwart", "driekwart", "ruim de helft", "een aantal", "diverse",
    "sommige", "meerdere", "steeds meer", "steeds vaker", "veel ", "vele ",
    "flink", "fors", "aanzienlijk", "behoorlijk", "grotendeels", "diverse",
)

# Naamwoordstijl: een gebeurtenis vermomd als abstractie.
NAAMWOORDSTIJL = (
    "de invoering van", "het gebruik van", "de toepassing van", "de inzet van",
    "de implementatie van", "de ontwikkeling van", "de introductie van",
)

# Lijdende vorm: hulpwerkwoord gevolgd door iets dat op een voltooid deelwoord
# lijkt. Nederlandse deelwoorden zijn niet aan hun uitgang te herkennen — 'wet'
# en 'herbouwd' eindigen allebei op een medeklinker — dus toetsen we op de
# voorvoegsels waarmee deelwoorden vrijwel altijd beginnen.
# 'is' en 'zijn' staan er bewust niet bij: "is bekend" en "is beter" zijn geen
# lijdende vorm, en dit is een blokkerende controle. Liever een enkele gemiste
# dan een goede kop die ten onrechte wordt tegengehouden.
_LIJDEND = re.compile(
    r"\b(wordt|worden|werd|werden)\s+"
    r"(ge|her|ver|be|ont|aan|af|uit|in|op|over|onder|door)\w{2,}\b",
    re.IGNORECASE,
)

_TIJDWOORDEN = re.compile(
    r"\b(zondag|maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|"
    r"gisteren|vandaag|morgen|overmorgen|volgende week|"
    r"januari|februari|maart|april|mei|juni|juli|augustus|september|"
    r"oktober|november|december)\b",
    re.IGNORECASE,
)


def controleer_kop(kop: str) -> list[str]:
    """Geeft de gevonden bezwaren terug. Lege lijst betekent: geen bezwaar."""
    bezwaren: list[str] = []
    laag = kop.lower()

    if len(kop) > MAX_TEKENS:
        bezwaren.append(f"te lang ({len(kop)} tekens, max {MAX_TEKENS})")

    if not kop.strip():
        return ["leeg"]

    for term in VAGE_TERMEN:
        if term in laag:
            bezwaren.append(f"vage hoeveelheid: '{term.strip()}'")

    for term in NAAMWOORDSTIJL:
        if term in laag:
            bezwaren.append(f"naamwoordstijl: '{term}'")

    if "!" in kop:
        bezwaren.append("uitroepteken")

    # Lijdende vorm zonder handelende partij: "wordt herbouwd" verzwijgt wie.
    # Mét "door ..." is het geen bezwaar, dan staat de actor er alsnog.
    if _LIJDEND.search(kop) and " door " not in laag:
        bezwaren.append("lijdende vorm zonder handelende partij")

    # Minstens één concreet houvast: een getal, een eigennaam of een tijdstip.
    heeft_getal = bool(re.search(r"\d", kop))
    heeft_naam = any(woord[:1].isupper() for woord in kop.split()[1:])
    heeft_tijd = bool(_TIJDWOORDEN.search(kop))
    if not (heeft_getal or heeft_naam or heeft_tijd):
        bezwaren.append("niets specifieks: geen getal, naam of tijdstip")

    return bezwaren


def toets_editie(koppen: list[str]) -> dict[str, list[str]]:
    """Toetst alle koppen van een editie; retourneert alleen wat mis is."""
    return {kop: bezwaren for kop in koppen if (bezwaren := controleer_kop(kop))}
