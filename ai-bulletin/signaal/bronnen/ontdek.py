"""Feeds vinden bij een website, in plaats van de URL raden.

Aanleiding, 31 juli 2026. De editie van die ochtend kwam voor vier van de zes
berichten van Tweakers, omdat er nog maar vijf bronnen de shortlist haalden.
Drie Nederlandse feeds waren eerder uitgezet omdat ze 404 gaven, en er kwam
niets voor terug — met als reden dat de feed-URL's niet te controleren waren
vanuit de ontwikkelomgeving. Dat was geen reden maar een excuus.

Het probleem is echt: de proxy hier weigert elk nieuwsdomein, ook de domeinen
die in de workflow prima werken. Raden levert dan onzichtbare fouten op, want
een dode feed geeft alleen een regel in een log die niemand leest.

De oplossing is niet beter raden maar niet raden. Vrijwel elke nieuwssite zet
zijn feed in de `<head>`:

    <link rel="alternate" type="application/rss+xml" href="/feed/">

Daarom noemt config.yaml **sites**, geen feed-URL's, en zoekt deze module de
feed op de plek waar de site zelf zegt dat hij staat. Verhuist die feed, dan
verhuizen wij mee.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlsplit

from .basis import haal_op

log = logging.getLogger(__name__)

# <link rel="alternate" type="application/rss+xml" href="...">, in elke
# volgorde van attributen — daar is geen enkele site het over eens.
_LINK = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r"""(\w[\w-]*)\s*=\s*["']([^"']*)["']""")

# Paden die het proberen waard zijn als de site geen <link> heeft. Bewust kort:
# dit is een vangnet, geen zoektocht. Elk pad kost een verzoek.
TERUGVALPADEN = ("/feed/", "/rss", "/rss.xml", "/feed.xml", "/index.xml")


def _links(html: str) -> list[dict]:
    gevonden = []
    for tag in _LINK.findall(html or ""):
        attrs = {k.lower(): v for k, v in _ATTR.findall(tag)}
        if "feed" in attrs.get("type", "").lower() or "xml" in attrs.get("type", "").lower():
            gevonden.append(attrs)
    return gevonden


def _lijkt_op_feed(tekst: str | None) -> bool:
    """Genoeg om een HTML-foutpagina van een echte feed te onderscheiden."""
    kop = (tekst or "")[:800].lower()
    return "<rss" in kop or "<feed" in kop or "<rdf" in kop


def vind_feed(site: str) -> str | None:
    """De feed-URL van deze site, of None.

    Eerst wat de site zelf aanwijst; pas daarna de gebruikelijke paden. Die
    volgorde is niet vrijblijvend — een site die zijn feed verplaatst heeft,
    laat op het oude pad vaak een lege of kapotte feed staan.
    """
    pagina = haal_op(site)
    for attrs in _links(pagina or ""):
        href = attrs.get("href", "").strip()
        if not href:
            continue
        feed = urljoin(site, href)
        if _lijkt_op_feed(haal_op(feed)):
            log.info("feed gevonden via <link>: %s → %s", site, feed)
            return feed

    wortel = f"{urlsplit(site).scheme}://{urlsplit(site).netloc}"
    for pad in TERUGVALPADEN:
        feed = wortel + pad
        if _lijkt_op_feed(haal_op(feed)):
            log.info("feed gevonden op een gebruikelijk pad: %s", feed)
            return feed

    log.warning("geen feed gevonden voor %s", site)
    return None


def feeds_van(config_blok: dict) -> list[str]:
    """De feeds van dit bronblok: de vaste lijst plus wat we bij de sites vinden.

    Een site waarvan de feed niet te vinden is, valt stil weg — dat is beter dan
    de hele run laten struikelen. `keuring`/`gezondheid` maken zichtbaar dat het
    gebeurd is, want een stille misser is hier hetzelfde als een lege editie.
    """
    feeds = list(config_blok.get("feeds") or [])
    for site in config_blok.get("sites") or []:
        feed = vind_feed(site)
        if feed and feed not in feeds:
            feeds.append(feed)
    return feeds


def gezondheid(config: dict) -> list[dict]:
    """Per bron: werkt hij, en hoeveel berichten levert hij op.

    Bedoeld om te draaien op een plek mét netwerk — de workflow dus, niet de
    ontwikkelomgeving. Zo hoeft niemand meer te raden welke feed leeft.
    """
    from .basis import parse_feed  # lokaal: alleen deze functie heeft het nodig

    rapport = []
    for blok in ("rss", "rss_nl"):
        instellingen = (config.get("bronnen") or {}).get(blok) or {}
        for site in instellingen.get("sites") or []:
            feed = vind_feed(site)
            rapport.append({"blok": blok, "opgegeven": site, "feed": feed,
                            "items": len(parse_feed(haal_op(feed) or "")) if feed else 0})
        for feed in instellingen.get("feeds") or []:
            xml = haal_op(feed)
            rapport.append({"blok": blok, "opgegeven": feed, "feed": feed if xml else None,
                            "items": len(parse_feed(xml or ""))})
    return rapport
