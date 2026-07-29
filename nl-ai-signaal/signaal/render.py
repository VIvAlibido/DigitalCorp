"""Output: JSON (archief/API), Markdown (web) en HTML (e-mail)."""

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


def datum_nl(d: date) -> str:
    return f"{_DAGEN[d.weekday()]} {d.day} {_MAANDEN[d.month - 1]} {d.year}"


def naar_json(selecties: list[Selectie], d: date) -> str:
    return json.dumps(
        {"datum": d.isoformat(), "items": [s.as_dict() for s in selecties]},
        ensure_ascii=False,
        indent=2,
    )


def naar_markdown(selecties: list[Selectie], d: date) -> str:
    regels = [
        f"# NL-AI-Signaal — {datum_nl(d)}",
        "",
        f"De {len(selecties)} dingen die vandaag in AI gebeurd zijn en ertoe doen.",
        "",
    ]
    for nummer, s in enumerate(selecties, 1):
        regels += [
            f"## {nummer}. {s.kop}",
            "",
            f"*{s.categorie} · {s.bron}*",
            "",
            s.wat,
            "",
            f"**Waarom het ertoe doet:** {s.waarom}",
            "",
            f"[Lees verder →]({s.url})",
            "",
            "---",
            "",
        ]
    regels.append("*Samengesteld door NL-AI-Signaal. Reageren? Beantwoord deze mail.*")
    return "\n".join(regels)


def naar_html(selecties: list[Selectie], d: date) -> str:
    """E-mail-HTML: tabellen en inline styles, want mailclients kunnen weinig."""
    e = html.escape
    blokken = []
    for nummer, s in enumerate(selecties, 1):
        blokken.append(
            f"""
      <tr><td style="padding:0 0 28px 0;">
        <div style="font:600 12px/1.4 -apple-system,Segoe UI,Roboto,sans-serif;
                    color:#8a7f6d;text-transform:uppercase;letter-spacing:.06em;">
          {nummer} · {e(s.categorie)} · {e(s.bron)}
        </div>
        <h2 style="margin:6px 0 10px;font:600 19px/1.35 Georgia,serif;color:#1c1a17;">
          {e(s.kop)}
        </h2>
        <p style="margin:0 0 10px;font:400 15px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;
                  color:#33302b;">{e(s.wat)}</p>
        <p style="margin:0 0 12px;font:400 15px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;
                  color:#33302b;">
          <strong style="color:#1c1a17;">Waarom het ertoe doet:</strong> {e(s.waarom)}
        </p>
        <a href="{e(s.url)}" style="font:600 14px/1 -apple-system,Segoe UI,Roboto,sans-serif;
           color:#a4552b;text-decoration:none;">Lees verder →</a>
      </td></tr>"""
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
           style="max-width:600px;background:#fffdf8;border-radius:8px;padding:32px;">
      <tr><td style="padding:0 0 8px 0;">
        <div style="font:700 22px/1.2 Georgia,serif;color:#1c1a17;">NL-AI-Signaal</div>
        <div style="font:400 14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#8a7f6d;">
          {e(datum_nl(d))} · {len(selecties)} dingen die ertoe doen
        </div>
      </td></tr>
      <tr><td style="padding:20px 0 24px 0;">
        <hr style="border:0;border-top:1px solid #e5ded1;margin:0;">
      </td></tr>
      {"".join(blokken)}
      <tr><td style="padding:8px 0 0 0;border-top:1px solid #e5ded1;
                     font:400 13px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;color:#8a7f6d;">
        Je ontvangt deze mail omdat je je hebt aangemeld voor NL-AI-Signaal.<br>
        <a href="{{{{unsubscribe}}}}" style="color:#8a7f6d;">Uitschrijven</a> ·
        <a href="{{{{preferences}}}}" style="color:#8a7f6d;">Voorkeuren</a>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""
