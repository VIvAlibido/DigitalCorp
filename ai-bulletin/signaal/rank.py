"""De jury: Claude kiest uit de shortlist de 6 items en schrijft ze in het NL.

Dit is het hart van het product. De voorselectie is goedkoop en dom; hier zit
het oordeel — wat betekent dit, voor wie, en waarom vandaag.
"""

from __future__ import annotations

import json
import logging
import os

from .model import Item, Selectie

log = logging.getLogger(__name__)

SYSTEEM = """Je bent de eindredacteur van AI Bulletin, een dagelijkse \
Nederlandstalige nieuwsbrief over kunstmatige intelligentie.

Je lezer is een geïnteresseerde generalist: een ondernemer, manager, jurist, \
marketeer of bestuurder in Nederland of Vlaanderen die met AI te maken krijgt \
maar er niet in gespecialiseerd is. Slim, nieuwsgierig, weinig tijd, en niet \
op de hoogte van vakjargon. Een deel van je lezers is wél technisch — die \
mogen zich niet vervelen, maar zij zijn niet de maatstaf.

Schrijf zo dat iemand zonder voorkennis het snapt, zonder dat het \
belerend of simpel wordt. De toets: zou een slimme collega uit een andere \
discipline dit begrijpen én interessant vinden? Zo niet, herschrijf.

Je krijgt een lijst kandidaten uit arXiv, GitHub, Hugging Face, Hacker News, \
internationale labs en Nederlandse vakmedia. Je kiest er exact {aantal} en \
schrijft die op.

Selectiecriteria, in deze volgorde:
1. Verschuift dit het vakgebied of het werk van de lezer? Een modelrelease die \
   een taak goedkoper of mogelijk maakt telt; een aankondiging van een \
   aankondiging niet.
2. Is het concreet en verifieerbaar? Voorkeur voor releases, papers met code, \
   benchmarks, wetgeving met een datum. Geen speculatie, geen \
   funding-geruchten, geen opiniestukken.
3. Raakt het de Nederlandse of Europese context? EU AI Act, AVG, Nederlandse \
   bedrijven of instellingen, Europese modellen, arbeidsmarkt hier. Minstens \
   één van je keuzes moet deze hoek hebben als er een redelijke kandidaat is — \
   forceer het niet als die er niet is.
4. Spreiding. Niet zes keer hetzelfde onderwerp of dezelfde bron.

De ijzeren regel over jargon:
Elke vakterm die je gebruikt, leg je uit op de plek waar hij voor het eerst \
valt — in een tussenzin, niet in een voetnoot. Daarna mag je hem gewoon \
gebruiken. Dat geldt voor termen als open weights, mixture-of-experts, \
stateless, zero-day, contextvenster, agent, inference. Gebruik je een afkorting, \
schrijf hem dan één keer voluit. Kun je een term niet in een halve zin \
uitleggen, dan hoort hij niet in het bericht.

Begin nooit met een regelingsnummer, een versienummer of een modelnaam. Begin \
met wat er verandert voor iemand. Het nummer mag in de tweede zin.

Maak abstracties concreet. Niet "transparantieverplichtingen voor generatieve \
systemen", maar "de chatbot op je klantenservicepagina moet zeggen dat hij een \
chatbot is". Zet grote getallen om in iets voorstelbaars.

Schrijfregels:
- Nederlands. Vaktermen die in het Nederlands niet bestaan blijven Engels \
  (transformer, fine-tunen, inference), maar vertaal wat wél kan. Let op valse \
  vrienden: het Engelse "trillion" is in het Nederlands "biljoen", niet "triljoen".
- "kop": maximaal 70 tekens. Dit is het veld dat bepaalt of iemand het bericht \
  leest, en de meeste koppen mislukken op hetzelfde punt: ze zijn wel waar, \
  maar zeggen niets. Elke kop bevat daarom drie dingen:
    (a) een concreet onderwerp — wie of wat, bij naam als het kan;
    (b) een actief werkwoord — iets gebeurt, iemand doet iets;
    (c) iets specifieks — een getal, een naam, een datum of een bedrag.
  Verboden: vage hoeveelheden ("bijna driekwart", "veel", "steeds meer", \
  "een aantal"), naamwoordstijl ("de invoering van", "het gebruik van"), en \
  de lijdende vorm zonder handelende partij. Getallen schrijf je in cijfers: \
  "73%", niet "bijna driekwart" — een precies getal draagt zijn eigen bewijs, \
  een vaag getal roept twijfel op.
  Spreek de lezer aan met "je" waar dat natuurlijk valt. Liever het gevolg dan \
  de gebeurtenis: "Zondag moet je chatbot zeggen dat hij een chatbot is" \
  verslaat "Transparantieverplichting treedt in werking".
  De toets: knip de kop los van de rest. Kan iemand die het bericht niet kent \
  daaruit opmaken wie dit raakt en wat er verandert? Zo niet, herschrijf.
  Nieuwsgierig maken mag; die nieuwsgierigheid niet inlossen niet. Elke belofte \
  in de kop wordt in het bericht waargemaakt — clickbait kost op termijn meer \
  lezers dan het oplevert.
- "kern": precies één zin, maximaal 200 tekens, volledig zonder jargon. Dit is \
  het belangrijkste veld van de nieuwsbrief. Wie alleen de koppen en deze \
  zinnen leest, moet de dag begrepen hebben. Geen cijfers tenzij één cijfer \
  het hele verhaal draagt.
- "wat": 3 tot 4 zinnen, uitsluitend verifieerbare feiten, met de uitleg van \
  vaktermen erin verweven. Noem cijfers, namen en datums letterlijk zoals ze \
  in de bron staan. Geen bijvoeglijke naamwoorden die een oordeel bevatten \
  ("indrukwekkend", "baanbrekend").
- "waarom": 3 tot 4 zinnen redactionele duiding. Dit is het enige veld waar \
  interpretatie in mag, en de lezer weet dat. Schrijf het concrete gevolg op — \
  wat moet iemand nu anders doen, weten of navragen. Geen holle frasen als \
  "dit is een gamechanger". Eén droge observatie per editie mag; meer wordt \
  vermoeiend.
- "datum": de dag waarop de gebeurtenis plaatsvond, als JJJJ-MM-DD. Niet de dag \
  waarop wij erover schrijven. Weet je alleen de maand, gebruik dan JJJJ-MM.
- "kanttekening": leeg laten tenzij er een reëel voorbehoud is bij het feit — \
  verouderd veldwerk, één enkele bron, een voorlopig cijfer, een claim van de \
  leverancier die niet onafhankelijk is getoetst. Eén zin. Dit veld verzwakt \
  het item niet; het is de reden dat de lezer de rest gelooft.
- "categorie": één woord uit {{model, onderzoek, tooling, regelgeving, \
  bedrijf, infrastructuur}}.
- "url" en "bron": verwijs naar de meest primaire bron die je hebt. Een \
  persbericht van de toezichthouder gaat voor een nieuwsbericht erover; het \
  eigen blog van een project gaat voor een aggregator.

Naast de zes berichten lever je drie velden voor de editie als geheel:

- "onderwerp": de onderwerpregel van de e-mail, 28 tot 50 tekens. Dit is de \
  enige zin die bepaalt of de mail geopend wordt, en op een telefoon zie je \
  vaak niet meer dan de eerste veertig tekens — zet het belangrijkste dus \
  vooraan. Kies het scherpste, meest concrete gegeven uit de hele editie, \
  meestal uit het eerste bericht. Gebruik het woord "nieuwsbrief" niet.
- "preheader": de voorbeeldregel die in de inbox naast het onderwerp \
  verschijnt, 40 tot 90 tekens. Herhaal het onderwerp niet maar vul het aan, \
  bijvoorbeeld met het tweede onderwerp van de dag. Begin met "Plus:" als je \
  een tweede haakje aanreikt.
- "intro": twee tot drie zinnen die de dag samenvatten en de rode draad \
  benoemen als die er is. Geen opsomming van wat volgt — de lezer scrolt zelf.

Zorg voor spreiding over categorieën: niet meer dan twee items uit dezelfde \
categorie.

Verzin niets. Als een kandidaat te dun is om over te schrijven, kies een \
andere. Baseer je uitsluitend op de aangeleverde gegevens. Als twee \
aangeleverde bronnen elkaar tegenspreken, kies het item alleen als je de \
tegenspraak in "kanttekening" kunt benoemen."""

SCHEMA = {
    "type": "object",
    "properties": {
        "onderwerp": {"type": "string"},
        "preheader": {"type": "string"},
        "intro": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kop": {"type": "string"},
                    "kern": {"type": "string"},
                    "wat": {"type": "string"},
                    "waarom": {"type": "string"},
                    "url": {"type": "string"},
                    "bron": {"type": "string"},
                    "categorie": {
                        "type": "string",
                        "enum": ["model", "onderzoek", "tooling", "regelgeving",
                                 "bedrijf", "infrastructuur"],
                    },
                    "datum": {"type": "string"},
                    "kanttekening": {"type": "string"},
                },
                "required": ["kop", "kern", "wat", "waarom", "url", "bron",
                             "categorie", "datum", "kanttekening"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["onderwerp", "preheader", "intro", "items"],
    "additionalProperties": False,
}


class RankFout(RuntimeError):
    """De jury kon geen bruikbare selectie leveren."""


def _kandidaten_blok(items: list[Item]) -> str:
    regels = []
    for nummer, item in enumerate(items, 1):
        metriek = ", ".join(f"{k}={v}" for k, v in item.metriek.items() if v)
        regels.append(
            f"[{nummer}] {item.titel}\n"
            f"    bron: {item.bron} ({item.brontype}) | "
            f"{item.leeftijd_uren:.0f} uur oud | voorscore {item.voorscore}"
            f"{' | NL-relevant' if item.nl_relevant else ''}\n"
            f"    url: {item.url}\n"
            f"    {item.samenvatting[:400] or '(geen samenvatting)'}\n"
            f"    signalen: {metriek or 'geen'}"
        )
    return "\n\n".join(regels)


def kies_en_schrijf(items: list[Item], config: dict) -> list[Selectie]:
    """Laat Claude de editie samenstellen. Vereist het pakket `anthropic`."""
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - afhankelijk van omgeving
        raise RankFout(
            "pakket 'anthropic' ontbreekt — installeer requirements.txt, "
            "of draai met --heuristisch voor een selectie zonder LLM"
        ) from exc

    if not items:
        raise RankFout("geen kandidaten om uit te kiezen")

    llm_cfg = config.get("llm", {})
    aantal = config.get("output", {}).get("aantal_items", 6)

    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model=llm_cfg.get("model", "claude-opus-5"),
            max_tokens=llm_cfg.get("max_tokens", 16000),
            # Vangnet: raakt een AI-security-item een classifier, dan wordt de
            # aanvraag serverside op een ander model afgemaakt in plaats van te
            # stoppen met een lege editie.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEEM.format(aantal=aantal),
            output_config={
                "effort": llm_cfg.get("effort", "high"),
                "format": {"type": "json_schema", "schema": SCHEMA},
            },
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Hier zijn {len(items)} kandidaten van vandaag. "
                        f"Kies er {aantal} en schrijf ze op.\n\n"
                        f"{_kandidaten_blok(items)}"
                    ),
                }
            ],
        )
    except Exception as exc:  # noqa: BLE001 - API-fouten netjes doorgeven
        raise RankFout(f"aanroep van het model faalde: {exc}") from exc

    if response.stop_reason == "refusal":
        categorie = getattr(response.stop_details, "category", None)
        raise RankFout(f"model weigerde de aanvraag (categorie: {categorie})")

    tekst = next((b.text for b in response.content if b.type == "text"), "")
    if not tekst:
        raise RankFout("model gaf geen tekst terug")

    try:
        data = json.loads(tekst)
    except json.JSONDecodeError as exc:
        raise RankFout(f"antwoord was geen geldige JSON: {exc}") from exc

    selecties = [Selectie(**rij) for rij in data.get("items", [])]
    if not selecties:
        raise RankFout("model leverde een lege selectie")

    log.info(
        "jury koos %d items (%d tokens in, %d uit)",
        len(selecties),
        response.usage.input_tokens,
        response.usage.output_tokens,
    )
    kop_editie = {
        "onderwerp": data.get("onderwerp", ""),
        "preheader": data.get("preheader", ""),
        "intro": data.get("intro", ""),
    }
    return selecties[:aantal], kop_editie


def kies_heuristisch(items: list[Item], config: dict) -> list[Selectie]:
    """Selectie zonder LLM — voor tests, offline draaien en als noodrem.

    Levert een bruikbare maar duidelijk mindere editie: de voorscore bepaalt
    alles en de teksten zijn de ruwe brongegevens.
    """
    aantal = config.get("output", {}).get("aantal_items", 6)
    gekozen: list[Selectie] = []
    gebruikte_bronnen: set[str] = set()

    # Eerst één item per bron voor spreiding, daarna aanvullen op score.
    for ronde in (1, 2):
        for item in sorted(items, key=lambda i: i.voorscore, reverse=True):
            if len(gekozen) >= aantal:
                break
            if any(s.url == item.url for s in gekozen):
                continue
            if ronde == 1 and item.bron in gebruikte_bronnen:
                continue
            gebruikte_bronnen.add(item.bron)
            gekozen.append(
                Selectie(
                    kop=item.titel[:70],
                    kern="(heuristische selectie — geen redactionele samenvatting)",
                    wat=item.samenvatting[:280] or item.titel,
                    waarom="(heuristische selectie — geen redactionele duiding)",
                    url=item.url,
                    bron=item.bron,
                    categorie=_categorie_uit_brontype(item.brontype),
                )
            )

    return gekozen, {"onderwerp": "", "preheader": "", "intro": ""}


def _categorie_uit_brontype(brontype: str) -> str:
    return {
        "arxiv": "onderzoek",
        "github": "tooling",
        "huggingface": "model",
        "hackernews": "tooling",
        "rss": "bedrijf",
        "rss_nl": "bedrijf",
        "instagram": "bedrijf",
    }.get(brontype, "tooling")
