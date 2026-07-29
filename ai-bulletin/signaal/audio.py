"""Audio-editie: de dagelijkse briefing als Nederlands gesproken fragment.

Dit is bewust een eigen stap. Het voorleesscript is niet dezelfde tekst als de
mail: geschreven Nederlands met URL's, haakjes en afkortingen klinkt beroerd
als je het letterlijk door een TTS-engine haalt.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import date
from pathlib import Path

from .model import Selectie
from .render import datum_nl

log = logging.getLogger(__name__)

# Afkortingen die een TTS-stem in het Nederlands verkeerd uitspreekt.
_UITSPRAAK = {
    r"\bLLM\b": "el-el-em",
    r"\bAPI\b": "ee-pee-ie",
    r"\bAI\b": "ee-ie",
    r"\bGPU\b": "gee-pee-uu",
    r"\bAVG\b": "aa-vee-gee",
    r"\bEU\b": "ee-uu",
    r"\bopen source\b": "open sors",
    r"\bSOTA\b": "state of the art",
}


class AudioFout(RuntimeError):
    pass


def maak_script(selecties: list[Selectie], d: date) -> str:
    """Zet de editie om naar tekst die hardop goed klinkt."""
    delen = [
        f"AI Bulletin, {datum_nl(d)}.",
        f"Dit zijn de {len(selecties)} dingen die vandaag in AI gebeurd zijn.",
        "",
    ]
    for nummer, s in enumerate(selecties, 1):
        # De kernzin is geschreven om hardop te werken: geen jargon, één
        # gedachte. Hij opent het item; de details volgen erachteraan.
        delen += [
            f"{nummer}. {_leesbaar(s.kop)}",
            _leesbaar(s.kern),
            _leesbaar(s.wat),
            f"Waarom dit ertoe doet: {_leesbaar(s.waarom)}",
            "",
        ]
    delen.append("De links staan in de nieuwsbrief. Tot morgen.")
    return "\n".join(delen)


def _leesbaar(tekst: str) -> str:
    # URL's zijn onverstaanbaar; de luisteraar heeft de mail ernaast.
    tekst = re.sub(r"https?://\S+", "", tekst)
    for patroon, vervanging in _UITSPRAAK.items():
        tekst = re.sub(patroon, vervanging, tekst)
    # Haakjes worden voorgelezen als pauzes; maak er komma's van.
    tekst = tekst.replace(" (", ", ").replace(")", ",")
    return " ".join(tekst.split())


def genereer(script: str, config: dict, d: date) -> Path:
    """Zet het script om naar MP3 via de ingestelde provider."""
    audio_cfg = config.get("audio", {})
    provider = audio_cfg.get("provider", "elevenlabs")
    uitvoermap = Path(audio_cfg.get("map", "audio"))
    uitvoermap.mkdir(parents=True, exist_ok=True)
    doel = uitvoermap / f"{d.isoformat()}.mp3"

    if provider == "elevenlabs":
        audio = _elevenlabs(script, audio_cfg)
    else:
        raise AudioFout(
            f"audioprovider '{provider}' is niet geïmplementeerd. "
            "ElevenLabs (multilingual v2) en Azure Neural (nl-NL) zijn beide "
            "geschikt voor Nederlands; zie README."
        )

    doel.write_bytes(audio)
    log.info("audio geschreven naar %s (%d kB)", doel, len(audio) // 1024)
    return doel


def _elevenlabs(script: str, cfg: dict) -> bytes:
    import requests

    sleutel = os.environ.get("ELEVENLABS_API_KEY")
    stem = cfg.get("stem") or os.environ.get("ELEVENLABS_VOICE_ID")
    if not (sleutel and stem):
        raise AudioFout("ELEVENLABS_API_KEY of stem-ID ontbreekt")

    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{stem}",
        headers={"xi-api-key": sleutel, "Content-Type": "application/json"},
        json={
            "text": script,
            # Multilingual is vereist voor bruikbaar Nederlands; het Engelstalige
            # model spreekt Nederlandse woorden met een Engels accent uit.
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=120,
    )
    if resp.status_code != 200:
        raise AudioFout(f"ElevenLabs gaf {resp.status_code}: {resp.text[:200]}")
    return resp.content
