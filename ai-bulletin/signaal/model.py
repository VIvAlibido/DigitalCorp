"""Kerndatatypes die door de hele pijplijn heen gaan."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone

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
    """Eén door de LLM gekozen en geschreven item in de dagelijkse editie.

    De scheiding tussen `wat` (feit) en `waarom` (duiding) is bewust: de lezer
    moet kunnen zien waar de verifieerbare bewering ophoudt en de redactionele
    interpretatie begint. `datum` en `bron` staan erbij zodat elk item op zijn
    eigen merites te controleren is.
    """

    kop: str
    # Eén zin zonder jargon die het hele bericht draagt. Wie alleen de kop en
    # deze zin leest, snapt het. Alles daaronder is verdieping, geen voorwaarde.
    kern: str
    wat: str
    waarom: str
    url: str
    bron: str
    categorie: str = ""
    # Wanneer de gebeurtenis plaatsvond — niet wanneer wij erover schrijven.
    datum: str = ""
    # Voorbehoud bij het feit zelf: oud veldwerk, één bron, voorlopig cijfer.
    kanttekening: str = ""

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def slug(self) -> str:
        """URL-fragment voor de eigen pagina van dit bericht."""
        return _slug(self.kop)


@dataclass
class Toepassing:
    """Het onderdeel 'Vandaag toepassen' — één ding dat de lezer vandaag kan doen.

    Dit is het enige deel van de editie dat niet uit het nieuws volgt maar
    zelf bedacht wordt, en daarmee het deel dat een concurrent niet kan
    scrapen. Drie stappen, want twee is te dun en vier leest als huiswerk.
    """

    titel: str
    intro: str
    stappen: list[str] = field(default_factory=list)
    # Wat expliciet níét hoeft. Geruststelling is even waardevol als een
    # instructie, en voorkomt dat lezers meer doen dan nodig.
    niet_doen: str = ""
    tijd: str = ""
    categorie: str = ""

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def slug(self) -> str:
        return _slug(self.titel)


@dataclass
class Beschouwing:
    """Het zondagsstuk: één onderwerp, uitgeschreven, met een naam eronder.

    Dit is het enige deel van AI Bulletin dat níét uit een bron volgt en niet
    door de automaat wordt gemaakt. Zes dagen machinewerk met verantwoording,
    één dag mensenwerk met een handtekening — en dat verschil is voor de lezer
    zichtbaar. Daarom staat `auteur` hier verplicht bij: een stuk met een mening
    zonder naam is het slechtste van twee werelden.

    In `alineas` begint een tussenkop met "# ". Dat is de enige opmaak; de rest
    is gewone tekst.
    """

    titel: str
    kern: str
    alineas: list[str] = field(default_factory=list)
    auteur: str = ""
    # Waar het stuk op teruggrijpt, als dat er is: een rapport, een cijfer.
    bron: str = ""
    url: str = ""

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def slug(self) -> str:
        return _slug(self.titel)

    @property
    def woorden(self) -> int:
        return sum(len(a.split()) for a in self.alineas if not a.startswith("# "))


@dataclass
class Editie:
    """Alles wat één editie uitmaakt.

    Vervangt de losse parameters die render- en schrijffuncties eerder
    doorgaven; die lijst groeide bij elke nieuwe rubriek en was niet meer
    te overzien.
    """

    datum: date
    items: list[Selectie] = field(default_factory=list)
    onderwerp: str = ""
    preheader: str = ""
    intro: str = ""
    toepassing: Toepassing | None = None
    voor_bedrijven: str = ""
    # Alleen op zondag. Zie Beschouwing.
    beschouwing: Beschouwing | None = None
    # Verantwoording: hoeveel kandidaten en bronnen deze editie opleverden.
    kandidaten: int | None = None
    bronnen: int | None = None

    @property
    def stam(self) -> str:
        return self.datum.isoformat()

    def as_dict(self) -> dict:
        return {
            "datum": self.datum.isoformat(),
            "onderwerp": self.onderwerp,
            "preheader": self.preheader,
            "intro": self.intro,
            "items": [i.as_dict() for i in self.items],
            "toepassing": self.toepassing.as_dict() if self.toepassing else None,
            "beschouwing": self.beschouwing.as_dict() if self.beschouwing else None,
            "voor_bedrijven": self.voor_bedrijven,
            "kandidaten": self.kandidaten,
            "bronnen": self.bronnen,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Editie":
        toepassing = data.get("toepassing")
        beschouwing = data.get("beschouwing")
        return cls(
            datum=date.fromisoformat(data["datum"]),
            items=[Selectie(**rij) for rij in data.get("items", [])],
            onderwerp=data.get("onderwerp", ""),
            preheader=data.get("preheader", ""),
            intro=data.get("intro", ""),
            toepassing=Toepassing(**toepassing) if toepassing else None,
            beschouwing=Beschouwing(**beschouwing) if beschouwing else None,
            voor_bedrijven=data.get("voor_bedrijven", ""),
            kandidaten=data.get("kandidaten"),
            bronnen=data.get("bronnen"),
        )


def _slug(tekst: str) -> str:
    """Leesbare, stabiele URL uit een kop of titel."""
    zonder_accenten = (
        unicodedata.normalize("NFKD", tekst).encode("ascii", "ignore").decode("ascii")
    )
    schoon = re.sub(r"[^a-z0-9]+", "-", zonder_accenten.lower()).strip("-")
    return schoon[:70].rstrip("-") or "bericht"
