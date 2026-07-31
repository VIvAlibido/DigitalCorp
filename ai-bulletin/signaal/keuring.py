"""Eén keuring waar elke editie doorheen moet, ongeacht wie hem maakte.

Aanleiding: de controles in dit project waren aangesloten op de automatische
run, en niet op `render_selectie()` — de route waarlangs elke met de hand
geschreven editie binnenkomt. Alle redactionele fouten die de opdrachtgever in
deze week vond, kwamen via die tweede route: een duiding van 77 woorden waar er
60 mochten, en een kop over "de AI-wet" waar niemand in voorkwam.

Losse regels bijplakken lost dat niet op. Wat het wel oplost is dat er precies
één poort is die alles keurt, en dat beide routes daar doorheen moeten.

Onderscheid tussen twee soorten bevindingen:

* BLOKKADE — aantoonbaar fout. Een ontbrekend veld, een dubbele URL, een
  placeholder die is blijven staan, een mening zonder naam. Hier valt niets over
  te oordelen, dus mag het niet gepubliceerd worden.
* WAARSCHUWING — redactioneel oordeel. Een zwakke kop, een te lange duiding.
  Dat wil je zien, maar een mindere editie is beter dan geen editie.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import koptoets, rank
from .model import Editie

# Tekst die alleen in tussenversies hoort te staan en nooit bij een lezer.
_PLACEHOLDERS = (
    "heuristische selectie",
    "automatische selectie zonder redactie",
    "nog niet ingevuld",
    "todo",
    "lorem ipsum",
    "xxx",
)

MIN_ONDERWERP, MAX_ONDERWERP = 20, 50
MAX_KERN_TEKENS = 200


@dataclass(frozen=True)
class Bevinding:
    ernst: str      # "blokkade" of "waarschuwing"
    waar: str       # welk onderdeel
    wat: str

    def __str__(self) -> str:
        teken = "✗" if self.ernst == "blokkade" else "!"
        return f"{teken} {self.waar}: {self.wat}"


def keur(editie: Editie, streng: bool = False) -> list[Bevinding]:
    """Keur een complete editie. Lege lijst betekent: niets aan te merken.

    `streng` maakt van placeholders een blokkade. Dat staat aan voor edities die
    met de hand zijn geschreven en uit bij de automatische run, waar de
    heuristische terugval legitiem placeholdertekst oplevert.
    """
    b: list[Bevinding] = []
    b += _keur_opbouw(editie)
    b += _keur_koppen(editie)
    b += _keur_items(editie, streng)
    b += _keur_herkomst(editie)
    b += _keur_toepassing(editie)
    b += _keur_beschouwing(editie)
    b += _keur_onderwerpregel(editie)
    return b


def blokkades(bevindingen: list[Bevinding]) -> list[Bevinding]:
    return [x for x in bevindingen if x.ernst == "blokkade"]


# ─────────────────────────── deelkeuringen ───────────────────────────

def _keur_opbouw(editie: Editie) -> list[Bevinding]:
    b = []
    if not editie.items and not editie.beschouwing:
        b.append(Bevinding("blokkade", "editie", "geen berichten en geen zondagsstuk"))
    elif editie.items and len(editie.items) < rank.MIN_ITEMS:
        b.append(Bevinding(
            "blokkade", "editie",
            f"{len(editie.items)} berichten, minimaal {rank.MIN_ITEMS}"))
    if len(editie.items) > rank.MAX_ITEMS:
        b.append(Bevinding(
            "blokkade", "editie",
            f"{len(editie.items)} berichten, hoogstens {rank.MAX_ITEMS}"))

    urls = [i.url for i in editie.items]
    for dubbel in {u for u in urls if urls.count(u) > 1}:
        b.append(Bevinding("blokkade", "editie", f"dezelfde bron twee keer: {dubbel}"))
    return b


def _keur_koppen(editie: Editie) -> list[Bevinding]:
    """Koppen van berichten én van het zondagsstuk — die laatste viel eerder
    buiten elke controle, en dat is precies waar het misging."""
    koppen = [(f"bericht {n}", s.kop) for n, s in enumerate(editie.items, 1)]
    if editie.beschouwing:
        koppen.append(("zondagsstuk", editie.beschouwing.titel))
    return [
        Bevinding("waarschuwing", waar, bezwaar)
        for waar, kop in koppen
        for bezwaar in koptoets.controleer_kop(kop)
    ]


def _keur_items(editie: Editie, streng: bool) -> list[Bevinding]:
    b = []
    for n, s in enumerate(editie.items, 1):
        waar = f"bericht {n}"
        # "kop" ontbrak hier tot 30 juli. Uitgerekend het veld dat de lezer als
        # eerste ziet mocht dus leeg zijn, en een kop met "TODO" erin kwam er
        # ook doorheen omdat de placeholdertoets alleen naar de tekst keek.
        # Gevonden doordat een verzendtest een editie probeerde te breken en
        # de keuring hem gewoon goedkeurde.
        for veld in ("kop", "kern", "wat", "waarom", "url", "bron"):
            if not str(getattr(s, veld, "")).strip():
                b.append(Bevinding("blokkade", waar, f"leeg veld: {veld}"))
        if not s.datum:
            b.append(Bevinding("waarschuwing", waar, "geen datum van de gebeurtenis"))
        if len(s.kern) > MAX_KERN_TEKENS:
            b.append(Bevinding("waarschuwing", waar,
                               f"kern is {len(s.kern)} tekens (max {MAX_KERN_TEKENS})"))
        b += _keur_placeholders(waar, f"{s.kop} {s.kern} {s.wat} {s.waarom}", streng)

    for bezwaar in rank.toets_verhouding(editie):
        nummer = bezwaar.split(".", 1)[0]
        b.append(Bevinding("waarschuwing", f"bericht {nummer}",
                           bezwaar.split(": ", 1)[-1]))
    return b


# Cijfers waarbij het uitmaakt waar ze vandaan komen. Bewust géén losse getallen
# als "zeven fabrieken" of "drie bedrijven": die zijn na te tellen in de bron.
# Wat hier staat is het soort cijfer dat een lezer overneemt zonder controle —
# een percentage, een bedrag, een groot getal, een verhouding.
_GROOT = r"\d{1,3}(?:[.\u00a0 ]\d{3})+"          # 3.700, 24 000
_CIJFER = re.compile(
    # Volgorde telt: de langste vorm eerst, anders knipt "1 op de 24.000" in
    # tweeen en meldt de keuring '1 op de 2' en '4.000' als losse cijfers.
    rf"""(
        \b\d+\s+op\s+(?:de\s+)?(?:{_GROOT}|\d+)  # 1 op de 24.000
      | \d+(?:[.,]\d+)?\s*(?:%|procent)          # 44%, 0,62 procent
      | \d+(?:[.,]\d+)?\s*(?:duizend|miljoen|miljard|biljoen)
      | (?:\u20ac|\$|EUR|USD)\s?\d                    # euro 10, $2,50
      | \d+(?:[.,]\d+)?\s*(?:euro|dollar)
      | {_GROOT}
    )""",
    re.VERBOSE | re.IGNORECASE,
)

# Wat eruitziet als zo'n cijfer maar het niet is. Een jaartal en een
# wetsartikel zijn geen bewering over de wereld maar een verwijzing.
_GEEN_CIJFER = re.compile(
    r"\b(?:19|20|21)\d{2}\b|\bartikel\s+\d+|\blid\s+\d+", re.IGNORECASE)


def cijfers_zonder_herkomst(s) -> list[str]:
    """De cijfers in dit bericht die om een kanttekening vragen.

    Leeg als het bericht een kanttekening heeft, want dan is de herkomst
    benoemd. Wij toetsen niets onafhankelijk na — dat kan deze pijplijn niet —
    dus is "waar komt dit vandaan" het enige wat we wél kunnen leveren.
    """
    if str(getattr(s, "kanttekening", "") or "").strip():
        return []
    tekst = _GEEN_CIJFER.sub(" ", f"{s.kern} {s.wat} {s.waarom}")
    return sorted({m.group(0).strip() for m in _CIJFER.finditer(tekst)})


def _keur_herkomst(editie: Editie) -> list[Bevinding]:
    """Beslissing 20: elk cijfer heeft een herkomst, of het bericht gaat eruit.

    Onder elke editie staat de belofte "een kanttekening bij elk cijfer dat niet
    onafhankelijk is getoetst". Op 30 juli stond "900 miljoen wekelijkse
    gebruikers van ChatGPT" zonder kanttekening, terwijl vergelijkbare cijfers
    er wél een kregen. Die inconsequentie is erger dan strengheid: hij maakt de
    belofte onbetrouwbaar, en de belofte is het product.

    Blokkade, geen waarschuwing. Een waarschuwing had dit precies zo laten
    passeren als op 30 juli.
    """
    b = []
    for n, s in enumerate(editie.items, 1):
        ontbreekt = cijfers_zonder_herkomst(s)
        if ontbreekt:
            b.append(Bevinding(
                "blokkade", f"bericht {n}",
                "cijfer zonder kanttekening over de herkomst: "
                + ", ".join(f"'{x}'" for x in ontbreekt[:3])))
    return b


def _keur_toepassing(editie: Editie) -> list[Bevinding]:
    """'Vandaag toepassen' is het ene kenmerk van dit product (CLAUDE.md).

    Een dagelijkse editie zonder toepassing is geen mindere editie maar een
    ander product. Op een zondag met alleen een beschouwing mag hij ontbreken.
    """
    if not editie.toepassing:
        # Waarschuwing, geen blokkade. Als blokkade dwong deze regel een toepassing
        # af op dagen waarop er niets te doen viel, en dan wordt "zet één zin onder
        # je chatvenster" opgeblazen tot drie stappen en twintig minuten. Geen echte
        # handeling betekent geen rubriek.
        return [Bevinding("waarschuwing", "toepassing",
                          "ontbreekt — alleen aanvaardbaar als er echt niets te doen valt")]

    b, t = [], editie.toepassing
    for veld in ("titel", "intro"):
        if not str(getattr(t, veld, "")).strip():
            b.append(Bevinding("blokkade", "toepassing", f"leeg veld: {veld}"))
    if len(t.stappen) > 3:
        b.append(Bevinding("waarschuwing", "toepassing",
                           f"{len(t.stappen)} stappen — vier leest als huiswerk"))
    for n, stap in enumerate(t.stappen, 1):
        eerste = stap.split()[0].lower() if stap.split() else ""
        if eerste in ("overweeg", "denk", "bedenk", "probeer", "kijk"):
            b.append(Bevinding("waarschuwing", "toepassing",
                               f"stap {n} begint met '{eerste}' — dat is geen handeling"))
    return b


def _keur_beschouwing(editie: Editie) -> list[Bevinding]:
    if not editie.beschouwing:
        return []
    b, stuk = [], editie.beschouwing
    if not stuk.auteur.strip():
        # Geen detail: een mening zonder naam is het slechtste van twee werelden.
        b.append(Bevinding("blokkade", "zondagsstuk", "geen auteur"))
    if not stuk.kern.strip():
        b.append(Bevinding("blokkade", "zondagsstuk", "geen kernzin"))
    if stuk.woorden < 300:
        b.append(Bevinding("waarschuwing", "zondagsstuk",
                           f"{stuk.woorden} woorden — een zondagsstuk draagt vanaf ±800"))
    b += _keur_placeholders("zondagsstuk", " ".join(stuk.alineas), streng=True)
    return b


def _keur_onderwerpregel(editie: Editie) -> list[Bevinding]:
    b, onderwerp = [], editie.onderwerp
    if not onderwerp.strip():
        return [Bevinding("blokkade", "onderwerpregel", "ontbreekt")]
    if not MIN_ONDERWERP <= len(onderwerp) <= MAX_ONDERWERP:
        b.append(Bevinding("waarschuwing", "onderwerpregel",
                           f"{len(onderwerp)} tekens (mik op {MIN_ONDERWERP}-{MAX_ONDERWERP})"))
    if "nieuwsbrief" in onderwerp.lower():
        b.append(Bevinding("waarschuwing", "onderwerpregel", "bevat het woord 'nieuwsbrief'"))
    if editie.preheader and editie.preheader.strip() == onderwerp.strip():
        b.append(Bevinding("waarschuwing", "preheader", "herhaalt de onderwerpregel"))
    return b


def _keur_placeholders(waar: str, tekst: str, streng: bool) -> list[Bevinding]:
    laag = tekst.lower()
    ernst = "blokkade" if streng else "waarschuwing"
    return [
        Bevinding(ernst, waar, f"placeholdertekst: '{p}'")
        for p in _PLACEHOLDERS
        if p in laag
    ]
