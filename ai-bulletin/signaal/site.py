"""Statische websitegenerator.

De mail is de gewoonte, de site is het bezit. Elke editie levert drie soorten
pagina's op die vanzelf blijven staan:

  /                       vandaag
  /2026-07-29/            de editie van die dag
  /2026-07-29/<slug>/     één bericht, met het volledige feitenrelaas
  /toepassingen/          de bibliotheek die dagelijks groeit
  /archief/               alle edities
  /voorkeuren/            frequentie en rubrieken kiezen

De toepassingenpagina's zijn het punt. Mensen zoeken niet op "AI-nieuws
29 juli" maar op "hoe gebruik ik AI voor offertes"; die pagina's blijven
verkeer trekken lang nadat de editie oud nieuws is.

Alles is platte HTML zonder bouwstap of framework: een map die je zo op een
statische host zet.
"""

from __future__ import annotations

import html
import json
import logging
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import keuring
from .model import Editie
from .render import MERK, datum_nl, kort_datum

log = logging.getLogger(__name__)

BESCHRIJVING = ("Elke dag één ding dat je met AI kunt doen. Plus het nieuws dat je\n                moet weten, in vier minuten.")


@dataclass
class Sitepagina:
    pad: str          # map ten opzichte van de siteroot, "" is de homepage
    titel: str
    beschrijving: str
    inhoud: str


# ─────────────────────────────── Opmaak ──────────────────────────────

def _stylesheet() -> str:
    return """
:root{--papier:#f4f1ea;--wit:#fffdf8;--inkt:#1c1a17;--zacht:#4a4437;
--gedempt:#8a7f6d;--lijn:#e5ded1;--accent:#a4552b;--accent-zacht:#faf4ee;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
--serif:Georgia,"Times New Roman",serif}
*{box-sizing:border-box}
body{margin:0;background:var(--papier);color:var(--inkt);font-family:var(--sans);
line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:var(--accent)}
.binnen{max-width:1060px;margin:0 auto;padding:0 22px}
.smal{max-width:720px}
.balk{border-bottom:1px solid var(--lijn);background:var(--wit)}
.balk-in{display:flex;align-items:center;gap:26px;height:62px}
.merk{font:700 19px/1 var(--serif);color:var(--inkt);text-decoration:none}
.nav{display:flex;gap:20px;margin-right:auto}
.nav a{font-size:14px;color:var(--zacht);text-decoration:none}
.nav a:hover{color:var(--accent)}
.knop{background:var(--accent);color:#fff;font:600 13px/1 var(--sans);padding:10px 15px;
border-radius:6px;text-decoration:none;white-space:nowrap}
.hero{background:var(--wit);border-bottom:1px solid var(--lijn);padding:52px 0 46px;text-align:center}
.hero h1{font:600 34px/1.25 var(--serif);margin:0 auto 14px;max-width:720px;letter-spacing:-.01em}
.hero-sub{font-size:16px;color:var(--zacht);max-width:600px;margin:0 auto 24px}
.aanmelden{display:flex;gap:9px;max-width:440px;margin:0 auto;flex-wrap:wrap}
.aanmelden input{flex:1;min-width:200px;padding:13px 14px;border:1px solid var(--lijn);
border-radius:7px;font-size:15px;font-family:inherit;background:#fff}
.aanmelden button{padding:13px 20px;background:var(--accent);color:#fff;border:0;
border-radius:7px;font:600 15px/1 var(--sans);cursor:pointer}
.hero-klein{font-size:12.5px;color:var(--gedempt);margin:12px 0 0}
.kolommen{display:grid;grid-template-columns:1fr 300px;gap:44px;padding-top:40px;
padding-bottom:56px;align-items:start}
.sectiekop{display:flex;align-items:baseline;gap:14px;margin-bottom:6px}
.sectiekop h2{font:600 24px/1.25 var(--serif);margin:0}
.tijd{font:600 12px/1 var(--sans);color:var(--accent);background:#f6ece4;
border-radius:20px;padding:6px 11px}
.meer{margin-left:auto;font-size:13.5px;color:var(--accent);text-decoration:none}
.ene-zin{border-left:3px solid var(--accent);padding:3px 0 3px 15px;margin:16px 0 30px;
font:400 18px/1.55 var(--serif)}
.bericht{padding:0 0 26px;margin-bottom:26px;border-bottom:1px solid var(--lijn)}
.bericht h3{font:600 20px/1.32 var(--serif);margin:8px 0}
.bericht h3 a{color:var(--inkt);text-decoration:none}
.bericht h3 a:hover{color:var(--accent)}
.kern{font-size:16px;color:var(--zacht);margin:0 0 10px}
.volledig,.waarom{font-size:15px;color:var(--zacht);margin:0 0 10px}
.waarom{border-left:2px solid var(--lijn);padding-left:13px}
.wijzer{display:block;font:600 10px/1.4 var(--sans);color:#a08a72;
text-transform:uppercase;letter-spacing:.09em;margin-bottom:2px}
.kanttekening{font-size:13.5px;color:#6b6355;border-left:3px solid #d9cdb8;
padding:6px 0 6px 12px;margin:0 0 10px}
.herkomst{font-size:13px;color:var(--gedempt);margin:0}
.tag{display:inline-block;font:600 10.5px/1 var(--sans);text-transform:uppercase;
letter-spacing:.07em;padding:5px 8px;border-radius:4px;color:#5f5744;background:#efe9dd}
.tag.regelgeving{background:#f0e6dd;color:#8a5a33}
.tag.model{background:#e6ebe6;color:#4b6150}
.tag.bedrijf{background:#ece7f0;color:#5f5075}
.tag.tooling{background:#e9edf1;color:#4a5b6b}
.tag.infrastructuur{background:#f2e8e6;color:#8a4b45}
.tag.onderzoek{background:#e8eae4;color:#5a6147}
.toepassing{background:var(--accent-zacht);border:1px solid #ecdccd;border-radius:10px;
padding:28px 30px 26px;margin-bottom:40px}
.toep-label{font:600 11px/1.4 var(--sans);color:var(--accent);text-transform:uppercase;
letter-spacing:.08em}
.toepassing h2,.toepassing h1{font:600 23px/1.3 var(--serif);margin:8px 0 6px}
.toep-intro{font-size:15px;color:var(--zacht);margin:0 0 18px}
.stappen{margin:0;padding-left:20px}
.stappen li{font-size:15px;color:var(--zacht);margin-bottom:12px;padding-left:4px}
.stappen strong{color:var(--inkt)}
.niet-doen{font-size:13.5px;color:#6b6355;border-top:1px solid #ecdccd;
padding-top:14px;margin:16px 0 0}
.rooster{display:grid;grid-template-columns:repeat(auto-fill,minmax(228px,1fr));gap:14px}
.kaartje{display:block;background:var(--wit);border:1px solid var(--lijn);border-radius:9px;
padding:16px;text-decoration:none;transition:border-color .15s}
.kaartje:hover{border-color:var(--accent)}
.kaart-tijd{font:600 11px/1 var(--sans);color:var(--accent)}
.kaartje h4{font:600 15px/1.4 var(--serif);color:var(--inkt);margin:8px 0 10px}
.kaart-tag{font-size:11.5px;color:var(--gedempt);text-transform:uppercase;letter-spacing:.05em}
.lijst{list-style:none;margin:14px 0 0;padding:0}
.lijst li{border-bottom:1px solid var(--lijn)}
.lijst a{display:flex;gap:16px;padding:12px 0;color:var(--zacht);text-decoration:none;font-size:15px}
.lijst a:hover{color:var(--accent)}
.dat{color:var(--gedempt);font-size:13.5px;min-width:74px;flex-shrink:0}
aside{display:flex;flex-direction:column;gap:16px;position:sticky;top:20px}
.blokje{background:var(--wit);border:1px solid var(--lijn);border-radius:9px;padding:20px}
.blokje h3{font:600 16px/1.3 var(--serif);margin:0 0 8px}
.blokje p{font-size:14px;color:var(--zacht);margin:0 0 12px}
.link{font:600 13.5px/1 var(--sans);color:var(--accent);text-decoration:none}
.keuzes{list-style:none;margin:0;padding:0;font-size:14px;color:var(--zacht)}
.keuzes li{display:flex;align-items:center;gap:9px;padding:7px 0}
.keuzes strong{color:var(--inkt);font-weight:600}
.bol{width:13px;height:13px;border-radius:50%;border:2px solid var(--lijn);
flex-shrink:0;background:#fff}
.bol.aan{border-color:var(--accent);background:var(--accent);box-shadow:inset 0 0 0 2.5px #fff}
.essay{border-top:2px solid var(--inkt);padding-top:20px;margin-bottom:44px}
.essay-label{font:600 11px/1.4 var(--sans);color:var(--accent);
text-transform:uppercase;letter-spacing:.08em}
.essay h1,.essay h2{font:600 30px/1.22 var(--serif);margin:10px 0 8px;
letter-spacing:-.01em;text-wrap:balance}
.essay h2 a{color:inherit;text-decoration:none}
.essay-kern{font-size:17px;color:var(--zacht);margin:0 0 6px}
.essay-auteur{font:600 13px/1.4 var(--sans);color:var(--gedempt);margin:0 0 22px}
.essay-body p{font:400 17px/1.7 var(--serif);color:#33302b;margin:0 0 16px;max-width:64ch}
.essay-body h3{font:600 19px/1.35 var(--serif);margin:28px 0 10px}
.artikel{padding:40px 0 56px}
.artikel h1{font:600 30px/1.28 var(--serif);margin:10px 0 14px;letter-spacing:-.01em}
.kruimels{font-size:13px;color:var(--gedempt);margin-bottom:6px}
.kruimels a{color:var(--gedempt);text-decoration:none}
.gegevens{border-collapse:collapse;margin:18px 0 8px;font-size:14.5px;width:100%}
.gegevens td{padding:9px 0;border-bottom:1px solid var(--lijn);color:var(--zacht);vertical-align:top}
.gegevens .lab{width:190px;color:var(--gedempt);padding-right:16px}
.artikel h2{font:600 20px/1.3 var(--serif);margin:30px 0 8px}
.methode{border-top:1px solid var(--lijn);margin-top:34px;padding-top:20px;
font-size:13px;line-height:1.65;color:var(--gedempt)}
.strip{display:flex;align-items:center;gap:26px;flex-wrap:wrap;margin-top:34px;
background:var(--wit);border:1px solid var(--lijn);border-radius:10px;padding:22px 24px}
.strip-tekst{flex:1;min-width:230px}
.strip-tekst strong{font:600 17px/1.3 var(--serif)}
.strip-tekst p{font-size:14px;color:var(--zacht);margin:5px 0 0}
.strip .aanmelden{margin:0;max-width:340px;flex:1;min-width:250px}
.strip .aanmelden input,.strip .aanmelden button{padding:11px 14px;font-size:14px}
.verder{margin-top:42px}
.verder .sectiekop h2{font-size:20px}
.verder .dat{min-width:112px;font-size:11.5px;text-transform:uppercase;
letter-spacing:.06em;padding-top:3px}
.voet{border-top:1px solid var(--lijn);background:var(--wit);padding:24px 0}
.voet .binnen{display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;
font-size:13px;color:var(--gedempt)}
.voet a{color:var(--gedempt);text-decoration:none}
@media(max-width:880px){.kolommen{grid-template-columns:1fr;gap:32px}aside{position:static}
.hero h1{font-size:27px}.nav{display:none}.artikel h1{font-size:25px}}
"""


def _pagina(p: Sitepagina, diepte: int) -> str:
    """Zet de inhoud in het paginasjabloon. `diepte` bepaalt de relatieve paden."""
    e = html.escape
    op = "../" * diepte or "./"
    return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(p.titel)}</title>
<meta name="description" content="{e(p.beschrijving)}">
<meta property="og:title" content="{e(p.titel)}">
<meta property="og:description" content="{e(p.beschrijving)}">
<meta property="og:type" content="website">
<link rel="stylesheet" href="{op}stijl.css">
</head>
<body>
<header class="balk"><div class="binnen balk-in">
  <a class="merk" href="{op}">{MERK}</a>
  <nav class="nav">
    <a href="{op}">Vandaag</a>
    <a href="{op}toepassingen/">Toepassingen</a>
    <a href="{op}archief/">Archief</a>
  </nav>
  <a class="knop" href="{op}#aanmelden">Gratis ontvangen</a>
</div></header>
{p.inhoud}
<footer class="voet"><div class="binnen">
  <span><strong style="color:#4a4437">{MERK}</strong> · aibulletin.nl — {e(BESCHRIJVING)}</span>
  <span>
    <a href="{op}werkwijze/">Werkwijze</a> ·
    <a href="{op}colofon/">Colofon</a> ·
    <a href="{op}privacy/">Privacy</a> ·
    <a href="{op}voorkeuren/">Voorkeuren</a> ·
    <a href="{op}archief/">Archief</a>
  </span>
</div></footer>
</body>
</html>"""


# ─────────────────────────── Bouwstenen ──────────────────────────────

def _aanmeldblok() -> str:
    return f"""
<section class="hero"><div class="binnen">
  <h1>{html.escape(BESCHRIJVING)}</h1>
  <p class="hero-sub">Geen cursus, geen abonnement: één stap die je vandaag afmaakt,
    met het Nederlandse AI-nieuws eronder. Jij bepaalt of je ons dagelijks, wekelijks
    of alleen bij groot nieuws hoort.</p>
  <form class="aanmelden" id="aanmelden" method="post" action="#">
    <input type="email" name="email" placeholder="jouw@e-mailadres.nl"
           aria-label="E-mailadres" required>
    <button type="submit">Ontvang de nieuwsbrief</button>
  </form>
  <p class="hero-klein">Geen spam. Uitschrijven met één klik. Verzonden vanuit de EU.</p>
</div></section>"""


def _bericht_kaart(editie: Editie, item, diepte: int) -> str:
    e = html.escape
    op = "../" * diepte or "./"
    herkomst = " · ".join(filter(None, [item.bron, kort_datum(item.datum)]))
    return f"""
<article class="bericht">
  <span class="tag {e(item.categorie)}">{e(item.categorie)}</span>
  <h3><a href="{op}{editie.stam}/{item.slug}/">{e(item.kop)}</a></h3>
  <p class="kern">{e(item.kern)}</p>
  <p class="waarom"><span class="wijzer">Wat het betekent</span>{e(item.waarom)}</p>
  <p class="herkomst">Bron: {e(herkomst)} · <a href="{op}{editie.stam}/{item.slug}/">het hele verhaal</a></p>
</article>"""


def _toepassingblok(editie: Editie, als_link: bool, diepte: int) -> str:
    if not editie.toepassing:
        return ""
    e = html.escape
    op = "../" * diepte or "./"
    t = editie.toepassing
    kop = e(t.titel) + (e(f" — {t.tijd}") if t.tijd else "")
    titel = (
        f'<h2><a href="{op}toepassingen/{t.slug}/" style="color:inherit;text-decoration:none">{kop}</a></h2>'
        if als_link
        else f"<h1>{kop}</h1>"
    )
    stappen = "".join(f"<li>{e(s)}</li>" for s in t.stappen)
    niet = (
        f'<p class="niet-doen"><strong>Wat je níét hoeft te doen:</strong> {e(t.niet_doen)}</p>'
        if t.niet_doen
        else ""
    )
    return f"""
<section class="toepassing">
  <div class="toep-label">Vandaag toepassen</div>
  {titel}
  <p class="toep-intro">{e(t.intro)}</p>
  <ol class="stappen">{stappen}</ol>
  {niet}
</section>"""


def _zijkolom(diepte: int) -> str:
    op = "../" * diepte or "./"
    return f"""
<aside>
  <div class="blokje">
    <h3>Hoe vaak wil je ons horen?</h3>
    <p>De meeste mensen zeggen op omdat het er te veel worden. Daarom kies je zelf —
      en verander je dat wanneer je wilt.</p>
    <ul class="keuzes">
      <li><span class="bol aan"></span><strong>Dagelijks</strong> — volledige editie</li>
      <li><span class="bol"></span><strong>Wekelijks</strong> — vrijdag, het belangrijkste</li>
      <li><span class="bol"></span><strong>Groot nieuws</strong> — een paar keer per maand</li>
    </ul>
    <a class="link" href="{op}voorkeuren/">Voorkeuren aanpassen →</a>
  </div>
  <div class="blokje">
    <h3>Hoe wij werken</h3>
    <p>Zes berichten per dag, per feit gecontroleerd tegen minstens twee bronnen.
      Twijfel vermelden we, we verzwijgen het niet. Teksten van anderen nemen we
      niet over.</p>
    <a class="link" href="{op}werkwijze/">Lees onze werkwijze →</a>
  </div>
</aside>"""


# ───────────────────────────── Pagina's ──────────────────────────────

def _homepage(edities: list[Editie]) -> Sitepagina:
    e = html.escape
    laatste = edities[0]
    berichten = "".join(_bericht_kaart(laatste, i, 0) for i in laatste.items)

    kaartjes = ""
    for ed in edities[:8]:
        if not ed.toepassing:
            continue
        t = ed.toepassing
        kaartjes += f"""
      <a class="kaartje" href="./toepassingen/{t.slug}/">
        <span class="kaart-tijd">{e(t.tijd or "")}</span>
        <h4>{e(t.titel)}</h4>
        <span class="kaart-tag">{e(t.categorie or kort_datum(ed.stam))}</span>
      </a>"""

    archief = "".join(
        f'<li><a href="./{ed.stam}/"><span class="dat">{e(kort_datum(ed.stam))}</span>'
        f"{e(ed.items[0].kop if ed.items else ed.stam)}</a></li>"
        for ed in edities[:6]
    )

    inhoud = f"""
{_aanmeldblok()}
<div class="binnen kolommen">
  <main>
    {_beschouwingblok(laatste, als_link=True, diepte=0)}
    {_toepassingblok(laatste, als_link=True, diepte=0)}
    <section>
      <div class="sectiekop">
        <h2>{e(datum_nl(laatste.datum).capitalize())}</h2>
        <span class="tijd">{len(laatste.items)} berichten</span>
      </div>
      {f'<p class="ene-zin">{e(laatste.intro)}</p>' if laatste.intro else ""}
      {berichten}
    </section>
    <section>
      <div class="sectiekop"><h2>Eerdere toepassingen</h2>
        <a class="meer" href="./toepassingen/">alle →</a></div>
      <div class="rooster">{kaartjes or "<p class='kern'>Nog geen eerdere toepassingen.</p>"}</div>
    </section>
    <section style="margin-top:40px">
      <div class="sectiekop"><h2>Archief</h2><a class="meer" href="./archief/">alles →</a></div>
      <ul class="lijst">{archief}</ul>
    </section>
  </main>
  {_zijkolom(0)}
</div>"""
    return Sitepagina("", f"{MERK} — dagelijks AI-nieuws voor Nederland", BESCHRIJVING, inhoud)


def _editiepagina(editie: Editie) -> Sitepagina:
    e = html.escape
    berichten = "".join(_bericht_kaart(editie, i, 1) for i in editie.items)
    bedrijven = (
        f"""<section class="blokje" style="margin-bottom:34px">
        <h3>Voor jouw bedrijf</h3><p>{e(editie.voor_bedrijven)}</p></section>"""
        if editie.voor_bedrijven
        else ""
    )
    inhoud = f"""
<div class="binnen kolommen">
  <main>
    <p class="kruimels"><a href="../">{MERK}</a> · <a href="../archief/">Archief</a></p>
    <div class="sectiekop">
      <h2>{e(datum_nl(editie.datum).capitalize())}</h2>
      <span class="tijd">{len(editie.items)} berichten</span>
    </div>
    {f'<p class="ene-zin">{e(editie.intro)}</p>' if editie.intro else ""}
    {_beschouwingblok(editie, als_link=True, diepte=1)}
    {_toepassingblok(editie, als_link=True, diepte=1)}
    {berichten}
    {bedrijven}
  </main>
  {_zijkolom(1)}
</div>"""
    titel = f"{datum_nl(editie.datum).capitalize()} — {MERK}"
    return Sitepagina(editie.stam, titel, editie.intro or BESCHRIJVING, inhoud)


def _strip(diepte: int) -> str:
    """Compacte aanmeldbalk voor pagina's zonder hero.

    Een gedeelde link of een klik uit de mail landt op een losse pagina. Zonder
    dit blok is dat een doodlopende weg: de lezer heeft het beste wat we maken
    net gelezen en kan zich nergens aanmelden.
    """
    op = "../" * diepte or "./"
    return f"""
<section class="strip">
  <div class="strip-tekst">
    <strong>Elke werkdag in je inbox</strong>
    <p>Zes berichten over AI die er in Nederland toe doen, in vier minuten.
      Jij bepaalt of dat dagelijks, wekelijks of alleen bij groot nieuws is.</p>
  </div>
  <form class="aanmelden" method="post" action="{op}#aanmelden">
    <input type="email" name="email" placeholder="jouw@e-mailadres.nl"
           aria-label="E-mailadres" required>
    <button type="submit">Aanmelden</button>
  </form>
</section>"""


def _verder_in_editie(editie: Editie, huidig) -> str:
    """De andere berichten van dezelfde dag, onderaan een berichtpagina."""
    e = html.escape
    andere = [i for i in editie.items if i.slug != huidig.slug]
    if not andere:
        return ""
    regels = "".join(
        f'<li><a href="../{i.slug}/"><span class="dat">{e(i.categorie)}</span>'
        f"{e(i.kop)}</a></li>"
        for i in andere
    )
    return f"""
<section class="verder">
  <div class="sectiekop"><h2>Verder in deze editie</h2>
    <a class="meer" href="../">Hele editie →</a></div>
  <ul class="lijst">{regels}</ul>
</section>"""


def _beschouwingblok(editie: Editie, als_link: bool, diepte: int) -> str:
    """Het zondagsstuk. Andere typografie dan de zes berichten, want dit is
    geen nieuws maar een mening — en dat mag de lezer meteen zien."""
    if not editie.beschouwing:
        return ""
    e = html.escape
    op = "../" * diepte or "./"
    b = editie.beschouwing
    titel = (
        f'<h2><a href="{op}{editie.stam}/{b.slug}/">{e(b.titel)}</a></h2>'
        if als_link else f"<h1>{e(b.titel)}</h1>"
    )
    body = "".join(
        f"<h3>{e(a[2:])}</h3>" if a.startswith("# ") else f"<p>{e(a)}</p>"
        for a in b.alineas
    )
    herkomst = (
        f'<p class="herkomst">Gebaseerd op: '
        f'<a href="{e(b.url)}" rel="noopener">{e(b.bron)}</a></p>'
        if b.bron and b.url else ""
    )
    return f"""
<section class="essay">
  <div class="essay-label">Zondagsstuk</div>
  {titel}
  <p class="essay-kern">{e(b.kern)}</p>
  <p class="essay-auteur">{e(b.auteur)}</p>
  <div class="essay-body">{body}</div>
  {herkomst}
</section>"""


def _beschouwingpagina(editie: Editie) -> Sitepagina:
    b = editie.beschouwing
    inhoud = f"""
<div class="binnen smal artikel">
  <p class="kruimels"><a href="../../">{MERK}</a> ·
    <a href="../">{html.escape(datum_nl(editie.datum))}</a></p>
  {_beschouwingblok(editie, als_link=False, diepte=2)}
  <div class="methode">
    Dit stuk is geschreven door {html.escape(b.auteur)} en is een mening, geen
    nieuwsbericht. De zes dagelijkse berichten volgen andere regels — zie onze
    <a href="../../werkwijze/">werkwijze</a>.
  </div>
  {_strip(2)}
</div>"""
    return Sitepagina(f"{editie.stam}/{b.slug}", f"{b.titel} — {MERK}", b.kern, inhoud)


def _berichtpagina(editie: Editie, item) -> Sitepagina:
    e = html.escape
    herkomst = " · ".join(filter(None, [item.bron, kort_datum(item.datum)]))
    kanttekening = (
        f'<p class="kanttekening"><strong>Kanttekening:</strong> {e(item.kanttekening)}</p>'
        if item.kanttekening
        else ""
    )
    inhoud = f"""
<div class="binnen smal artikel">
  <p class="kruimels"><a href="../../">{MERK}</a> ·
    <a href="../">{e(datum_nl(editie.datum))}</a></p>
  <span class="tag {e(item.categorie)}">{e(item.categorie)}</span>
  <h1>{e(item.kop)}</h1>
  <p class="kern">{e(item.kern)}</p>
  <p class="volledig">{e(item.wat)}</p>
  <p class="waarom"><span class="wijzer">Wat het betekent</span>{e(item.waarom)}</p>
  {kanttekening}
  <p class="herkomst">Bron: {e(herkomst)} —
    <a href="{e(item.url)}" rel="noopener nofollow">naar de oorspronkelijke publicatie</a></p>
  <div class="methode">
    Dit bericht is geschreven op basis van de genoemde bron. Wij nemen geen teksten
    van anderen over; feiten worden gecontroleerd tegen minstens twee bronnen.
    Fout gezien? <a href="../../werkwijze/">Laat het ons weten</a>.
  </div>
  {_strip(2)}
  {_verder_in_editie(editie, item)}
</div>"""
    return Sitepagina(f"{editie.stam}/{item.slug}", f"{item.kop} — {MERK}", item.kern, inhoud)


def _toepassingpagina(editie: Editie) -> Sitepagina:
    t = editie.toepassing
    e = html.escape
    inhoud = f"""
<div class="binnen smal artikel">
  <p class="kruimels"><a href="../../">{MERK}</a> ·
    <a href="../">Toepassingen</a> · {e(datum_nl(editie.datum))}</p>
  {_toepassingblok(editie, als_link=False, diepte=2)}
  <div class="methode">
    Uit de editie van <a href="../../{editie.stam}/">{e(datum_nl(editie.datum))}</a>.
    Elke werkdag komt er één toepassing bij.
  </div>
  {_strip(2)}
</div>"""
    return Sitepagina(f"toepassingen/{t.slug}", f"{t.titel} — {MERK}", t.intro, inhoud)


def _bibliotheek(edities: list[Editie]) -> Sitepagina:
    e = html.escape
    kaartjes = "".join(
        f"""
      <a class="kaartje" href="./{ed.toepassing.slug}/">
        <span class="kaart-tijd">{e(ed.toepassing.tijd or "")}</span>
        <h4>{e(ed.toepassing.titel)}</h4>
        <span class="kaart-tag">{e(ed.toepassing.categorie or kort_datum(ed.stam))}</span>
      </a>"""
        for ed in edities
        if ed.toepassing
    )
    inhoud = f"""
<div class="binnen" style="padding-top:40px;padding-bottom:56px">
  <div class="sectiekop"><h2>Toepassingen</h2></div>
  <p class="kern" style="max-width:640px;margin-bottom:22px">
    Elke werkdag één ding dat je met AI kunt doen, uitgelegd in stappen die je
    dezelfde dag afmaakt. Geen theorie, geen abonnementen die je eerst moet afsluiten.</p>
  <div class="rooster">{kaartjes or "<p class='kern'>Nog geen toepassingen.</p>"}</div>
</div>"""
    return Sitepagina(
        "toepassingen",
        f"Toepassingen — {MERK}",
        "Elke werkdag één ding dat je met AI kunt doen, uitgelegd in stappen.",
        inhoud,
    )


def _archief(edities: list[Editie]) -> Sitepagina:
    e = html.escape
    regels = "".join(
        f'<li><a href="../{ed.stam}/"><span class="dat">{e(kort_datum(ed.stam))}</span>'
        f"{e(ed.items[0].kop if ed.items else ed.stam)}</a></li>"
        for ed in edities
    )
    inhoud = f"""
<div class="binnen smal" style="padding-top:40px;padding-bottom:56px">
  <div class="sectiekop"><h2>Archief</h2></div>
  <p class="kern">Alle edities, nieuwste eerst.</p>
  <ul class="lijst">{regels}</ul>
</div>"""
    return Sitepagina("archief", f"Archief — {MERK}", "Alle edities van AI Bulletin.", inhoud)


# ───────────────────── Uitgeversidentiteit ───────────────────────────
#
# Een nieuwssite die op betrouwbaarheid concurreert en anoniem is, is een
# tegenspraak. Los daarvan verplicht art. 3:15d BW een commerciële site tot
# naam, adres, e-mail en KvK-nummer, en verplicht de AVG tot een
# privacyverklaring die de verwerkingsverantwoordelijke noemt.
#
# Beide pagina's worden uit config gegenereerd, zodat er nergens een tweede
# versie van deze gegevens rondslingert die kan verouderen.

VERPLICHTE_UITGEVERSVELDEN = ("naam", "adres", "postcode", "plaats", "kvk", "email")


def controleer_publicatiegereed(config: dict) -> list[str]:
    """Geeft de blokkades die publicatie in de weg staan; leeg = klaar.

    Bedoeld om vóór het deployen aangeroepen te worden, niet tijdens het
    bouwen: lokaal een site kunnen bouwen zonder KvK-nummer moet gewoon
    kunnen, hem live zetten niet.
    """
    uitgever = config.get("uitgever") or {}
    ontbreekt = [v for v in VERPLICHTE_UITGEVERSVELDEN if not str(uitgever.get(v, "")).strip()]
    blokkades = []
    if ontbreekt:
        blokkades.append(
            "uitgeversgegevens ontbreken in config.yaml: " + ", ".join(ontbreekt)
            + " — wettelijk verplicht (art. 3:15d BW) en nodig voor het colofon"
        )
    if not str(uitgever.get("correcties", "") or uitgever.get("email", "")).strip():
        blokkades.append(
            "geen correctie-adres: elke editie belooft correcties, dus er moet "
            "een adres zijn waar die belofte terechtkomt"
        )
    return blokkades


def _uitgever_regels(config: dict) -> list[tuple[str, str]]:
    """De uitgeversgegevens als label/waarde-paren, ontbrekende velden gemarkeerd."""
    u = config.get("uitgever") or {}
    ontbreekt = "— nog niet ingevuld —"

    def veld(sleutel: str, verplicht: bool = True) -> str:
        waarde = str(u.get(sleutel, "") or "").strip()
        if waarde:
            return waarde
        return ontbreekt if verplicht else ""

    # Postcode en plaats staan op één regel. Ontbreken ze allebei, dan hoort er
    # één keer "nog niet ingevuld" te staan en niet twee keer achter elkaar.
    postcode_plaats = " ".join(
        w for w in (str(u.get("postcode", "") or "").strip(),
                    str(u.get("plaats", "") or "").strip()) if w
    ) or ontbreekt

    regels = [
        ("Uitgever", veld("naam")),
        ("Handelsnaam", veld("handelsnaam", verplicht=False)),
        ("Adres", veld("adres")),
        ("Postcode en plaats", postcode_plaats),
        ("Land", veld("land", verplicht=False)),
        # Het label mag niet vastliggen op "KvK-nummer". De uitgever is een
        # Estse OÜ met een registrikood, en dat nummer onder een Nederlands
        # label zetten is een onwaarheid — uitgerekend op de pagina die je
        # identiteit moet bewijzen. Welk register het is, staat in config.yaml.
        (f"Registratienummer ({veld('register', verplicht=False) or 'handelsregister'})",
         veld("kvk")),
        ("Btw-nummer", veld("btw", verplicht=False)),
        ("E-mail", veld("email")),
        ("Correcties", str(u.get("correcties") or u.get("email") or "").strip() or ontbreekt),
        ("Telefoon", veld("telefoon", verplicht=False)),
    ]
    return [(label, waarde) for label, waarde in regels if waarde]


def _colofon(config: dict) -> Sitepagina:
    e = html.escape
    rijen = "".join(
        f'<tr><td class="lab">{e(label)}</td><td>{e(waarde)}</td></tr>'
        for label, waarde in _uitgever_regels(config)
    )
    waarschuwing = (
        '<p class="kanttekening"><strong>Let op:</strong> deze pagina is nog niet '
        "compleet. De site hoort niet live te staan zolang hier gegevens ontbreken.</p>"
        if controleer_publicatiegereed(config)
        else ""
    )
    inhoud = f"""
<div class="binnen smal artikel">
  <h1>Colofon</h1>
  <p class="kern">Wie {MERK} maakt, en waar je ons kunt bereiken.</p>
  {waarschuwing}
  <table class="gegevens">{rijen}</table>

  <h2>Verantwoordelijkheid</h2>
  <p class="volledig">De selectie en de teksten in {MERK} komen tot stand met behulp
    van een taalmodel, onder vaste redactieregels en onder verantwoordelijkheid van
    de hierboven genoemde uitgever. Wij nemen geen teksten van anderen over: elk
    bericht is een eigen tekst over feiten uit de vermelde bron, met een verwijzing
    naar die bron.</p>

  <h2>Correcties</h2>
  <p class="volledig">Een fout is geen ramp, hem laten staan wel. Correcties komen
    bovenaan de eerstvolgende editie en worden in het archief bij het oorspronkelijke
    bericht gezet, met de datum van de correctie erbij. Wij verwijderen geen
    berichten stilletjes.</p>
</div>"""
    return Sitepagina("colofon", f"Colofon — {MERK}",
                      f"Wie {MERK} maakt, en waar je ons kunt bereiken.", inhoud)


def _privacy(config: dict) -> Sitepagina:
    e = html.escape
    u = config.get("uitgever") or {}
    naam = str(u.get("naam") or "").strip() or "— nog niet ingevuld —"
    contact = str(u.get("email") or "").strip() or "— nog niet ingevuld —"
    inhoud = f"""
<div class="binnen smal artikel">
  <h1>Privacyverklaring</h1>
  <p class="kern">Wat we van je bijhouden als je je op {MERK} abonneert, en wat niet.</p>

  <h2>Wie is verantwoordelijk</h2>
  <p class="volledig">{e(naam)} is verwerkingsverantwoordelijke in de zin van de
    AVG. Contact: {e(contact)}. De volledige gegevens staan in het
    <a href="../colofon/">colofon</a>.</p>

  <h2>Welke gegevens en waarom</h2>
  <p class="volledig">Als je je aanmeldt bewaren we je e-mailadres, het moment van
    aanmelden en je bevestiging daarvan, en de frequentie die je hebt gekozen. Dat
    laatste hebben we nodig om je niet vaker te mailen dan je wilt. De grondslag is
    je toestemming, die je met één klik weer kunt intrekken.</p>
  <p class="volledig">Onze verzendpartner registreert of een e-mail is aangekomen en
    geopend. Dat gebruiken we om te zien of een editie de deur uit is gegaan en welke
    onderwerpen gelezen worden — niet om profielen op te bouwen.</p>

  <h2>Waar het staat</h2>
  <p class="volledig">De verzending loopt via een verwerker binnen de Europese Unie,
    met een verwerkersovereenkomst. Je gegevens worden niet verkocht en niet gedeeld
    met adverteerders.</p>

  <h2>Hoe lang</h2>
  <p class="volledig">Tot je je uitschrijft. Daarna bewaren we alleen wat nodig is om
    te kunnen aantonen dat je ooit toestemming hebt gegeven, en niet langer dan
    daarvoor nodig is.</p>

  <h2>Je rechten</h2>
  <p class="volledig">Je kunt inzage vragen, gegevens laten corrigeren of laten
    wissen, en bezwaar maken. Eén bericht naar {e(contact)} volstaat. Kom je er met
    ons niet uit, dan kun je klagen bij de Autoriteit Persoonsgegevens.</p>

  <h2>Cookies</h2>
  <p class="volledig">Deze website plaatst geen tracking-cookies en laadt geen
    scripts van derden. Er is daarom geen cookiemelding — niet omdat we hem
    verstoppen, maar omdat er niets te melden valt.</p>
</div>"""
    return Sitepagina("privacy", f"Privacyverklaring — {MERK}",
                      f"Wat {MERK} van je bijhoudt, en wat niet.", inhoud)


def _voorkeuren() -> Sitepagina:
    inhoud = """
<div class="binnen smal artikel">
  <h1>Hoe vaak wil je ons horen?</h1>
  <p class="kern">De belangrijkste reden dat mensen een nieuwsbrief opzeggen is niet de
    inhoud maar de hoeveelheid. Daarom hoef je hier niet te kiezen tussen alles of
    niets.</p>
  <form method="post" action="#" style="margin:26px 0">
    <div class="blokje" style="margin-bottom:12px">
      <label><input type="radio" name="frequentie" value="dagelijks" checked>
        <strong>Dagelijks</strong> — elke werkdag om 7 uur, vier minuten</label>
    </div>
    <div class="blokje" style="margin-bottom:12px">
      <label><input type="radio" name="frequentie" value="wekelijks">
        <strong>Wekelijks</strong> — vrijdag, alleen wat er echt toe deed</label>
    </div>
    <div class="blokje" style="margin-bottom:20px">
      <label><input type="radio" name="frequentie" value="groot">
        <strong>Alleen groot nieuws</strong> — een paar keer per maand</label>
    </div>
    <div class="blokje" style="margin-bottom:20px">
      <label><input type="checkbox" name="bedrijven" checked>
        Toon het blok <strong>Voor jouw bedrijf</strong></label>
    </div>
    <button class="knop" type="submit" style="border:0;cursor:pointer">Opslaan</button>
  </form>
  <div class="methode">
    Liever helemaal weg? Dat kan met één klik onderaan elke mail. We houden je niet
    tegen met een enquête.
  </div>
</div>"""
    return Sitepagina("voorkeuren", f"Voorkeuren — {MERK}",
                      "Kies zelf hoe vaak je AI Bulletin ontvangt.", inhoud)


def _werkwijze() -> Sitepagina:
    inhoud = """
<div class="binnen smal artikel">
  <h1>Hoe wij werken</h1>
  <p class="volledig">Elke werkdag scannen we arXiv, GitHub, Hugging Face, Hacker News,
    de blogs van de grote labs en de Nederlandse vakmedia. Daaruit kiezen we zes
    berichten en schrijven ze zelf op.</p>
  <h2 style="font:600 19px/1.3 var(--serif);margin:26px 0 8px">Feit en mening staan apart</h2>
  <p class="volledig">Wat er gebeurd is, staat in het bericht. Wat wij ervan vinden,
    staat onder “waarom het ertoe doet”. Die scheiding is expres, zodat je kunt zien
    waar de controleerbare bewering ophoudt.</p>
  <h2 style="font:600 19px/1.3 var(--serif);margin:26px 0 8px">Twijfel benoemen we</h2>
  <p class="volledig">Een cijfer van een leverancier dat niemand heeft nagerekend, een
    onderzoek met oud veldwerk, een voorlopige tussenstand — dat staat erbij als
    kanttekening. Dat verzwakt het bericht niet; het is de reden dat je de rest kunt
    geloven.</p>
  <h2 style="font:600 19px/1.3 var(--serif);margin:26px 0 8px">Wij nemen niets over</h2>
  <p class="volledig">We citeren hooguit één zin, met bron en auteur, en verwijzen
    verder door. Waar het kan gebruiken we de primaire bron: het persbericht van de
    toezichthouder gaat voor het nieuwsbericht daarover.</p>
  <h2 style="font:600 19px/1.3 var(--serif);margin:26px 0 8px">Er zit een taalmodel in</h2>
  <p class="volledig">Selectie en tekst komen tot stand met behulp van een taalmodel,
    onder vaste redactieregels. We zeggen dat liever gewoon dan dat je het moet raden.</p>
  <h2 style="font:600 19px/1.3 var(--serif);margin:26px 0 8px">Correcties</h2>
  <p class="volledig">Fouten corrigeren we bovenaan de eerstvolgende editie en bij het
    oorspronkelijke bericht in het archief. Mail ons als je iets ziet.</p>
</div>"""
    return Sitepagina("werkwijze", f"Werkwijze — {MERK}",
                      "Hoe AI Bulletin tot stand komt: bronnen, controle en correcties.", inhoud)


# ─────────────────────────────── Bouwen ──────────────────────────────

def laad_edities(map_: Path, vandaag: date | None = None) -> list[Editie]:
    """Leest alle editie-JSON's, nieuwste eerst. Kapotte bestanden overslaan.

    Edities met een datum in de toekomst blijven liggen. Ze horen in de map —
    het zondagsstuk wordt vooruit geschreven — maar niet op de site: de
    homepage toont de nieuwste editie, en zonder deze regel stond een stuk van
    aanstaande zondag op donderdag al op de voorpagina. Voor een nieuwssite is
    dat geen schoonheidsfout maar een onwaarheid over wat er vandaag speelt.
    """
    vandaag = vandaag or date.today()
    edities = []
    for pad in sorted(map_.glob("*.json"), reverse=True):
        try:
            editie = Editie.from_dict(json.loads(pad.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            log.warning("editie overgeslagen (%s): %s", pad.name, exc)
            continue
        if editie.datum > vandaag:
            log.info("editie %s is van later (%s) — nog niet op de site",
                     pad.name, editie.datum.isoformat())
            continue
        edities.append(editie)
    return edities


class OngekeurdeEditie(ValueError):
    """Een editie in de uitvoermap die niet gepubliceerd hoort te worden."""


def bouw(edities_map: Path, uitvoer: Path, config: dict | None = None,
         leeg_eerst: bool = True, indexeerbaar: bool = True,
         keuren: bool = True, vandaag: date | None = None) -> list[Path]:
    """Bouwt de volledige site. Retourneert de geschreven paden.

    `config` levert de uitgeversgegevens voor colofon en privacyverklaring.
    Ontbreekt hij, dan komen die pagina's er wel maar met lege velden en een
    zichtbare waarschuwing — bouwen mag altijd, publiceren niet.
    """
    config = config or {}
    edities = laad_edities(edities_map, vandaag)
    if not edities:
        raise ValueError(
            f"geen publiceerbare edities in {edities_map} — staan ze allemaal "
            "in de toekomst?")

    # Dit is de route die de lezer werkelijk bereikt. Blokkeren in
    # render_selectie() helpt niet als het JSON-bestand daarna nog met de hand
    # wordt bijgewerkt — en dat is precies wat er in deze repo is gebeurd.
    if keuren:
        kapot = {
            ed.stam: keuring.blokkades(keuring.keur(ed, streng=True))
            for ed in edities
        }
        kapot = {stam: b for stam, b in kapot.items() if b}
        if kapot:
            regels = "\n".join(
                f"  {stam}: " + "; ".join(str(x) for x in b)
                for stam, b in sorted(kapot.items()))
            raise OngekeurdeEditie(
                f"{len(kapot)} editie(s) in {edities_map} zijn niet "
                f"publicatiegereed:\n{regels}")

    if leeg_eerst and uitvoer.exists():
        shutil.rmtree(uitvoer)
    uitvoer.mkdir(parents=True, exist_ok=True)

    paginas: list[Sitepagina] = [
        _homepage(edities),
        _bibliotheek(edities),
        _archief(edities),
        _voorkeuren(),
        _werkwijze(),
        _colofon(config),
        _privacy(config),
    ]
    for ed in edities:
        paginas.append(_editiepagina(ed))
        paginas += [_berichtpagina(ed, item) for item in ed.items]
        if ed.toepassing:
            paginas.append(_toepassingpagina(ed))
        if ed.beschouwing:
            paginas.append(_beschouwingpagina(ed))

    geschreven = [uitvoer / "stijl.css"]
    (uitvoer / "stijl.css").write_text(_stylesheet().strip() + "\n", encoding="utf-8")

    for p in paginas:
        doel = uitvoer / p.pad / "index.html" if p.pad else uitvoer / "index.html"
        doel.parent.mkdir(parents=True, exist_ok=True)
        doel.write_text(_pagina(p, diepte=len(Path(p.pad).parts)), encoding="utf-8")
        geschreven.append(doel)

    geschreven.append(_robots(uitvoer, indexeerbaar))
    geschreven.append(_sitemap(paginas, uitvoer))
    log.info("site gebouwd: %d pagina's in %s", len(paginas), uitvoer)
    return geschreven


def _robots(uitvoer: Path, indexeerbaar: bool) -> Path:
    """robots.txt — en op een voorvertoning een verbod op indexeren.

    Een preview-URL die wél geïndexeerd wordt, concurreert met de echte site
    om dezelfde teksten. Dat is precies het soort dubbele inhoud waar je later
    niet meer vanaf komt.
    """
    from .render import SITE

    pad = uitvoer / "robots.txt"
    if indexeerbaar:
        pad.write_text(
            "User-agent: *\nAllow: /\n\n"
            f"Sitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    else:
        pad.write_text(
            "# Voorvertoning — niet de echte site.\n"
            "User-agent: *\nDisallow: /\n", encoding="utf-8")
    return pad


def _sitemap(paginas: list[Sitepagina], uitvoer: Path) -> Path:
    from .render import SITE

    regels = "".join(
        f"  <url><loc>{SITE}/{p.pad + '/' if p.pad else ''}</loc></url>\n" for p in paginas
    )
    pad = uitvoer / "sitemap.xml"
    pad.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{regels}</urlset>\n",
        encoding="utf-8",
    )
    return pad
