"""E-mailuitvoer: JSON (archief), Markdown (leesbaar) en HTML (de mail zelf).

De opmaak volgt twee onderzoeksresultaten. Uit onderzoek naar
nieuwsbriefgeloofwaardigheid (Trust Project, American Press Institute, IPTC):
zichtbare scheiding tussen feit en duiding, herkomst per bericht, een
methodeverantwoording en een vindbaar correctiebeleid. Uit de Smart
Brevity-opbouw: elk bericht in onder de minuut te begrijpen, "wat het betekent" als vast
gelabeld en ingesprongen onderdeel, één kolom, vetgedrukte ankerpunten.

De mail is bewust korter dan de website. Het volledige feitenrelaas staat
online; hier staat wat je moet weten om te beslissen of je doorklikt. Dat houdt
de belofte van vier minuten haalbaar én geeft de site bestaansrecht.
"""

from __future__ import annotations

import html
import json
from datetime import date

from .model import Beschouwing, Editie, Selectie

MERK = "AI Bulletin"
SITE = "https://aibulletin.nl"

_MAANDEN = [
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]
_DAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]

CORRECTIEBELEID = (
    "Fout gezien? Mail ons — correcties verschijnen bovenaan de eerstvolgende "
    "editie en worden in het online archief bij het oorspronkelijke item gezet."
)

_SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif"


def datum_nl(d: date) -> str:
    return f"{_DAGEN[d.weekday()]} {d.day} {_MAANDEN[d.month - 1]} {d.year}"


def kort_datum(iso: str) -> str:
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


def bericht_url(editie: Editie, item: Selectie) -> str:
    return f"{SITE}/{editie.stam}/{item.slug}"


def leestijd(editie: Editie) -> int:
    """Geschatte leestijd in minuten, op 200 woorden per minuut."""
    delen = [editie.intro, editie.voor_bedrijven]
    if editie.beschouwing:
        delen += editie.beschouwing.alineas + [editie.beschouwing.kern]
    delen += [f"{i.kop} {i.kern} {i.waarom}" for i in editie.items]
    if editie.toepassing:
        t = editie.toepassing
        delen.append(f"{t.titel} {t.intro} {' '.join(t.stappen)} {t.niet_doen}")
    woorden = sum(len(d.split()) for d in delen)
    return max(round(woorden / 200), 1)


def methodeverantwoording(editie: Editie) -> str:
    """Hoe deze editie tot stand kwam — in gewone taal, niet als disclaimer."""
    omvang = (
        f"Vandaag zijn {editie.kandidaten} berichten uit {editie.bronnen} bronnen "
        "bekeken. "
        if editie.kandidaten and editie.bronnen
        else ""
    )
    return (
        f"{omvang}Selectie en tekst komen tot stand met een taalmodel onder vaste "
        "redactieregels: alleen verifieerbare feiten in de berichten, duiding "
        "herkenbaar apart gezet, en een kanttekening bij elk cijfer dat niet "
        "onafhankelijk is getoetst. We verwijzen naar de meest primaire bron — een "
        "persbericht van de toezichthouder gaat voor een nieuwsbericht daarover — "
        "en nemen geen teksten van anderen over."
    )


# ─────────────────────────────── JSON ────────────────────────────────

def naar_json(editie: Editie) -> str:
    return json.dumps(editie.as_dict(), ensure_ascii=False, indent=2)


# ────────────────────────────── Markdown ─────────────────────────────

def naar_markdown(editie: Editie) -> str:
    r = [f"# {MERK} — {datum_nl(editie.datum)}", ""]
    if editie.onderwerp:
        r.append(f"*Onderwerpregel: “{editie.onderwerp}” ({len(editie.onderwerp)} tekens)*")
        if editie.preheader:
            r.append(f"*Preheader: “{editie.preheader}”*")
        r.append("")
    r += [f"*{len(editie.items)} berichten · {leestijd(editie)} minuten lezen*", ""]

    if editie.intro:
        r += [f"> {editie.intro}", ""]
    r += ["---", ""]

    if editie.beschouwing:
        b = editie.beschouwing
        r += [f"## {b.titel}", "", f"*{b.kern}*", ""]
        r += [f"**{b.auteur}**" if b.auteur else "", ""]
        for alinea in b.alineas:
            r += [f"### {alinea[2:]}" if alinea.startswith("# ") else alinea, ""]
        if b.bron:
            r += [f"*Gebaseerd op: [{b.bron}]({b.url})*" if b.url else f"*Bron: {b.bron}*", ""]
        r += ["---", ""]

    # De toepassing staat vóór de zes. Dit is het onderdeel waar AI Bulletin om
    # bekend staat; onder zes nieuwsberichten is het een voetnoot.
    if editie.toepassing:
        t = editie.toepassing
        titel = f"{t.titel} — {t.tijd}" if t.tijd else t.titel
        r += [f"## Vandaag toepassen: {titel}", "", t.intro, ""]
        r += [f"{n}. {stap}" for n, stap in enumerate(t.stappen, 1)]
        r.append("")
        if t.niet_doen:
            r += [f"**Wat je níét hoeft te doen:** {t.niet_doen}", ""]
        r += ["---", ""]

    for nummer, s in enumerate(editie.items, 1):
        r += [
            f"## {nummer}. {s.kop}", "",
            f"**{s.kern}**", "",
            s.wat, "",
            f"**Wat het betekent** — {s.waarom}", "",
        ]
        if s.kanttekening:
            r += [f"> **Kanttekening:** {s.kanttekening}", ""]
        herkomst = " · ".join(filter(None, [s.categorie, s.bron, kort_datum(s.datum)]))
        r += [f"[Naar de bron →]({s.url}) · *{herkomst}*", "", "---", ""]

    if editie.voor_bedrijven:
        r += ["### Voor jouw bedrijf", "", editie.voor_bedrijven, "", "---", ""]

    r += [
        "### Hoe deze editie tot stand kwam", "",
        methodeverantwoording(editie), "",
        f"*{CORRECTIEBELEID}*", "",
    ]
    return "\n".join(r)


# ──────────────────────────────── HTML ───────────────────────────────

def _bericht_html(nummer: int, s: Selectie, editie: Editie) -> str:
    e = html.escape
    herkomst = " · ".join(filter(None, [s.bron, kort_datum(s.datum)]))
    # De methodeverantwoording onderaan deze mail belooft "een kanttekening bij
    # elk cijfer dat niet onafhankelijk is getoetst". Die kanttekeningen stonden
    # wel in de Markdown en op de site, maar niet in de mail — de belofte werd
    # dus verstuurd zonder wat erbij hoort. Kleiner gezet dan de duiding: het is
    # een voorbehoud, geen tweede mening.
    kanttekening = ""
    if getattr(s, "kanttekening", ""):
        kanttekening = f"""
    <p style="margin:0 0 7px;font:400 12.5px/1.6 {_SANS};color:#7a7264;">
      <span style="font:600 12.5px/1.6 {_SANS};color:#5c5548;">Kanttekening:</span>
      {e(s.kanttekening)}</p>"""
    return f"""
  <tr><td style="padding:16px 34px 0;">
    <h2 style="margin:0 0 5px;font:600 17px/1.35 Georgia,serif;color:#1c1a17;">
      {nummer}. {e(s.kop)}</h2>
    <p style="margin:0 0 6px;font:400 15px/1.6 {_SANS};color:#33302b;">{e(s.kern)}</p>
    <p style="margin:0 0 7px;font:400 14px/1.6 {_SANS};color:#4a4437;
              border-left:2px solid #e5ded1;padding-left:11px;">
      <span style="font:600 10px/1 {_SANS};color:#a08a72;text-transform:uppercase;
                   letter-spacing:.09em;">Wat het betekent</span><br>{e(s.waarom)}</p>{kanttekening}
    <a href="{e(bericht_url(editie, s))}"
       style="font:600 13px/1 {_SANS};color:#a4552b;text-decoration:none;">Het hele verhaal →</a>
    <span style="font:400 12px/1 {_SANS};color:#8a7f6d;">&nbsp;{e(herkomst)}</span>
  </td></tr>
  <tr><td style="padding:18px 34px 0;">
    <hr style="border:0;border-top:1px solid #f0eae0;margin:0;"></td></tr>"""


def _toepassing_html(editie: Editie) -> str:
    if not editie.toepassing:
        return ""
    e = html.escape
    t = editie.toepassing
    stappen = "".join(
        f"""
          <tr>
            <td valign="top" width="26" style="font:600 14px/1.5 {_SANS};color:#a4552b;">{n}</td>
            <td style="padding-bottom:12px;font:400 14px/1.6 {_SANS};color:#33302b;">{e(stap)}</td>
          </tr>"""
        for n, stap in enumerate(t.stappen, 1)
    )
    niet_doen = (
        f"""
        <div style="margin-top:16px;padding-top:13px;border-top:1px solid #ecdccd;
                    font:400 13px/1.6 {_SANS};color:#6b6355;">
          <strong style="color:#4a4437;">Wat je níét hoeft te doen:</strong> {e(t.niet_doen)}
        </div>"""
        if t.niet_doen
        else ""
    )
    kop = e(t.titel) + (e(f" — {t.tijd}") if t.tijd else "")
    return f"""
  <tr><td style="padding:28px 34px 0;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background:#faf4ee;border:1px solid #ecdccd;border-radius:8px;">
      <tr><td style="padding:22px 24px 24px;">
        <div style="font:600 11px/1.4 {_SANS};color:#a4552b;
                    text-transform:uppercase;letter-spacing:.08em;">Vandaag toepassen</div>
        <h2 style="margin:7px 0 6px;font:600 19px/1.32 Georgia,serif;color:#1c1a17;">{kop}</h2>
        <p style="margin:0 0 15px;font:400 14px/1.6 {_SANS};color:#4a4437;">{e(t.intro)}</p>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{stappen}
        </table>{niet_doen}
      </td></tr>
    </table>
  </td></tr>"""


def _beschouwing_html(editie: Editie) -> str:
    """Het zondagsstuk in de mail. Bewust anders van vorm dan de zes berichten:
    de lezer moet in één oogopslag zien dat hier een mens aan het woord is."""
    if not editie.beschouwing:
        return ""
    e = html.escape
    b = editie.beschouwing
    body = ""
    for alinea in b.alineas:
        if alinea.startswith("# "):
            body += (f'<h3 style="margin:22px 0 8px;font:600 16px/1.35 Georgia,serif;'
                     f'color:#1c1a17;">{e(alinea[2:])}</h3>')
        else:
            body += (f'<p style="margin:0 0 13px;font:400 15.5px/1.68 Georgia,serif;'
                     f'color:#33302b;">{e(alinea)}</p>')
    herkomst = (
        f'<p style="margin:16px 0 0;font:400 12.5px/1.6 {_SANS};color:#8a7f6d;">'
        f'Gebaseerd op: <a href="{e(b.url)}" style="color:#a4552b;">{e(b.bron)}</a></p>'
        if b.bron and b.url else ""
    )
    return f"""
  <tr><td style="padding:26px 34px 0;">
    <div style="border-top:2px solid #1c1a17;padding-top:18px;">
      <div style="font:600 11px/1.4 {_SANS};color:#a4552b;text-transform:uppercase;
                  letter-spacing:.08em;">Zondagsstuk</div>
      <h2 style="margin:9px 0 7px;font:600 25px/1.24 Georgia,serif;color:#1c1a17;">
        {e(b.titel)}</h2>
      <p style="margin:0 0 6px;font:400 16px/1.55 {_SANS};color:#4a4437;">{e(b.kern)}</p>
      <p style="margin:0 0 20px;font:600 13px/1.4 {_SANS};color:#8a7f6d;">
        {e(b.auteur)}</p>
      {body}{herkomst}
    </div>
  </td></tr>"""


def naar_html(editie: Editie) -> str:
    """E-mail-HTML: tabellen en inline styles, want mailclients kunnen weinig."""
    e = html.escape

    preheader = (
        f"""
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{e(editie.preheader)}
{"&nbsp;&zwnj;" * 60}</div>"""
        if editie.preheader
        else ""
    )

    intro = (
        f"""
  <tr><td style="padding:22px 34px 0;">
    <div style="border-left:3px solid #a4552b;padding:2px 0 2px 14px;
                font:400 17px/1.55 Georgia,serif;color:#1c1a17;">{e(editie.intro)}</div>
  </td></tr>"""
        if editie.intro
        else ""
    )

    bedrijven = (
        f"""
  <tr><td style="padding:22px 34px 0;">
    <div style="font:600 11px/1.4 {_SANS};color:#8a7f6d;text-transform:uppercase;
                letter-spacing:.08em;margin-bottom:7px;">Voor jouw bedrijf</div>
    <p style="margin:0;font:400 14px/1.6 {_SANS};color:#4a4437;">{e(editie.voor_bedrijven)}
      <a href="{SITE}/voorkeuren" style="color:#8a7f6d;">Niet relevant? Zet dit blok uit →</a>
    </p>
  </td></tr>"""
        if editie.voor_bedrijven
        else ""
    )

    berichten = "".join(_bericht_html(n, s, editie) for n, s in enumerate(editie.items, 1))

    return f"""<!doctype html>
<html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(editie.onderwerp or f"{MERK} — {datum_nl(editie.datum)}")}</title></head>
<body style="margin:0;padding:0;background:#f4f1ea;">{preheader}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background:#f4f1ea;padding:24px 14px 44px;">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="max-width:640px;background:#fffdf8;border-radius:10px;">

  <tr><td style="padding:32px 34px 0;">
    <table role="presentation" width="100%"><tr>
      <td style="font:700 21px/1.2 Georgia,serif;color:#1c1a17;">{MERK}</td>
      <td align="right" style="font:600 12px/1 {_SANS};color:#a4552b;background:#f6ece4;
                 border-radius:20px;padding:6px 11px;white-space:nowrap;">
        {leestijd(editie)} min</td>
    </tr></table>
    <div style="font:400 13px/1.5 {_SANS};color:#8a7f6d;margin-top:5px;">
      {e(datum_nl(editie.datum).capitalize())} · AI-nieuws voor Nederland</div>
  </td></tr>
{intro}
{_beschouwing_html(editie)}
{_toepassing_html(editie)}
  <tr><td style="padding:26px 34px 0;">
    <div style="font:600 11px/1.4 {_SANS};color:#8a7f6d;text-transform:uppercase;
                letter-spacing:.08em;">De zes</div>
    <div style="font:400 12.5px/1.5 {_SANS};color:#a09684;margin-top:4px;">
      Eerst het feit. Wat ingesprongen staat, is onze duiding.</div>
  </td></tr>
{berichten}
{bedrijven}

  <tr><td style="padding:26px 34px 30px;">
    <div style="border-top:1px solid #e5ded1;padding-top:18px;
                font:400 12.5px/1.65 {_SANS};color:#8a7f6d;">
      <strong style="color:#4a4437;">Te veel mail?</strong> Je kunt overstappen naar
      wekelijks of alleen groot nieuws —
      <a href="{SITE}/voorkeuren" style="color:#a4552b;">pas je voorkeuren aan</a>.
      Uitschrijven mag ook, maar dat hoeft niet je eerste optie te zijn.
      <br><br>
      <strong style="color:#4a4437;">Hoe deze editie tot stand kwam</strong><br>
      {e(methodeverantwoording(editie))}
      <br><br>
      {e(CORRECTIEBELEID)}
      <br><br>
      <a href="{SITE}/voorkeuren" style="color:#8a7f6d;">Voorkeuren</a> ·
      <a href="{SITE}/archief" style="color:#8a7f6d;">Archief</a> ·
      <a href="{{{{unsubscribe}}}}" style="color:#8a7f6d;">Uitschrijven</a>
      <br><br>
      <strong style="color:#4a4437;">{MERK}</strong> · aibulletin.nl
    </div>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""
