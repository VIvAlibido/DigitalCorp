"""Geheugen tussen edities: wat we gisteren brachten, brengen we vandaag niet weer.

Het ontdubbelen in `dedupe.py` werkt binnen één run. Dat vangt de modelrelease
die tegelijk op Hacker News, de vendor-blog en Tweakers staat, maar niet het
verhaal dat maandag door Tweakers en woensdag door Emerce wordt opgepikt. Bij
één editie valt dat niet op; bij dagelijks publiceren stuur je mensen oud nieuws
als nieuw, en dat is de eerste terechte klacht die je krijgt.

Onderscheid dat hier wordt gemaakt:

* **Dezelfde bron-URL** — hard weigeren. Daar valt niets over te twisten.
* **Sterk gelijkende kop** — straffen, niet weigeren. Een vervolgstap in een
  lopend verhaal ("de AI-wet gaat nu écht in") is legitiem nieuws; een
  herhaling niet. Het verschil is niet betrouwbaar machinaal vast te stellen,
  dus verlagen we de score en laten we de jury beslissen.

De index komt uit de gepubliceerde edities zelf, niet uit een aparte database.
Eén bron van waarheid die niet uit de pas kan lopen.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from . import dedupe
from .model import Item, canonicaliseer_url

log = logging.getLogger(__name__)


@dataclass
class Historie:
    """Wat er in de afgelopen periode is gepubliceerd."""

    # Gecanonicaliseerde URL → datum van de editie waarin hij stond.
    urls: dict[str, str] = field(default_factory=dict)
    # (genormaliseerde kop, editiedatum) — genormaliseerd zoals dedupe dat doet.
    koppen: list[tuple[str, str]] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.urls)


def laad(map_: Path, dagen: int = 30, vandaag: date | None = None) -> Historie:
    """Lees de edities van de afgelopen `dagen` uit een uitvoermap.

    Een ontbrekende of onleesbare map levert een lege historie op in plaats van
    een fout: de eerste run heeft nog geen verleden, en een kapot archiefbestand
    mag de editie van vandaag niet tegenhouden.
    """
    historie = Historie()
    if not map_.is_dir():
        return historie

    vandaag = vandaag or date.today()
    grens = vandaag - timedelta(days=dagen)

    for pad in sorted(map_.glob("*.json")):
        try:
            data = json.loads(pad.read_text(encoding="utf-8"))
            datum = date.fromisoformat(data["datum"])
        except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
            log.warning("archiefbestand overgeslagen (%s): %s", pad.name, exc)
            continue

        # De editie van vandaag zelf telt niet mee — anders blokkeert een
        # herdraai van dezelfde dag zijn eigen items.
        if not (grens <= datum < vandaag):
            continue

        stempel = datum.isoformat()
        for rij in data.get("items", []):
            url = rij.get("url", "")
            if url:
                historie.urls[canonicaliseer_url(url)] = stempel
            kop = rij.get("kop", "")
            if kop:
                historie.koppen.append((dedupe.normaliseer(kop), stempel))

    log.info("historie: %d eerder gepubliceerde items uit %d dagen", len(historie), dagen)
    return historie


def oordeel(item: Item, historie: Historie, drempel: float = 0.72) -> tuple[str, str] | None:
    """Geeft `(oordeel, datum)` of None.

    Oordeel is `"blokkeer"` bij een exacte URL-match en `"straf"` bij een
    sterk gelijkende kop.
    """
    # Item.url is bij constructie al gecanonicaliseerd, maar we doen het hier
    # nog een keer: als dat ergens misgaat faalt de vergelijking stil, en een
    # stille misser betekent dat je hetzelfde bericht twee keer verstuurt.
    eerder = historie.urls.get(canonicaliseer_url(item.url))
    if eerder:
        return ("blokkeer", eerder)

    norm = dedupe.normaliseer(item.titel)
    for eerdere_kop, datum in historie.koppen:
        if dedupe.gelijkenis(norm, eerdere_kop) >= drempel:
            return ("straf", datum)
    return None


def pas_toe(items: list[Item], historie: Historie, config: dict) -> list[Item]:
    """Weer wat al gepubliceerd is en verlaag de score van bijna-herhalingen.

    Moet ná `score.scoor()` draaien — de straf werkt op de voorscore.
    """
    if not historie.urls and not historie.koppen:
        return items

    instellingen = config.get("historie", {})
    drempel = instellingen.get("drempel", 0.72)
    straf = instellingen.get("herhaalstraf", 0.45)

    over: list[Item] = []
    geblokkeerd = gestraft = 0

    for item in items:
        uitkomst = oordeel(item, historie, drempel)
        if uitkomst is None:
            over.append(item)
            continue

        soort, datum = uitkomst
        if soort == "blokkeer":
            geblokkeerd += 1
            log.debug("al gepubliceerd op %s: %s", datum, item.titel)
            continue

        item.voorscore *= straf
        item.metriek["eerder_gepubliceerd"] = datum
        gestraft += 1
        over.append(item)

    if geblokkeerd or gestraft:
        log.info("historie: %d geweerd, %d gestraft als mogelijke herhaling",
                 geblokkeerd, gestraft)
    return over
