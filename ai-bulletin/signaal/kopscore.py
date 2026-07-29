"""Koppen scoren — om varianten te rángschikken, niet om ze goed te keuren.

Onderzoek naar kop-analysetools is eensluidend en onaangenaam: de correlatie
tussen hun scores en werkelijke prestaties is zwak. Ze meten of een kop netjes
gebouwd is, niet of hij de juiste lezer op het juiste moment raakt. Voor een
publiek dat honderden vergelijkbare koppen heeft gezien, zijn de "bewezen
patronen" die zulke tools belonen juist de patronen die genegeerd worden.

Daarom gebruiken we de score hier op precies één manier: om varianten van
hetzelfde bericht onderling te vergelijken. Dat is de vergelijking waarvoor
een zwakke maat wél deugt, omdat alles behalve de formulering gelijk blijft.
Een absoluut oordeel ("83 van de 100, dus goed") geeft deze module bewust
niet — het cijfer bestaat alleen ten opzichte van een alternatief.

De harde afkeuringen staan in koptoets.py en wegen zwaarder dan elke score:
een kop met een blokkade gaat niet mee, hoe hoog hij verder ook scoort.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import koptoets
from .dedupe import zelfde_woord
from .leesbaarheid import flesch_douma

# Optimaal venster voor een kop in de nieuwsbrief zelf.
IDEALE_LENGTE = (45, 65)
# Wat op een telefoon zichtbaar blijft voordat de client afkapt.
ZICHTBARE_VOORLOOP = 40

# Woorden die een concreet gevolg aankondigen. Geen "power words" in de
# marketingzin — die vallen in een technisch publiek juist door de mand —
# maar werkwoorden en zelfstandige naamwoorden die een verandering benoemen.
GEVOLGWOORDEN = frozenset("""
moet mag kost bespaart verdwijnt vervalt stopt begint verandert schrapt
verbiedt verplicht wijst afkeurt weigert dwingt levert bezit beheerst
sneller trager duurder goedkoper simpeler strenger deadline vanaf sinds
""".split())

# Abstracties die een kop leeg maken.
VAGE_ZELFSTANDIGE_NAAMWOORDEN = frozenset("""
ontwikkelingen mogelijkheden oplossingen uitdagingen inzichten trends
innovatie transformatie optimalisatie strategie ecosysteem landschap
""".split())

# Woorden die spamfilters wantrouwen; die kosten geen conversie maar
# bezorging, wat erger is.
BEZORGRISICO = frozenset("""
gratis!!! win winnen prijs klik hier nu!! gegarandeerd exclusief!!!
100% risicoloos geld verdienen aanbieding actie!!!
""".split())

AANSPREEKVORMEN = frozenset({"je", "jouw", "jij", "u", "uw", "ons", "onze"})


@dataclass
class Kopoordeel:
    kop: str
    score: float                       # 0-100, alleen zinvol als vergelijking
    dimensies: dict[str, float] = field(default_factory=dict)
    blokkades: list[str] = field(default_factory=list)
    adviezen: list[str] = field(default_factory=list)

    @property
    def bruikbaar(self) -> bool:
        return not self.blokkades

    def __str__(self) -> str:
        staat = "geblokkeerd" if self.blokkades else f"{self.score:.0f}"
        return f"[{staat}] {self.kop}"


# Gewichten: specificiteit weegt het zwaarst omdat het de enige dimensie is
# waarvoor het bewijs consistent is — een precies getal draagt zichzelf,
# een vaag getal roept twijfel op.
GEWICHTEN = {
    "specifiek": 0.30,
    "gevolg": 0.20,
    "aanspraak": 0.15,
    "voorlading": 0.15,
    "lengte": 0.10,
    "leesbaar": 0.10,
}


def _dim_specifiek(kop: str) -> float:
    woorden = kop.split()
    getal = bool(re.search(r"\d", kop))
    naam = any(w[:1].isupper() for w in woorden[1:])
    tijd = bool(koptoets._TIJDWOORDEN.search(kop))
    treffers = sum([getal, naam, tijd])
    # Een percentage of bedrag is scherper dan een los getal.
    if re.search(r"\d+\s*(%|procent|euro|€|miljoen|miljard|tb|gb)", kop, re.I):
        treffers += 1
    return min(treffers / 2, 1.0)


def _bevat(woorden: set[str], lijst: frozenset[str]) -> bool:
    """Vergelijkt op stam, zodat 'bezitten' ook 'bezit' herkent."""
    return any(zelfde_woord(w, doel) for w in woorden for doel in lijst)


def _dim_gevolg(kop: str) -> float:
    woorden = {w.strip(".,:;").lower() for w in kop.split()}
    if _bevat(woorden, VAGE_ZELFSTANDIGE_NAAMWOORDEN):
        return 0.0
    return 1.0 if _bevat(woorden, GEVOLGWOORDEN) else 0.35


def _dim_aanspraak(kop: str) -> float:
    woorden = {w.strip(".,:;").lower() for w in kop.split()}
    return 1.0 if woorden & AANSPREEKVORMEN else 0.4


def _dim_voorlading(kop: str) -> float:
    """Draagt de eerste veertig tekens de boodschap al?

    Op een telefoon is dat vaak alles wat iemand ziet. Een kop waarvan de
    kern pas na teken 50 komt, wordt afgekapt tot betekenisloos.
    """
    voorloop = kop[:ZICHTBARE_VOORLOOP]
    if len(kop) <= ZICHTBARE_VOORLOOP:
        return 1.0
    heeft_houvast = bool(
        re.search(r"\d", voorloop)
        or koptoets._TIJDWOORDEN.search(voorloop)
        or any(w[:1].isupper() for w in voorloop.split()[1:])
    )
    heeft_werkwoord = _bevat({w.lower() for w in voorloop.split()}, GEVOLGWOORDEN)
    return 0.35 + 0.35 * heeft_houvast + 0.30 * heeft_werkwoord


def _dim_lengte(kop: str) -> float:
    n = len(kop)
    onder, boven = IDEALE_LENGTE
    if onder <= n <= boven:
        return 1.0
    afstand = onder - n if n < onder else n - boven
    return max(0.0, 1.0 - afstand / 25)


def _dim_leesbaar(kop: str) -> float:
    # Een kop is één zin; de zinslengtecomponent van Flesch-Douma doet hier
    # weinig, de woordlengtecomponent des te meer.
    score = flesch_douma(kop)
    if score >= 70:
        return 1.0
    if score <= 20:
        return 0.0
    return (score - 20) / 50


def beoordeel(kop: str) -> Kopoordeel:
    """Beoordeelt één kop. Blokkades wegen zwaarder dan de score."""
    blokkades = koptoets.controleer_kop(kop)

    dimensies = {
        "specifiek": _dim_specifiek(kop),
        "gevolg": _dim_gevolg(kop),
        "aanspraak": _dim_aanspraak(kop),
        "voorlading": _dim_voorlading(kop),
        "lengte": _dim_lengte(kop),
        "leesbaar": _dim_leesbaar(kop),
    }
    score = 100 * sum(dimensies[naam] * gewicht for naam, gewicht in GEWICHTEN.items())

    adviezen = []
    if dimensies["specifiek"] < 0.5:
        adviezen.append("voeg een getal, eigennaam of tijdstip toe")
    if dimensies["gevolg"] < 0.5:
        adviezen.append("benoem wat er verandert, niet dat er iets is")
    if dimensies["aanspraak"] < 0.5:
        adviezen.append("zet de lezer in de zin ('je', 'jouw')")
    if dimensies["voorlading"] < 0.6:
        adviezen.append(f"verplaats de kern naar de eerste {ZICHTBARE_VOORLOOP} tekens")
    if dimensies["lengte"] < 0.8:
        adviezen.append(f"streef naar {IDEALE_LENGTE[0]}-{IDEALE_LENGTE[1]} tekens")
    if woorden := {w.strip(".,:;!").lower() for w in kop.split()} & BEZORGRISICO:
        adviezen.append(f"spamgevoelige woorden: {', '.join(sorted(woorden))}")

    return Kopoordeel(kop=kop, score=round(score, 1), dimensies=dimensies,
                      blokkades=blokkades, adviezen=adviezen)


def rangschik(koppen: list[str]) -> list[Kopoordeel]:
    """Ordent varianten van best naar slechtst; geblokkeerde koppen achteraan.

    Dit is de enige aanroep waarvoor de score bedoeld is: kiezen tussen
    alternatieven voor hetzelfde bericht.
    """
    oordelen = [beoordeel(k) for k in koppen]
    return sorted(oordelen, key=lambda o: (o.bruikbaar, o.score), reverse=True)
