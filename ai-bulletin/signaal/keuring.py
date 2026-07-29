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
        for veld in ("kern", "wat", "waarom", "url", "bron"):
            if not str(getattr(s, veld, "")).strip():
                b.append(Bevinding("blokkade", waar, f"leeg veld: {veld}"))
        if not s.datum:
            b.append(Bevinding("waarschuwing", waar, "geen datum van de gebeurtenis"))
        if len(s.kern) > MAX_KERN_TEKENS:
            b.append(Bevinding("waarschuwing", waar,
                               f"kern is {len(s.kern)} tekens (max {MAX_KERN_TEKENS})"))
        b += _keur_placeholders(waar, f"{s.kern} {s.wat} {s.waarom}", streng)

    for bezwaar in rank.toets_verhouding(editie):
        nummer = bezwaar.split(".", 1)[0]
        b.append(Bevinding("waarschuwing", f"bericht {nummer}",
                           bezwaar.split(": ", 1)[-1]))
    return b


def _keur_toepassing(editie: Editie) -> list[Bevinding]:
    """'Vandaag toepassen' is het ene kenmerk van dit product (CLAUDE.md).

    Een dagelijkse editie zonder toepassing is geen mindere editie maar een
    ander product. Op een zondag met alleen een beschouwing mag hij ontbreken.
    """
    if not editie.toepassing:
        if editie.items:
            return [Bevinding("blokkade", "toepassing",
                              "ontbreekt — dit is het kenmerk van de nieuwsbrief")]
        return [Bevinding("waarschuwing", "toepassing", "ontbreekt")]

    b, t = [], editie.toepassing
    for veld in ("titel", "intro"):
        if not str(getattr(t, veld, "")).strip():
            b.append(Bevinding("blokkade", "toepassing", f"leeg veld: {veld}"))
    if len(t.stappen) != 3:
        b.append(Bevinding("waarschuwing", "toepassing",
                           f"{len(t.stappen)} stappen — twee is te dun, vier leest als huiswerk"))
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
