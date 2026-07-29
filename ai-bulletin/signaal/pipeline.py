"""De dagelijkse run: verzamel → scoor → ontdubbel → shortlist → jury → output."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from . import audio as audio_mod
from . import bronnen, dedupe, historie, koptoets, rank, render, score
from .model import Editie, Item

log = logging.getLogger(__name__)


@dataclass
class Resultaat:
    editie: Editie
    na_ontdubbelen: int
    bestanden: list[Path]

    # Doorgeefluiken zodat aanroepers niet overal `.editie.` hoeven te typen.
    @property
    def datum(self) -> date:
        return self.editie.datum

    @property
    def selecties(self) -> list:
        return self.editie.items

    @property
    def kandidaten(self) -> int:
        return self.editie.kandidaten or 0


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

    # Geheugen: wat gisteren in de editie stond, komt vandaag niet terug.
    # Ná het scoren, want de herhaalstraf werkt op de voorscore.
    verleden = historie.laad(
        uitvoermap, config.get("historie", {}).get("dagen", 30), vandaag)
    items = historie.pas_toe(items, verleden, config)

    lijst = score.shortlist(items, config.get("shortlist", 40))

    if heuristisch:
        editie = rank.kies_heuristisch(lijst, config, vandaag)
    else:
        try:
            editie = rank.kies_en_schrijf(lijst, config, vandaag)
        except rank.RankFout as exc:
            # Liever een mindere editie dan geen editie: de nieuwsbrief moet
            # elke ochtend de deur uit.
            log.error("jury faalde (%s) — val terug op heuristische selectie", exc)
            editie = rank.kies_heuristisch(lijst, config, vandaag)

    editie.kandidaten = kandidaten
    editie.bronnen = len({i.bron for i in items})

    # Het model kan afdwalen van de kopregels; dat willen we zien in de logs
    # en niet pas als een lezer klaagt. Blokkeren doen we niet — een editie
    # met een matige kop is beter dan geen editie.
    for zwakke_kop, bezwaren in koptoets.toets_editie([s.kop for s in editie.items]).items():
        log.warning("zwakke kop — %s: %r", "; ".join(bezwaren), zwakke_kop)

    bestanden = _schrijf(editie, uitvoermap)

    if met_audio:
        try:
            script = audio_mod.maak_script(editie.items, vandaag)
            (uitvoermap / f"{editie.stam}-audio.txt").write_text(script, encoding="utf-8")
            bestanden.append(audio_mod.genereer(script, config, vandaag))
        except audio_mod.AudioFout as exc:
            log.error("audio overgeslagen: %s", exc)

    return Resultaat(editie=editie, na_ontdubbelen=len(items), bestanden=bestanden)


def render_selectie(pad: Path, uitvoermap: Path) -> Resultaat:
    """Render een bestaande selectie opnieuw naar alle formaten.

    Nodig voor twee dingen: een redactioneel nagelopen editie publiceren via
    dezelfde code als een automatische run, en het hele archief opnieuw
    uitdraaien als het sjabloon verandert.
    """
    editie = Editie.from_dict(json.loads(pad.read_text(encoding="utf-8")))
    bestanden = _schrijf(editie, uitvoermap)
    return Resultaat(
        editie=editie,
        na_ontdubbelen=editie.kandidaten or len(editie.items),
        bestanden=bestanden,
    )


def _schrijf(editie: Editie, map_: Path) -> list[Path]:
    map_.mkdir(parents=True, exist_ok=True)
    uitvoer = {
        f"{editie.stam}.json": render.naar_json(editie),
        f"{editie.stam}.md": render.naar_markdown(editie),
        f"{editie.stam}.html": render.naar_html(editie),
    }
    paden = []
    for naam, inhoud in uitvoer.items():
        pad = map_ / naam
        pad.write_text(inhoud, encoding="utf-8")
        paden.append(pad)
    return paden
