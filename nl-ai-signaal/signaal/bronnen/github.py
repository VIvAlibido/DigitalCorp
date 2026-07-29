"""GitHub — repos die recent zijn aangemaakt en snel sterren winnen.

Sterren-per-dag is een betere proxy voor "dit gebeurt nu" dan het absolute
aantal sterren: een repo van drie jaar oud met 40k sterren is geen nieuws.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests

from ..model import Item
from .basis import TIMEOUT, USER_AGENT, parse_datum

API = "https://api.github.com/search/repositories"
AI_TREFWOORDEN = (
    "llm", "ai", "agent", "transformer", "diffusion", "rag", "inference",
    "prompt", "embedding", "gpt", "claude", "mcp", "fine-tun", "neural",
)


def verzamel(cfg: dict) -> list[Item]:
    sinds = (datetime.now(timezone.utc) - timedelta(days=14)).date().isoformat()
    query = cfg.get("query", "created:>{sinds} stars:>25").format(sinds=sinds)

    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    # Zonder token: 10 requests/minuut. Met token: 30. Zet GITHUB_TOKEN in CI.
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(
            API,
            params={"q": query, "sort": "stars", "order": "desc",
                    "per_page": cfg.get("max", 30)},
            headers=headers,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return []

    items = []
    for repo in data.get("items", []):
        beschrijving = repo.get("description") or ""
        tekst = f"{repo.get('name', '')} {beschrijving} {' '.join(repo.get('topics', []))}".lower()
        if not any(w in tekst for w in AI_TREFWOORDEN):
            continue

        aangemaakt = parse_datum(repo.get("created_at"))
        dagen = max((datetime.now(timezone.utc) - aangemaakt).days, 1)
        sterren = repo.get("stargazers_count", 0)

        items.append(
            Item(
                titel=f"{repo['full_name']} — {beschrijving}"[:200],
                url=repo["html_url"],
                bron="GitHub",
                brontype="github",
                # Push-datum is het echte activiteitssignaal, niet de aanmaakdatum.
                gepubliceerd=parse_datum(repo.get("pushed_at") or repo.get("created_at")),
                samenvatting=beschrijving,
                metriek={
                    "sterren": sterren,
                    "sterren_per_dag": round(sterren / dagen, 1),
                    "taal": repo.get("language"),
                },
            )
        )
    return items
