"""Commandoregel: `python -m signaal.cli [opties]`."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from . import pipeline, site, verzenden
from .bronnen import ontdek
from .model import Editie, Item

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
        prog="ai-bulletin",
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
    parser.add_argument(
        "--site",
        nargs="?",
        const=PROJECT / "site",
        type=Path,
        metavar="MAP",
        help="bouw de statische website uit alle edities en stop daarna",
    )
    parser.add_argument(
        "--verstuur",
        type=Path,
        metavar="EDITIE.JSON",
        help="verstuur een bestaande editie per e-mail en stop daarna",
    )
    parser.add_argument(
        "--proef",
        action="store_true",
        help="bij --verstuur: alle controles doorlopen maar niets versturen",
    )
    parser.add_argument(
        "--bronnen",
        action="store_true",
        help="controleer alle bronnen en rapporteer welke leven; stop daarna",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    config = pipeline.laad_config(args.config)
    uitvoermap = args.uitvoer or (PROJECT / config.get("output", {}).get("map", "edities"))

    if args.bronnen:
        # Draaien op een plek mét netwerk — de workflow dus. Vanuit de
        # ontwikkelomgeving weigert de proxy elk nieuwsdomein, en dat is precies
        # waarom feed-URL's daar niet te controleren zijn.
        rapport = ontdek.gezondheid(config)
        dood = [r for r in rapport if not r["feed"] or not r["items"]]
        print(f"\nAI Bulletin — bronnen: {len(rapport) - len(dood)} van "
              f"{len(rapport)} leveren berichten\n")
        for r in sorted(rapport, key=lambda r: (r["blok"], -r["items"])):
            teken = "OK " if r["items"] else "DOOD"
            print(f"  {teken} [{r['blok']}] {r['opgegeven']}")
            if r["feed"] and r["feed"] != r["opgegeven"]:
                print(f"       feed: {r['feed']}")
            print(f"       berichten: {r['items']}")
        return 0

    if args.site is not None:
        paden = site.bouw(uitvoermap, args.site, config)
        print(f"\nAI Bulletin — website: {len(paden)} bestanden in {args.site}")
        for pad in paden:
            print(f"  {pad.relative_to(args.site)}")
        return 0

    if args.verstuur is not None:
        editie = Editie.from_dict(json.loads(args.verstuur.read_text(encoding="utf-8")))
        try:
            verzending = verzenden.verstuur(editie, config, proef=args.proef)
        except verzenden.VerzendFout as exc:
            print(f"\nNIET VERSTUURD — {exc}\n", file=sys.stderr)
            return 1
        werkwoord = "opgebouwd (proefdraai)" if args.proef else "verstuurd"
        print(f"\n{len(verzending.ontvangers)} bericht(en) {werkwoord}")
        print(f"  onderwerp: {verzending.onderwerp}")
        for adres in verzending.ontvangers:
            print(f"  naar: {adres}")
        return 0

    if args.selectie:
        try:
            resultaat = pipeline.render_selectie(args.selectie, uitvoermap)
        except pipeline.KeuringsFout as exc:
            print(f"\nGEBLOKKEERD — {exc}\n", file=sys.stderr)
            return 1
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

    print(f"\nAI Bulletin — {resultaat.datum.isoformat()}")
    print(f"{resultaat.kandidaten} kandidaten → {resultaat.na_ontdubbelen} uniek "
          f"→ {len(resultaat.selecties)} geplaatst\n")
    for nummer, s in enumerate(resultaat.selecties, 1):
        print(f"  {nummer}. [{s.categorie}] {s.kop}")
        print(f"     {s.bron} — {s.url}")
    if resultaat.bevindingen:
        print("  Keuring:")
        for bevinding in resultaat.bevindingen:
            print(f"    {bevinding}")
        print()
    for pad in resultaat.bestanden:
        print(f"  geschreven: {pad}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
