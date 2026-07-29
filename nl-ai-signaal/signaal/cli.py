"""Commandoregel: `python -m signaal.cli [opties]`."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from . import pipeline
from .model import Item

PROJECT = Path(__file__).resolve().parent.parent


def _laad_fixtures(pad: Path) -> list[Item]:
    """Lees kandidaten uit een JSON-bestand — voor offline draaien en demo's."""
    ruw = json.loads(pad.read_text(encoding="utf-8"))
    items = []
    for rij in ruw:
        gepubliceerd = rij["gepubliceerd"]
        if isinstance(gepubliceerd, (int, float)):
            # Relatieve leeftijd in uren, zodat fixtures niet verouderen.
            gepubliceerd = datetime.now(timezone.utc).timestamp() - gepubliceerd * 3600
            gepubliceerd = datetime.fromtimestamp(gepubliceerd, tz=timezone.utc)
        else:
            gepubliceerd = datetime.fromisoformat(gepubliceerd)
        items.append(
            Item(
                titel=rij["titel"],
                url=rij["url"],
                bron=rij["bron"],
                brontype=rij["brontype"],
                gepubliceerd=gepubliceerd,
                samenvatting=rij.get("samenvatting", ""),
                metriek=rij.get("metriek", {}),
            )
        )
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nl-ai-signaal",
        description="Stelt de dagelijkse Nederlandstalige AI-nieuwsbrief samen.",
    )
    parser.add_argument("--config", default=PROJECT / "config.yaml", type=Path)
    parser.add_argument("--uitvoer", type=Path, help="map voor de editie (default uit config)")
    parser.add_argument("--datum", type=date.fromisoformat, default=None)
    parser.add_argument(
        "--heuristisch",
        action="store_true",
        help="sla de LLM-jury over; selecteer puur op voorscore",
    )
    parser.add_argument("--audio", action="store_true", help="genereer ook de audio-editie")
    parser.add_argument(
        "--fixtures",
        type=Path,
        help="lees kandidaten uit een JSON-bestand in plaats van live bronnen",
    )
    parser.add_argument(
        "--selectie",
        type=Path,
        help="render een bestaande selectie opnieuw; slaat verzamelen en jury over",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    config = pipeline.laad_config(args.config)
    uitvoermap = args.uitvoer or (PROJECT / config.get("output", {}).get("map", "edities"))
    if args.selectie:
        resultaat = pipeline.render_selectie(args.selectie, uitvoermap)
    else:
        vooraf = _laad_fixtures(args.fixtures) if args.fixtures else None
        resultaat = pipeline.draai(
            config,
            uitvoermap=uitvoermap,
            vandaag=args.datum,
            heuristisch=args.heuristisch,
            met_audio=args.audio,
            vooraf_verzameld=vooraf,
        )

    print(f"\nNL-AI-Signaal — {resultaat.datum.isoformat()}")
    print(f"{resultaat.kandidaten} kandidaten → {resultaat.na_ontdubbelen} uniek "
          f"→ {len(resultaat.selecties)} geplaatst\n")
    for nummer, s in enumerate(resultaat.selecties, 1):
        print(f"  {nummer}. [{s.categorie}] {s.kop}")
        print(f"     {s.bron} — {s.url}")
    print()
    for pad in resultaat.bestanden:
        print(f"  geschreven: {pad}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
