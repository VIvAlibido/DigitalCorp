"""Werkbank voor koppen: `python -m signaal.koppen [opties]`.

Drie standen, in volgorde van hoeveel je erop mag vertrouwen:

  --toets      keurt koppen af op aantoonbare gebreken (hoog vertrouwen)
  --varianten  laat het model acht alternatieven schrijven en kiest de beste
  --steekproef rekent uit of je lijst groot genoeg is om te toetsen

De laatste is de belangrijkste en de minst leuke: zonder voldoende ontvangers
is elke uitspraak over conversie een aanname, ook die van dit script.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import abtest, kopscore, kopvarianten, leesbaarheid, pipeline
from .model import Selectie

PROJECT = Path(__file__).resolve().parent.parent


def _laad(pad: Path) -> tuple[dict, list[Selectie]]:
    data = json.loads(pad.read_text(encoding="utf-8"))
    return data, [Selectie(**rij) for rij in data["items"]]


def _balk(waarde: float, breedte: int = 10) -> str:
    vol = round(waarde * breedte)
    return "█" * vol + "·" * (breedte - vol)


def toets(pad: Path) -> int:
    """Rapporteert per kop de blokkades, de score en het advies."""
    data, selecties = _laad(pad)
    print(f"\nKoppen — {pad.name}\n{'=' * 72}")

    problemen = 0
    for nummer, s in enumerate(selecties, 1):
        oordeel = kopscore.beoordeel(s.kop)
        merk = "GEBLOKKEERD" if oordeel.blokkades else f"score {oordeel.score:>5.1f}"
        print(f"\n{nummer}. {s.kop}")
        print(f"   {merk} · {len(s.kop)} tekens · "
              f"{leesbaarheid.niveau(leesbaarheid.flesch_douma(s.kop))}")
        for naam, waarde in oordeel.dimensies.items():
            print(f"     {naam:<12} {_balk(waarde)} {waarde:.2f}")
        for blokkade in oordeel.blokkades:
            print(f"     ✗ {blokkade}")
            problemen += 1
        for advies in oordeel.adviezen:
            print(f"     → {advies}")

    onderwerp = data.get("onderwerp", "")
    if onderwerp:
        print(f"\n{'-' * 72}\nOnderwerpregel: {onderwerp!r} ({len(onderwerp)} tekens)")
        if len(onderwerp) > 50:
            print("     ✗ langer dan 50 tekens; mobiel kapt af")
            problemen += 1

    print(f"\n{'=' * 72}\n{problemen} blokkade(s)\n")
    return 1 if problemen else 0


def varianten(pad: Path, config: dict, schrijf: bool) -> int:
    """Genereert alternatieven per bericht en kiest de sterkste."""
    data, selecties = _laad(pad)
    print(f"\nVarianten — {pad.name}\n{'=' * 72}")

    keuzes = kopvarianten.verbeter_editie(selecties, config)
    for nummer, (s, keuze) in enumerate(zip(selecties, keuzes), 1):
        print(f"\n{nummer}. gekozen: {keuze.gekozen}")
        print(f"   reserve (B-variant): {keuze.reserve}")
        if keuze.verbetering:
            print(f"   winst t.o.v. de oude kop: {keuze.verbetering:+.1f} punt")
        else:
            print("   de bestaande kop bleef de sterkste")
        for oordeel in keuze.alle[1:4]:
            staat = "geblokkeerd" if oordeel.blokkades else f"{oordeel.score:.0f}"
            print(f"     [{staat:>11}] {oordeel.kop}")

    if schrijf:
        data["items"] = [s.as_dict() for s in selecties]
        # Bewaar de B-varianten: zodra de lijst groot genoeg is om te toetsen,
        # heb je ze al zonder extra werk.
        data["kop_reserves"] = [k.reserve for k in keuzes]
        pad.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        print(f"\n{pad} bijgewerkt")
    else:
        print("\n(niets weggeschreven — gebruik --schrijf)")
    return 0


def steekproef(lijstgrootte: int, baseline: float) -> int:
    """Laat zien welk verschil bij deze lijstgrootte aantoonbaar is."""
    print(f"\nA/B-toetsing bij {lijstgrootte:,} ontvangers".replace(",", ".")
          + f" en een basis van {baseline:.0%}\n{'=' * 72}\n")
    print(f"{'verschil':<12}{'per variant':>14}{'totaal nodig':>15}   haalbaar?")
    print("-" * 72)

    haalbaar_vanaf = None
    for advies in abtest.adviestabel(baseline):
        verschil = advies.doel - advies.baseline
        kan = advies.totaal <= lijstgrootte
        if kan and haalbaar_vanaf is None:
            haalbaar_vanaf = verschil
        print(f"{f'+{verschil:.0%}':<12}{advies.per_variant:>14,}"
              f"{advies.totaal:>15,}   {'ja' if kan else 'nee'}".replace(",", "."))

    print("-" * 72)
    if haalbaar_vanaf is None:
        print(
            "\nBij deze lijstgrootte is geen enkel realistisch verschil aantoonbaar.\n"
            "Toets voorlopig niet op onderwerpregels: het resultaat is ruis, en\n"
            "beslissingen nemen op ruis is erger dan niet meten. Laat de koptoets\n"
            "en de variantselectie het werk doen tot de lijst groter is."
        )
    else:
        print(f"\nVanaf een verschil van {haalbaar_vanaf:.0%} is toetsen zinvol.")
        print("Kleinere verschillen bestaan wel, maar je kunt ze niet zien —\n"
              "en wat je niet kunt zien, moet je niet in een besluit stoppen.")
    print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="signaal.koppen", description="Toetst, verbetert en meet koppen."
    )
    parser.add_argument("--editie", type=Path,
                        help="pad naar een selectie-JSON in redactie/")
    parser.add_argument("--toets", action="store_true", help="alleen controleren")
    parser.add_argument("--varianten", action="store_true",
                        help="alternatieven laten schrijven en de beste kiezen")
    parser.add_argument("--schrijf", action="store_true",
                        help="gekozen koppen terugschrijven naar de editie")
    parser.add_argument("--steekproef", type=int, metavar="LIJSTGROOTTE",
                        help="reken uit welk verschil aantoonbaar is")
    parser.add_argument("--baseline", type=float, default=0.35,
                        help="huidige openratio, standaard 0.35")
    parser.add_argument("--config", type=Path, default=PROJECT / "config.yaml")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.steekproef:
        return steekproef(args.steekproef, args.baseline)

    if not args.editie:
        parser.error("geef --editie of --steekproef op")

    if args.varianten:
        return varianten(args.editie, pipeline.laad_config(args.config), args.schrijf)

    return toets(args.editie)


if __name__ == "__main__":
    sys.exit(main())
