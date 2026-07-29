"""Gedeelde helpers voor bronnen: HTTP-ophalen en RSS/Atom-parsen.

Bewust zonder feedparser — `xml.etree` uit de stdlib is genoeg voor de feeds
die we gebruiken en scheelt een dependency die vaak achterloopt.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

log = logging.getLogger(__name__)

USER_AGENT = "AI Bulletin/1.0 (+https://github.com/VIvAlibido/DigitalCorp)"
TIMEOUT = 20

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def haal_op(url: str, params: dict | None = None, accept_json: bool = False):
    """GET met nette timeout en user-agent. Geeft None terug bij een fout.

    Bronnen mogen individueel falen zonder de hele run om zeep te helpen.
    """
    headers = {"User-Agent": USER_AGENT}
    if accept_json:
        headers["Accept"] = "application/json"
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("bron onbereikbaar: %s (%s)", url, exc)
        return None
    return resp.json() if accept_json else resp.text


def parse_datum(waarde: str | None) -> datetime:
    """Parse RFC-822 (RSS) of ISO-8601 (Atom). Valt terug op 'nu'."""
    if not waarde:
        return datetime.now(timezone.utc)
    waarde = waarde.strip()
    try:
        dt = parsedate_to_datetime(waarde)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(waarde.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _tekst(element, pad: str, ns: dict | None = None) -> str:
    gevonden = element.find(pad, ns) if ns else element.find(pad)
    if gevonden is None or gevonden.text is None:
        return ""
    return " ".join(gevonden.text.split())


def parse_feed(xml_tekst: str) -> list[dict]:
    """Parse RSS 2.0 én Atom naar een uniforme lijst dicts.

    Retourneert per entry: titel, url, samenvatting, gepubliceerd.
    """
    try:
        root = ET.fromstring(xml_tekst)
    except ET.ParseError as exc:
        log.warning("feed niet te parsen: %s", exc)
        return []

    entries: list[dict] = []

    # RSS 2.0
    for item in root.iter("item"):
        link = _tekst(item, "link")
        if not link:
            continue
        entries.append(
            {
                "titel": _tekst(item, "title"),
                "url": link,
                "samenvatting": _tekst(item, "description")[:600],
                "gepubliceerd": parse_datum(_tekst(item, "pubDate") or _tekst(item, "date")),
            }
        )

    # Atom
    for entry in root.iter(f"{{{_NS['atom']}}}entry"):
        link_el = entry.find("atom:link[@rel='alternate']", _NS) or entry.find("atom:link", _NS)
        link = (link_el.get("href") if link_el is not None else "") or ""
        if not link:
            continue
        samenvatting = _tekst(entry, "atom:summary", _NS) or _tekst(entry, "atom:content", _NS)
        entries.append(
            {
                "titel": _tekst(entry, "atom:title", _NS),
                "url": link,
                "samenvatting": samenvatting[:600],
                "gepubliceerd": parse_datum(
                    _tekst(entry, "atom:published", _NS) or _tekst(entry, "atom:updated", _NS)
                ),
            }
        )

    return entries


def strip_html(tekst: str) -> str:
    """Grove HTML-stripper — feeds leveren vaak <p>-soep in de description."""
    import re

    zonder_tags = re.sub(r"<[^>]+>", " ", tekst)
    ontsnapt = (
        zonder_tags.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&nbsp;", " ")
    )
    return " ".join(ontsnapt.split())
