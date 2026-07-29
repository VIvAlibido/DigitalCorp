#!/usr/bin/env python3
"""Bouwstap voor Vercel (en elke andere statische host).

Draait als `python3 bouw_site.py` en schrijft de site naar `public/`.

Het verschil met `python -m signaal.cli --site` zit in de poort: een
voorvertoning mag altijd gebouwd worden, een productiedeploy niet zolang de
uitgeversgegevens ontbreken. Vercel geeft dat onderscheid door via VERCEL_ENV
("production", "preview" of "development").

Waarom die poort er is: art. 3:15d BW verplicht een commerciële website tot een
vindbare naam, vestigingsadres, e-mailadres en KvK-nummer, en een nieuwssite die
op betrouwbaarheid concurreert kan sowieso niet anoniem zijn. Zie
signaal/site.controleer_publicatiegereed().
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

from signaal import pipeline, site  # noqa: E402


def main() -> int:
    omgeving = os.environ.get("VERCEL_ENV", "development")
    productie = omgeving == "production"

    config = pipeline.laad_config(HIER / "config.yaml")
    edities = HIER / config.get("output", {}).get("map", "edities")
    uitvoer = HIER / "public"

    blokkades = site.controleer_publicatiegereed(config)
    if blokkades:
        kop = "GEBLOKKEERD" if productie else "Let op"
        print(f"\n{kop} — de site is nog niet publicatiegereed:")
        for regel in blokkades:
            print(f"  · {regel}")
        if productie:
            print(
                "\nVul het blok `uitgever:` in config.yaml in en deploy opnieuw.\n"
                "Een voorvertoning bouwen mag wel: die staat op noindex en op een\n"
                "tijdelijke URL, en telt niet als publicatie.\n"
            )
            return 1
        print("  → voorvertoning wordt wel gebouwd, met noindex.\n")

    paden = site.bouw(edities, uitvoer, config, indexeerbaar=productie and not blokkades)
    print(f"{len(paden)} bestanden geschreven naar {uitvoer} (omgeving: {omgeving})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
