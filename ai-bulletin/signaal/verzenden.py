"""De editie per e-mail versturen.

Dit is de derde route naar de lezer, naast `render_selectie()` en
`site.bouw()`, en de enige die niet terug te draaien is. Een fout op de website
herstel je met een commit; een fout in een verzonden mail staat in andermans
inbox. Daarom is dit de strengste poort van de drie: hij weigert bij elke
blokkade uit `keuring.keur()`, en bovendien bij dingen die alleen voor e-mail
gelden — een niet-ingevulde uitschrijflink, een ontbrekende afzender.

Bewust geen ESP-koppeling. Zolang er één ontvanger is (beslissing 12:
kees@telemedia.es) is SMTP genoeg en is een abonnement overhead. Vanaf de
tweede lezer komt Laposta erbij; dan gaat het lijstbeheer daarheen en blijft
deze module bestaan voor de proefmail.
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage

from . import keuring, render, site
from .model import Editie

log = logging.getLogger(__name__)

# De sjabloonhaakjes die een ESP normaal invult. Staan ze er nog in op het
# moment van verzenden, dan leest de ontvanger letterlijk "{{unsubscribe}}".
SAMENVOEGVELDEN = ("{{unsubscribe}}",)


class VerzendFout(RuntimeError):
    """Er is niets verstuurd, en dat is met opzet."""


@dataclass
class Verzending:
    """Wat er is verstuurd — of zou zijn verstuurd bij een proefdraai."""

    ontvangers: list[str]
    onderwerp: str
    berichten: list[EmailMessage] = field(default_factory=list)
    verstuurd: bool = False


def ontvangers(config: dict) -> list[str]:
    """Wie de editie krijgt.

    `altijd_naar` staat los van een eventuele abonneelijst: die adressen
    krijgen de editie hoe dan ook. Dat is beslissing 12 en een test bewaakt
    dat het niet wegvalt.
    """
    verzend_cfg = config.get("verzending") or {}
    vast = [str(x).strip() for x in (verzend_cfg.get("altijd_naar") or []) if str(x).strip()]
    # Volgorde behouden en dubbelen eruit; dezelfde mail twee keer sturen is
    # geen ramp maar wel slordig.
    gezien, uniek = set(), []
    for adres in vast:
        if adres.lower() not in gezien:
            gezien.add(adres.lower())
            uniek.append(adres)
    return uniek


def afzender(config: dict) -> str:
    """Het From-adres. Env wint van config, zodat een geheim geen bestand raakt."""
    uit_env = os.environ.get("SMTP_AFZENDER", "").strip()
    if uit_env:
        return uit_env
    uitgever = config.get("uitgever") or {}
    naam = str(uitgever.get("handelsnaam") or uitgever.get("naam") or "").strip()
    adres = str(uitgever.get("email") or "").strip()
    if not adres:
        return ""
    return f"{naam} <{adres}>" if naam else adres


def bouw_bericht(
    editie: Editie,
    config: dict,
    ontvanger: str,
    *,
    uitschrijflink: str,
) -> EmailMessage:
    """Eén mail voor één ontvanger, als tekst én HTML.

    De tekstversie is geen bijzaak: sommige mailprogramma's tonen hem, en een
    lezer die HTML uitzet hoort dezelfde editie te krijgen en geen lege mail.
    """
    bericht = EmailMessage()
    bericht["Subject"] = editie.onderwerp
    bericht["From"] = afzender(config)
    bericht["To"] = ontvanger
    # Zonder deze kop belandt een nieuwsbrief eerder in de spamfilter, en een
    # lezer hoort zich te kunnen uitschrijven zonder eerst te hoeven zoeken.
    bericht["List-Unsubscribe"] = f"<{uitschrijflink}>"

    bericht.set_content(render.naar_markdown(editie))
    bericht.add_alternative(
        render.naar_html(editie).replace("{{unsubscribe}}", uitschrijflink),
        subtype="html",
    )
    return bericht


def _controleer(editie: Editie, config: dict, adressen: list[str], uitschrijflink: str) -> None:
    """Alles wat verzenden tegenhoudt, op één plek en vóór de eerste byte."""
    if not adressen:
        raise VerzendFout(
            "geen ontvangers — vul verzending.altijd_naar in config.yaml")

    blokkades = keuring.blokkades(keuring.keur(editie, streng=True))
    if blokkades:
        raise VerzendFout(
            "editie is niet verzendgereed:\n  "
            + "\n  ".join(str(x) for x in blokkades))

    if not afzender(config):
        raise VerzendFout(
            "geen afzender — zet SMTP_AFZENDER of vul uitgever.email in config.yaml")

    # Zodra er iemand anders dan de uitgever meeleest, gelden de identiteits-
    # verplichtingen ook voor de mail. Bij één ontvanger — de uitgever zelf —
    # is dat een formaliteit die niets beschermt. Deze controle staat vóór de
    # uitschrijflink: wie je bent weegt zwaarder dan waar de knop heen wijst,
    # en anders krijg je een foutmelding over een link terwijl het werkelijke
    # bezwaar iets anders is.
    vaste = {a.lower() for a in ontvangers(config)}
    if any(a.lower() not in vaste for a in adressen):
        ontbreekt = site.controleer_publicatiegereed(config)
        if ontbreekt:
            raise VerzendFout(
                "verzenden naar anderen dan de vaste ontvangers mag niet zolang "
                "de uitgeversgegevens ontbreken:\n  " + "\n  ".join(ontbreekt))

    if not uitschrijflink or any(veld in uitschrijflink for veld in SAMENVOEGVELDEN):
        raise VerzendFout(
            "geen uitschrijflink — de mail bevat een uitschrijfknop en die mag "
            "niet naar een sjabloonhaakje wijzen")


def verstuur(
    editie: Editie,
    config: dict,
    *,
    naar: list[str] | None = None,
    uitschrijflink: str | None = None,
    proef: bool = False,
    smtp=None,
) -> Verzending:
    """Verstuur de editie, of weiger met opgaaf van reden.

    `proef=True` doet alles behalve het versturen zelf: dezelfde controles,
    dezelfde berichten, geen verbinding. Zo is de verzendweg te testen zonder
    dat er iets de deur uit gaat.

    `smtp` is een reeds geopende verbinding — bedoeld voor tests; laat hem in
    productie leeg, dan wordt er een verbinding opgezet uit de omgeving.
    """
    adressen = naar if naar is not None else ontvangers(config)
    link = uitschrijflink or os.environ.get("UITSCHRIJFLINK", "").strip()
    if not link and adressen and set(a.lower() for a in adressen) == {
            a.lower() for a in ontvangers(config)}:
        # De uitgever zelf kan zich niet uitschrijven van zijn eigen bulletin;
        # de knop wijst dan naar de voorkeurenpagina in plaats van nergens heen.
        link = f"{render.SITE}/voorkeuren"

    _controleer(editie, config, adressen, link)

    verzending = Verzending(ontvangers=adressen, onderwerp=editie.onderwerp)
    verzending.berichten = [
        bouw_bericht(editie, config, adres, uitschrijflink=link) for adres in adressen
    ]

    if proef:
        log.info("proefdraai: %d bericht(en) opgebouwd, niets verstuurd", len(adressen))
        return verzending

    eigen_verbinding = smtp is None
    if eigen_verbinding:
        smtp = _verbind()
    try:
        for bericht in verzending.berichten:
            smtp.send_message(bericht)
            log.info("verstuurd naar %s", bericht["To"])
    finally:
        if eigen_verbinding:
            smtp.quit()

    verzending.verstuurd = True
    return verzending


def _verbind():
    """SMTP-verbinding uit de omgeving. Geen enkel geheim staat in config.yaml."""
    host = os.environ.get("SMTP_HOST", "").strip()
    gebruiker = os.environ.get("SMTP_GEBRUIKER", "").strip()
    wachtwoord = os.environ.get("SMTP_WACHTWOORD", "")
    poort = int(os.environ.get("SMTP_POORT", "587"))
    if not host:
        raise VerzendFout("SMTP_HOST ontbreekt — zonder mailserver valt er niets te sturen")

    if poort == 465:
        verbinding = smtplib.SMTP_SSL(host, poort, context=ssl.create_default_context())
    else:
        verbinding = smtplib.SMTP(host, poort)
        verbinding.starttls(context=ssl.create_default_context())
    if gebruiker:
        verbinding.login(gebruiker, wachtwoord)
    return verbinding
