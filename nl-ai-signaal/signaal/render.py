"""Output: JSON (archief/API), Markdown (web) en HTML (e-mail).

De vormgeving volgt wat onderzoek naar nieuwsbriefgeloofwaardigheid consistent
aanwijst (Trust Project, American Press Institute, IPTC): herkenbare scheiding
tussen feit en duiding, zichtbare herkomst per item, een expliciete
methodeverantwoording, en een vindbaar correctiebeleid. Elk van die vier heeft
hier een eigen plek in het sjabloon in plaats van een belofte in de kleine
lettertjes.
"""

from __future__ import annotations

import html
import json
from datetime import date

from .model import Selectie

_MAANDEN = [
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]
_DAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]

CORRECTIEBELEID = (
    "Fout gezien? Mail ons — correcties verschijnen bovenaan de eerstvolgende "
    "editie en worden in het online archief bij het oorspronkelijke item gezet."
)


def datum_nl(d: date) -> str:
    return f"{_DAGEN[d.weekday()]} {d.day} {_MAANDEN[d.month - 1]} {d.year}"


def _kort_datum(iso: str) -> str:
    """'2026-07-27' → '27 juli'. Onvolledige datums blijven staan zoals ze zijn."""
    delen = iso.split("-")
    try:
        if len(delen) == 3:
            return f"{int(delen[2])} {_MAANDEN[int(delen[1]) - 1]}"
        if len(delen) == 2:
            return _MAANDEN[int(delen[1]) - 1]
    except (ValueError, IndexError):
        pass
    return iso


def methodeverantwoording(kandidaten: int | None = None, bronnen: int | None = None) -> str:
    """Hoe deze editie tot stand kwam — in gewone taal, niet als disclaimer."""
    omvang = (
        f"Vandaag zijn {kandidaten} berichten uit {bronnen} bronnen bekeken. "
        if kandidaten and bronnen
        else ""
    )
    return (
        f"{omvang}Selectie en tekst zijn door een taalmodel gemaakt onder vaste "
        "redactieregels: alleen verifieerbare feiten in 'wat', duiding uitsluitend "
        "in 'waarom', en een verplichte kanttekening bij elk cijfer dat niet "
        "onafhankelijk is getoetst. Er wordt altijd naar de meest primaire bron "
        "verwezen — een persbericht van de toezichthouder gaat voor een "
        "nieuwsbericht daarover. We schrijven niet over onderwerpen waarvoor we "
        "maar één bron hebben zonder dat erbij te zeggen."
    )


def naar_json(selecties: list[Selectie], d: date) -> str:
    return json.dumps(
        {"datum": d.isoformat(), "items": [s.as_dict() for s in selecties]},
        ensure_ascii=False,
        indent=2,
    )


def leestijd(selecties: list[Selectie], intro: str = "") -> int:
    """Geschatte leestijd in minuten, op 200 woorden per minuut."""
    woorden = len(intro.split()) + sum(
        len(f"{s.kop} {s.kern} {s.wat} {s.waarom} {s.kanttekening}".split())
        for s in selecties
    )
    return max(round(woorden / 200), 1)


def naar_markdown(
    selecties: list[Selectie],
    d: date,
    kandidaten: int | None = None,
    bronnen: int | None = None,
    intro: str = "",
) -> str:
    regels = [
        f"# NL-AI-Signaal — {datum_nl(d)}",
        "",
        f"*{len(selecties)} berichten · {leestijd(selecties, intro)} minuten lezen*",
        "",
    ]
    if intro:
        regels += [intro, ""]
    regels += ["---", ""]

    for nummer, s in enumerate(selecties, 1):
        herkomst = " · ".join(filter(None, [s.categorie, s.bron, _kort_datum(s.datum)]))
        regels += [
            f"## {nummer}. {s.kop}",
            "",
            f"**{s.kern}**",
            "",
            s.wat,
            "",
            f"**Waarom het ertoe doet** — {s.waarom}",
            "",
        ]
        if s.kanttekening:
            regels += [f"> **Kanttekening:** {s.kanttekening}", ""]
        # Herkomst onderaan: de lezer wil eerst weten wát er staat, en pas
        # daarna waar het vandaan komt — maar hij moet het wel kunnen vinden.
        regels += [f"[Naar de bron →]({s.url}) · *{herkomst}*", "", "---", ""]

    regels += [
        "### Hoe deze editie tot stand kwam",
        "",
        methodeverantwoording(kandidaten, bronnen),
        "",
        f"*{CORRECTIEBELEID}*",
        "",
    ]
    return "\n".join(regels)


def naar_html(
    selecties: list[Selectie],
    d: date,
    kandidaten: int | None = None,
    bronnen: int | None = None,
    intro: str = "",
) -> str:
    """E-mail-HTML: tabellen en inline styles, want mailclients kunnen weinig."""
    e = html.escape
    blokken = []
    for nummer, s in enumerate(selecties, 1):
        herkomst = " · ".join(filter(None, [s.categorie, s.bron, _kort_datum(s.datum)]))
        kanttekening = (
            f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
               style="margin:0 0 14px 0;"><tr>
          <td style="border-left:3px solid #d9cdb8;padding:8px 0 8px 12px;
                     font:400 13px/1.55 -apple-system,Segoe UI,Roboto,sans-serif;color:#6b6355;">
            <strong style="color:#4a4437;">Kanttekening:</strong> {e(s.kanttekening)}
          </td></tr></table>"""
            if s.kanttekening
            else ""
        )
        blokken.append(
            f"""
      <tr><td style="padding:0 0 34px 0;">
        <div style="font:600 11px/1.4 -apple-system,Segoe UI,Roboto,sans-serif;
                    color:#8a7f6d;text-transform:uppercase;letter-spacing:.07em;">
          {nummer} · {e(s.categorie)}
        </div>
        <h2 style="margin:7px 0 12px;font:600 20px/1.32 Georgia,serif;color:#1c1a17;">
          {e(s.kop)}
        </h2>
        <p style="margin:0 0 14px;font:400 17px/1.55 Georgia,serif;color:#4a4437;">
          {e(s.kern)}
        </p>
        <p style="margin:0 0 12px;font:400 15px/1.65 -apple-system,Segoe UI,Roboto,sans-serif;
                  color:#33302b;">{e(s.wat)}</p>
        <p style="margin:0 0 12px;font:400 15px/1.65 -apple-system,Segoe UI,Roboto,sans-serif;
                  color:#33302b;">
          <strong style="color:#1c1a17;">Waarom het ertoe doet</strong> — {e(s.waarom)}
        </p>{kanttekening}
        <div style="font:400 13px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#8a7f6d;">
          <a href="{e(s.url)}" style="font-weight:600;color:#a4552b;
             text-decoration:none;">Naar de bron →</a>
          &nbsp;{e(s.bron)}{e(f" · {_kort_datum(s.datum)}" if s.datum else "")}
        </div>
      </td></tr>"""
        )

    intro_blok = (
        f"""
      <tr><td style="padding:0 0 26px 0;">
        <p style="margin:0;font:400 16px/1.65 Georgia,serif;color:#4a4437;">{e(intro)}</p>
      </td></tr>"""
        if intro
        else ""
    )

    return f"""<!doctype html>
<html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NL-AI-Signaal — {e(datum_nl(d))}</title></head>
<body style="margin:0;padding:0;background:#f4f1ea;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background:#f4f1ea;padding:32px 16px;">
  <tr><td align="center">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="max-width:620px;background:#fffdf8;border-radius:8px;padding:36px;">
      <tr><td style="padding:0 0 6px 0;">
        <div style="font:700 22px/1.2 Georgia,serif;color:#1c1a17;">NL-AI-Signaal</div>
        <div style="font:400 14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#8a7f6d;">
          {e(datum_nl(d))} · {len(selecties)} berichten ·
          {leestijd(selecties, intro)} minuten lezen
        </div>
      </td></tr>
      <tr><td style="padding:18px 0 24px 0;">
        <hr style="border:0;border-top:1px solid #e5ded1;margin:0;">
      </td></tr>
      {intro_blok}
      {"".join(blokken)}
      <tr><td style="padding:6px 0 0 0;border-top:1px solid #e5ded1;">
        <div style="font:600 11px/1.4 -apple-system,Segoe UI,Roboto,sans-serif;color:#8a7f6d;
                    text-transform:uppercase;letter-spacing:.07em;padding:18px 0 8px 0;">
          Hoe deze editie tot stand kwam
        </div>
        <p style="margin:0 0 12px;font:400 13px/1.65 -apple-system,Segoe UI,Roboto,sans-serif;
                  color:#6b6355;">{e(methodeverantwoording(kandidaten, bronnen))}</p>
        <p style="margin:0 0 16px;font:400 13px/1.65 -apple-system,Segoe UI,Roboto,sans-serif;
                  color:#6b6355;">{e(CORRECTIEBELEID)}</p>
        <p style="margin:0;font:400 12px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;
                  color:#8a7f6d;">
          Je ontvangt deze mail omdat je je hebt aangemeld voor NL-AI-Signaal.<br>
          <a href="{{{{unsubscribe}}}}" style="color:#8a7f6d;">Uitschrijven</a> ·
          <a href="{{{{preferences}}}}" style="color:#8a7f6d;">Voorkeuren</a>
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""
