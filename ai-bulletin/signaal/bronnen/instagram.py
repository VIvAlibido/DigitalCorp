"""Instagram — accounts van derden volgen.

Belangrijk, en de reden dat deze bron standaard uit staat:

Meta's officiële Instagram Graph API geeft **geen** toegang tot de posts van
willekeurige accounts. Wat wél kan:

  * je eigen Business/Creator-account uitlezen (media, insights, mentions);
  * `business_discovery`: van een ánder *Business/Creator*-account de publieke
    profielvelden en recente media opvragen — maar alleen vanuit jouw eigen
    Business-account, alleen voor zakelijke accounts, en zonder Stories/Reels-
    insights. Persoonlijke accounts vallen er volledig buiten.
  * oEmbed voor het embedden van één specifieke, bekende post.

Er is dus geen officiële route om "volg deze 10 accounts en geef me hun nieuwe
posts". De praktische opties:

  1. `business_discovery` (gratis, officieel, beperkt tot zakelijke accounts) —
     implementeer als `provider: "graph_business_discovery"`.
  2. Een commerciële scraping-provider (Apify, Bright Data, Phyllo). Werkt in de
     praktijk, kost geld, en schuurt met Instagram's gebruiksvoorwaarden —
     het risico ligt bij de afnemer, niet bij de leverancier.
  3. Scrapen in eigen beheer. Afgeraden: schendt de voorwaarden, breekt continu,
     en leidt tot IP- en accountblokkades.

Deze module implementeert (1) en laat (2) via een adapter toe. (3) niet.
"""

from __future__ import annotations

import logging
import os

from ..model import Item
from .basis import haal_op, parse_datum

log = logging.getLogger(__name__)

GRAPH = "https://graph.facebook.com/v21.0"


def verzamel(cfg: dict) -> list[Item]:
    provider = cfg.get("provider")
    if provider == "graph_business_discovery":
        return _business_discovery(cfg)
    if provider:
        return _via_externe_provider(provider, cfg)
    log.info("instagram: geen provider ingesteld — bron overgeslagen")
    return []


def _business_discovery(cfg: dict) -> list[Item]:
    """Officiële route. Vereist een eigen IG Business-account + token.

    Zet IG_USER_ID (jouw eigen Instagram Business-account-ID) en IG_ACCESS_TOKEN.
    De doelaccounts moeten zélf Business- of Creator-accounts zijn.
    """
    eigen_id = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not (eigen_id and token):
        log.warning("instagram: IG_USER_ID of IG_ACCESS_TOKEN ontbreekt")
        return []

    items: list[Item] = []
    for account in cfg.get("accounts") or []:
        velden = (
            f"business_discovery.username({account})"
            "{username,media.limit(5){caption,permalink,timestamp,like_count,comments_count}}"
        )
        data = haal_op(
            f"{GRAPH}/{eigen_id}",
            params={"fields": velden, "access_token": token},
            accept_json=True,
        )
        if not data or "business_discovery" not in data:
            log.warning("instagram: geen data voor @%s (geen zakelijk account?)", account)
            continue

        for post in data["business_discovery"].get("media", {}).get("data", []):
            caption = (post.get("caption") or "").strip()
            if not caption:
                continue
            items.append(
                Item(
                    titel=caption.split("\n")[0][:200],
                    url=post["permalink"],
                    bron=f"Instagram @{account}",
                    brontype="instagram",
                    gepubliceerd=parse_datum(post.get("timestamp")),
                    samenvatting=caption[:600],
                    metriek={
                        "likes": post.get("like_count", 0),
                        "reacties": post.get("comments_count", 0),
                    },
                )
            )
    return items


def _via_externe_provider(provider: str, cfg: dict) -> list[Item]:
    """Haak voor een betaalde provider (Apify/Bright Data/Phyllo).

    Bewust niet ingevuld: elke provider heeft een eigen schema en een eigen
    contract. Implementeer hier de mapping naar Item zodra je een keuze maakt —
    en lees eerst hun voorwaarden én die van Instagram.
    """
    raise NotImplementedError(
        f"Instagram-provider '{provider}' is niet geïmplementeerd. "
        "Zie de module-docstring voor de afweging tussen de opties."
    )
