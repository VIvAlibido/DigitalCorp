"""De dagelijkse run: verzamel → scoor → ontdubbel → shortlist → jury → output."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from . import audio as audio_mod
from . import bronnen, dedupe, rank, render, score
from .model import Item, Selectie

log = logging.getLogger(__name__)


@dataclass
class Resultaat:
    datum: date
    selecties: list[Selectie]
    kandidaten: int
    na_ontdubbelen: int
    bestanden: list[Path]


def laad_config(pad: str | Path) -> dict:
    with open(pad, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def draai(
    config: dict,
    *,
    uitvoermap: Path,
    vandaag: date | None = None,
    heuristisch: bool = False,
    met_audio: bool = False,
    vooraf_verzameld: list[Item] | None = None,
) -> Resultaat:
    """Voer één editie uit.

    `vooraf_verzameld` omzeilt het ophalen — gebruikt door tests en door
    `--fixtures` om offline te kunnen draaien.
    """
    vandaag = vandaag or date.today()

    items = vooraf_verzameld if vooraf_verzameld is not None else bronnen.verzamel_alles(config)
    log.info("%d kandidaten opgehaald", len(items))

    items = score.filter_op_leeftijd(items, config.get("max_leeftijd_uren", 36))
    items = score.scoor(items, config)
    # Ontdubbelen ná scoren: de hoogste voorscore wint het cluster, en het
    # cluster levert een bonus die pas dan bekend is — dus nog een keer scoren.
    kandidaten = len(items)
    items = dedupe.ontdubbel(items)
    items = score.scoor(items, config)
    log.info("%d over na ontdubbelen", len(items))

    lijst = score.shortlist(items, config.get("shortlist", 40))

    if heuristisch:
        selecties = rank.kies_heuristisch(lijst, config)
    else:
        try:
            selecties = rank.kies_en_schrijf(lijst, config)
        except rank.RankFout as exc:
            # Liever een mindere editie dan geen editie: de nieuwsbrief moet
            # elke ochtend de deur uit.
            log.error("jury faalde (%s) — val terug op heuristische selectie", exc)
            selecties = rank.kies_heuristisch(lijst, config)

    bestanden = _schrijf(
        selecties, vandaag, uitvoermap,
        kandidaten=kandidaten,
        bronnen=len({i.bron for i in items}),
    )

    if met_audio:
        try:
            script = audio_mod.maak_script(selecties, vandaag)
            (uitvoermap / f"{vandaag.isoformat()}-audio.txt").write_text(script, encoding="utf-8")
            bestanden.append(audio_mod.genereer(script, config, vandaag))
        except audio_mod.AudioFout as exc:
            log.error("audio overgeslagen: %s", exc)

    return Resultaat(
        datum=vandaag,
        selecties=selecties,
        kandidaten=kandidaten,
        na_ontdubbelen=len(items),
        bestanden=bestanden,
    )


def render_selectie(pad: Path, uitvoermap: Path) -> Resultaat:
    """Render een bestaande selectie opnieuw naar alle formaten.

    Nodig voor twee dingen: een redactioneel nagelopen editie publiceren via
    dezelfde code als een automatische run, en het hele archief opnieuw
    uitdraaien als het sjabloon verandert.
    """
    import json

    data = json.loads(pad.read_text(encoding="utf-8"))
    selecties = [Selectie(**rij) for rij in data["items"]]
    d = date.fromisoformat(data["datum"])
    kandidaten = data.get("kandidaten")
    bronnen = data.get("bronnen")

    bestanden = _schrijf(selecties, d, uitvoermap, kandidaten=kandidaten, bronnen=bronnen)
    return Resultaat(
        datum=d,
        selecties=selecties,
        kandidaten=kandidaten or 0,
        na_ontdubbelen=kandidaten or 0,
        bestanden=bestanden,
    )


def _schrijf(
    selecties: list[Selectie],
    d: date,
    map_: Path,
    kandidaten: int | None = None,
    bronnen: int | None = None,
) -> list[Path]:
    map_.mkdir(parents=True, exist_ok=True)
    stam = d.isoformat()
    uitvoer = {
        f"{stam}.json": render.naar_json(selecties, d),
        f"{stam}.md": render.naar_markdown(selecties, d, kandidaten, bronnen),
        f"{stam}.html": render.naar_html(selecties, d, kandidaten, bronnen),
    }
    paden = []
    for naam, inhoud in uitvoer.items():
        pad = map_ / naam
        pad.write_text(inhoud, encoding="utf-8")
        paden.append(pad)
    return paden
