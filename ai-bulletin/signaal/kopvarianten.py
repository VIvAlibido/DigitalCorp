"""Varianten genereren en de beste kiezen.

Dit is waar de winst zit. Eén kop schrijven is een gok; acht koppen schrijven
en de beste kiezen is een selectie. De scorefunctie is een zwakke voorspeller
in absolute zin, maar bij het vergelijken van varianten van hetzelfde bericht
— waarbij onderwerp, bron en belang gelijk blijven en alleen de formulering
verschilt — is precies dat de vergelijking waarvoor hij bruikbaar is.

De runner-up wordt altijd bewaard. Zodra de lijst groot genoeg is om te
toetsen (zie abtest.py), is dat je B-variant zonder extra werk.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from . import kopscore
from .model import Selectie

log = logging.getLogger(__name__)

AANTAL_VARIANTEN = 8

SYSTEEM = """Je schrijft koppen voor een Nederlandstalige nieuwsbrief over AI, \
gelezen door ondernemers, managers en juristen die geen AI-specialist zijn.

Je krijgt één bericht en schrijft daar {aantal} verschillende koppen bij. Niet \
{aantal} variaties op dezelfde zin — {aantal} echt verschillende invalshoeken \
op hetzelfde feit. Denk aan: het gevolg voor de lezer, de deadline, het \
opvallendste getal, de betrokken partij, de tegenstelling in het verhaal, wat \
er verdwijnt, wat er nu moet gebeuren.

Eisen aan elke kop:
- Maximaal 70 tekens, ideaal tussen 45 en 65.
- Bevat een concreet onderwerp, een actief werkwoord en iets specifieks: een \
  getal, een eigennaam of een tijdstip.
- Getallen als cijfers ("73%", niet "bijna driekwart"). Een precies getal \
  draagt zijn eigen bewijs; een vaag getal roept twijfel op.
- De kern staat in de eerste 40 tekens, want daarna kapt een telefoon af.
- Verboden: vage hoeveelheden (bijna, ruim, flink, fors, steeds meer), \
  naamwoordstijl (de invoering van, het gebruik van), lijdende vorm zonder \
  handelende partij, uitroeptekens, en woorden die spamfilters prikkelen.
- Geen clickbait. Elke belofte in de kop wordt in het bericht ingelost — een \
  kop die meer belooft dan het bericht waarmaakt, kost je de volgende opening.

Toets elke kop: kan iemand die het bericht niet kent hieruit opmaken wie het \
raakt en wat er verandert? Zo niet, schrijf een andere.

Geef uitsluitend de koppen terug, zonder toelichting en zonder nummering."""

SCHEMA = {
    "type": "object",
    "properties": {
        "koppen": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["koppen"],
    "additionalProperties": False,
}


@dataclass
class Keuze:
    gekozen: str
    reserve: str
    oordeel: kopscore.Kopoordeel
    alle: list[kopscore.Kopoordeel] = field(default_factory=list)
    verbetering: float = 0.0


class VariantFout(RuntimeError):
    pass


def genereer(selectie: Selectie, config: dict, aantal: int = AANTAL_VARIANTEN) -> list[str]:
    """Laat het model `aantal` verschillende koppen bij één bericht schrijven."""
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise VariantFout("pakket 'anthropic' ontbreekt") from exc

    llm = config.get("llm", {})
    client = anthropic.Anthropic()
    try:
        antwoord = client.beta.messages.create(
            model=llm.get("model", "claude-opus-5"),
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEEM.format(aantal=aantal),
            output_config={
                "effort": llm.get("effort", "high"),
                "format": {"type": "json_schema", "schema": SCHEMA},
            },
            messages=[{
                "role": "user",
                "content": (
                    f"Categorie: {selectie.categorie}\n"
                    f"Bron: {selectie.bron} ({selectie.datum})\n"
                    f"Kern: {selectie.kern}\n"
                    f"Wat er gebeurd is: {selectie.wat}\n"
                    f"Wat het betekent: {selectie.waarom}\n\n"
                    f"Huidige kop: {selectie.kop}"
                ),
            }],
        )
    except Exception as exc:  # noqa: BLE001
        raise VariantFout(f"aanroep faalde: {exc}") from exc

    if antwoord.stop_reason == "refusal":
        raise VariantFout("model weigerde de aanvraag")

    tekst = next((b.text for b in antwoord.content if b.type == "text"), "")
    try:
        koppen = json.loads(tekst).get("koppen", [])
    except json.JSONDecodeError as exc:
        raise VariantFout(f"antwoord was geen geldige JSON: {exc}") from exc

    if not koppen:
        raise VariantFout("model leverde geen koppen")
    return koppen


def kies_beste(huidige_kop: str, varianten: list[str]) -> Keuze:
    """Rangschikt de huidige kop tussen de varianten en kiest de beste.

    De bestaande kop doet mee als kandidaat: als die al de sterkste is,
    verandert er niets. Vervangen om te vervangen is geen verbetering.
    """
    kandidaten = [huidige_kop] + [k for k in varianten if k != huidige_kop]
    gerangschikt = kopscore.rangschik(kandidaten)

    bruikbaar = [o for o in gerangschikt if o.bruikbaar] or gerangschikt
    beste = bruikbaar[0]
    reserve = bruikbaar[1] if len(bruikbaar) > 1 else beste

    huidig_oordeel = next(o for o in gerangschikt if o.kop == huidige_kop)

    return Keuze(
        gekozen=beste.kop,
        reserve=reserve.kop,
        oordeel=beste,
        alle=gerangschikt,
        verbetering=round(beste.score - huidig_oordeel.score, 1),
    )


def verbeter_editie(
    selecties: list[Selectie], config: dict, aantal: int = AANTAL_VARIANTEN
) -> list[Keuze]:
    """Genereert varianten voor elk bericht en kiest per bericht de beste.

    Een bericht waarvoor het genereren mislukt houdt zijn eigen kop; de rest
    van de editie gaat gewoon door.
    """
    keuzes = []
    for selectie in selecties:
        try:
            varianten = genereer(selectie, config, aantal)
        except VariantFout as exc:
            log.warning("varianten mislukt voor %r: %s", selectie.kop, exc)
            varianten = []
        keuze = kies_beste(selectie.kop, varianten)
        selectie.kop = keuze.gekozen
        keuzes.append(keuze)
    return keuzes
