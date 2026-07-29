"""Hugging Face — nieuw gepubliceerde modellen, gesorteerd op trending."""

from __future__ import annotations

from ..model import Item
from .basis import haal_op, parse_datum

API = "https://huggingface.co/api/models"


def verzamel(cfg: dict) -> list[Item]:
    data = haal_op(
        API,
        params={"sort": "trendingScore", "direction": -1, "limit": cfg.get("max", 25)},
        accept_json=True,
    )
    if not data:
        return []

    items = []
    for model in data:
        model_id = model.get("modelId") or model.get("id")
        if not model_id:
            continue
        taken = model.get("pipeline_tag") or "onbekend"
        items.append(
            Item(
                titel=f"{model_id} ({taken})",
                url=f"https://huggingface.co/{model_id}",
                bron="Hugging Face",
                brontype="huggingface",
                gepubliceerd=parse_datum(model.get("lastModified") or model.get("createdAt")),
                samenvatting=f"Model voor {taken}. Tags: {', '.join(model.get('tags', [])[:8])}",
                metriek={
                    "downloads": model.get("downloads", 0),
                    "likes": model.get("likes", 0),
                    "trending": model.get("trendingScore", 0),
                },
            )
        )
    return items
