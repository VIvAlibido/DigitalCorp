"""Kerndatatypes die door de hele pijplijn heen gaan."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

_TRACKING_PARAMS = re.compile(r"^(utm_|fbclid|gclid|mc_cid|mc_eid|ref$|source$)")


def canonicaliseer_url(url: str) -> str:
    """Strip tracking-parameters en fragment zodat dezelfde link niet dubbel telt."""
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

    delen = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(delen.query) if not _TRACKING_PARAMS.match(k)]
    pad = delen.path.rstrip("/") or "/"
    netloc = delen.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return urlunsplit((delen.scheme.lower(), netloc, pad, urlencode(query), ""))


@dataclass
class Item:
    """Eén kandidaat-nieuwsfeit uit een bron."""

    titel: str
    url: str
    bron: str
    brontype: str
    gepubliceerd: datetime
    samenvatting: str = ""
    # Bronspecifieke signalen: sterren, punten, downloads, auteurs, ...
    metriek: dict = field(default_factory=dict)
    # Wordt gevuld door score.py
    voorscore: float = 0.0
    nl_relevant: bool = False

    def __post_init__(self) -> None:
        self.url = canonicaliseer_url(self.url)
        if self.gepubliceerd.tzinfo is None:
            self.gepubliceerd = self.gepubliceerd.replace(tzinfo=timezone.utc)

    @property
    def id(self) -> str:
        return hashlib.sha256(self.url.encode("utf-8")).hexdigest()[:16]

    @property
    def leeftijd_uren(self) -> float:
        delta = datetime.now(timezone.utc) - self.gepubliceerd
        return max(delta.total_seconds() / 3600.0, 0.0)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["gepubliceerd"] = self.gepubliceerd.isoformat()
        d["id"] = self.id
        return d


@dataclass
class Selectie:
    """Eén door de LLM gekozen en geschreven item in de dagelijkse editie."""

    kop: str
    wat: str
    waarom: str
    url: str
    bron: str
    categorie: str = ""

    def as_dict(self) -> dict:
        return asdict(self)
