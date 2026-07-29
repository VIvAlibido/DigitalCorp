"""De jury: Claude kiest uit de shortlist de 6 items en schrijft ze in het NL.

Dit is het hart van het product. De voorselectie is goedkoop en dom; hier zit
het oordeel — wat betekent dit, voor wie, en waarom vandaag.
"""

from __future__ import annotations

import copy
import json
import logging
import os
from datetime import date

from .model import Editie, Item, Selectie, Toepassing

log = logging.getLogger(__name__)

# Standaardgrenzen aan de omvang van een editie. Zie bouw_schema().
# MIN_ITEMS stond op 3 en dwong daarmee opvulling af: op een dag met één
# werkelijk bericht verbood de eigen keuring om dat ene bericht te sturen.
# Eén bericht dat iets verandert verslaat vier die dat niet doen.
MIN_ITEMS = 1
MAX_ITEMS = 6
# Bovengrens voor het duidingsveld. Zie toets_verhouding().
MAX_WOORDEN_WAAROM = 60

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
internationale labs en Nederlandse vakmedia. Je kiest er hoogstens {aantal} en \
schrijft die op.

Hoeveel er precies in de editie komen, bepaal jij:
- Zijn er {aantal} berichten die de lezer echt moet weten, dan neem je er {aantal}.
- Zijn er maar vier of vijf die die toets doorstaan, dan lever je er vier of \
  vijf. Een zwak zesde bericht kost meer lezers dan een korte editie.
- Is er vandaag één ding dat de lezer werkelijk moet weten, lever dan dat ene \
  ding. Een korte editie die ergens over gaat, verslaat een volle editie die \
  nergens over gaat. Vermeld het in "intro" en verzin geen verantwoording die \
  je niet kunt onderbouwen.
Dit is geen ontsnappingsroute voor moeilijk werk. Het is bedoeld voor dagen \
waarop er domweg weinig is gebeurd — weekends, feestdagen, komkommertijd. \
Vul een editie nooit op met een bericht dat je zelf zou overslaan.

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

Vier technieken die een bericht van braaf naar goed tillen. Gebruik ze waar ze \
passen, niet alle vier in elk bericht:

1. SPANNING BOVEN MEDEDELING. Een kop die twee dingen tegen elkaar in zet, \
   laat zich niet wegscrollen. "Kimi K3 is gratis te downloaden en onbetaalbaar \
   om te draaien" verslaat "Moonshot brengt Kimi K3 uit". Alleen als de \
   tegenstelling echt in het nieuws zit — verzin er geen.
   Voorwaarde: minstens één helft van de tegenstelling moet iets zijn dat de \
   lezer kan zien of aanwijzen. "De AI-wet is uitgesteld en gaat vandaag gewoon \
   in" is spanning tussen twee abstracties en dus geen spanning maar verwarring; \
   "De AI-wet is uitgesteld — behalve voor jouw chatbot" gaat over hetzelfde \
   feit en werkt wel.
2. EEN SCÈNE IN PLAATS VAN EEN DEFINITIE. Moet je een begrip uitleggen, laat \
   het dan zien in een situatie die de lezer kent. Niet "buiten de \
   trainingsverdeling", maar: je rijdt 's nachts door de sneeuw en er ligt iets \
   op de weg; je weet niet wát het is en remt toch. Eén zin is genoeg.
3. EEN CIJFER DAT BLIJFT HANGEN. Zet het getal apart en laat het even staan in \
   plaats van het in een bijzin te verstoppen. Twee getallen naast elkaar die \
   niet bij elkaar passen, doen het werk voor je.
4. DE DUIDING OORDEELT. "Wat het betekent" beschrijft niet wat er gebeurde — \
   dat stond al in "wat". Het zegt wat de lezer er nu mee moet. Een duiding die \
   je zonder verlies kunt schrappen, was geen duiding.

En wat je NIET doet, ook al lees je het bij goede AI-schrijvers:
- Geen ik-vorm en geen eigen stelling. De dagelijkse editie heeft geen \
  ik-persoon; het zondagsessay wel, en dat schrijft een mens.
- Geen uitweidingen, geen reeksen retorische vragen, geen "tja" of "nou ja". \
  Wat in een essay van 900 woorden charmant is, is in 180 woorden vulling.
- Geen gespeelde oneerbiedigheid. Spot alleen als het nieuws zelf spottend is. \
  Nagedane branietaal is binnen twee edities doorzichtig en kost lezers.

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
- "waarom": precies twee zinnen, samen hoogstens 55 woorden. Dit is het enige \
  veld waar interpretatie in mag, en de lezer weet dat. Schrijf het concrete \
  gevolg op — wat moet iemand nu anders doen, weten of navragen. Geen holle \
  frasen als "dit is een gamechanger". Eén droge observatie per editie mag; \
  meer wordt vermoeiend.
  De lengte is een harde eis, geen richtlijn. In de e-mail staat alleen "kern" \
  en "waarom"; wordt "waarom" langer, dan bestaat de nieuwsbrief voor het \
  grootste deel uit onze mening en voor een klein deel uit feiten. Dat is \
  precies omgekeerd aan wat dit product belooft. Krijg je het niet in twee \
  zinnen, dan heb je geen duiding maar een samenvatting geschreven — die hoort \
  in "wat".
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

Naast de berichten lever je nog een aantal velden voor de editie als geheel:

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
- "toepassing": het onderdeel dat deze nieuwsbrief onderscheidt. Eén ding dat \
  de lezer vandaag kan dóén, bij voorkeur volgend uit het belangrijkste bericht.
    * "titel": wat het oplevert, niet wat het is. Max 70 tekens.
    * "tijd": realistische schatting, bijvoorbeeld "15 minuten".
    * "intro": één zin die de drempel wegneemt — wat je níét nodig hebt.
    * "stappen": precies drie. Elke stap begint met een werkwoord en is af te \
      ronden zonder iets aan te schaffen. Geef bij tekststappen de voorbeeldzin \
      letterlijk mee, zodat de lezer hem kan kopiëren.
    * "niet_doen": wat expliciet niet hoeft. Geruststelling voorkomt dat mensen \
      meer doen dan nodig, en is even waardevol als een instructie.
    * "categorie": één woord, bijvoorbeeld juridisch, verkoop, klantenservice, \
      hr, marketing, administratie.
  Verzin geen toepassing die je niet kunt onderbouwen met het nieuws van vandaag \
  of met algemeen bekende werkwijzen. Een verzonnen stappenplan is erger dan geen.
- "voor_bedrijven": één zin voor wie een organisatie runt, volgend uit een van \
  de zes berichten. Concreet en meteen uitvoerbaar. Is er vandaag niets \
  zakelijks relevants, laat het veld dan leeg — een gedwongen zin leest als \
  vulling en kost lezers.

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
        "voor_bedrijven": {"type": "string"},
        "toepassing": {
            "type": "object",
            "properties": {
                "titel": {"type": "string"},
                "intro": {"type": "string"},
                "stappen": {"type": "array", "items": {"type": "string"}},
                "niet_doen": {"type": "string"},
                "tijd": {"type": "string"},
                "categorie": {"type": "string"},
            },
            "required": ["titel", "intro", "stappen", "niet_doen", "tijd", "categorie"],
            "additionalProperties": False,
        },
        "items": {
            "type": "array",
            "minItems": MIN_ITEMS,
            "maxItems": MAX_ITEMS,
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
    "required": ["onderwerp", "preheader", "intro", "voor_bedrijven",
                 "toepassing", "items"],
    "additionalProperties": False,
}


def toets_verhouding(editie) -> list[str]:
    """Waarschuw als de duiding het feitenrelaas overvleugelt.

    De e-mail toont alleen "kern" en "waarom". Loopt "waarom" uit de hand, dan
    leest de abonnee vooral onze mening — terwijl de belofte van dit product
    juist is dat je kunt zien waar het feit ophoudt. Blokkeren doen we niet;
    dit is een redactioneel oordeel, geen fout.
    """
    bezwaren = []
    for nummer, s in enumerate(editie.items, 1):
        duiding, feit = len(s.waarom.split()), len(s.wat.split())
        if duiding > MAX_WOORDEN_WAAROM:
            bezwaren.append(
                f"{nummer}. {s.kop[:45]}: duiding is {duiding} woorden "
                f"(hoogstens {MAX_WOORDEN_WAAROM})")
        elif feit and duiding > feit:
            bezwaren.append(
                f"{nummer}. {s.kop[:45]}: meer duiding ({duiding}) dan feiten ({feit})")
    return bezwaren


def bouw_schema(minimaal: int = MIN_ITEMS, maximaal: int = MAX_ITEMS) -> dict:
    """SCHEMA met de grenzen van deze run erin.

    Het aantal items is geen vast getal maar een bereik: op een rustige dag
    levert de jury er vier, en dat moet het schema toestaan. Zie de
    systeemprompt voor wanneer dat mag.
    """
    schema = copy.deepcopy(SCHEMA)
    schema["properties"]["items"]["minItems"] = minimaal
    schema["properties"]["items"]["maxItems"] = maximaal
    return schema


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


def kies_en_schrijf(items: list[Item], config: dict, datum: date) -> Editie:
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
    uitvoer_cfg = config.get("output", {})
    aantal = uitvoer_cfg.get("aantal_items", MAX_ITEMS)
    minimaal = min(uitvoer_cfg.get("minimaal_items", MIN_ITEMS), aantal)

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
            system=SYSTEEM.format(aantal=aantal, minimaal=minimaal),
            output_config={
                "effort": llm_cfg.get("effort", "high"),
                "format": {"type": "json_schema",
                           "schema": bouw_schema(minimaal, aantal)},
            },
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Hier zijn {len(items)} kandidaten van vandaag. "
                        f"Kies er hoogstens {aantal} (minimaal {minimaal}) "
                        f"en schrijf ze op.\n\n"
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
    toepassing = data.get("toepassing")
    return Editie(
        datum=datum,
        items=selecties[:aantal],
        onderwerp=data.get("onderwerp", ""),
        preheader=data.get("preheader", ""),
        intro=data.get("intro", ""),
        toepassing=Toepassing(**toepassing) if toepassing else None,
        voor_bedrijven=data.get("voor_bedrijven", ""),
    )


def kies_heuristisch(items: list[Item], config: dict, datum: date) -> Editie:
    """Selectie zonder LLM — voor tests, offline draaien en als noodrem.

    Levert een bruikbare maar duidelijk mindere editie: de voorscore bepaalt
    alles en de teksten zijn de ruwe brongegevens.

    Ook hier geldt de ondergrens uit `kies_en_schrijf`, maar dan zonder oordeel.
    Een absolute drempel op de voorscore kan niet: die score is een optelsom van
    recency, engagement en brontypegewicht zonder betekenisvolle schaal, en is
    nooit tegen echte data geijkt. Wat wél schaalvrij werkt is de verhouding tot
    de sterkste kandidaat van die dag — valt een item ver onder de kop van het
    veld, dan is het vulling.

    De beperking daarvan is eerlijk te benoemen: dit vangt "de staart is veel
    zwakker dan de kop", niet "vandaag is alles middelmatig". Dat laatste kan
    alleen de jury zien.
    """
    uitvoer_cfg = config.get("output", {})
    aantal = uitvoer_cfg.get("aantal_items", MAX_ITEMS)
    minimaal = min(uitvoer_cfg.get("minimaal_items", MIN_ITEMS), aantal)
    verhouding = config.get("selectie", {}).get("min_verhouding", 0.35)

    top = max((i.voorscore for i in items), default=0.0)
    ondergrens = top * verhouding if top > 0 else 0.0

    gekozen: list[Selectie] = []
    gebruikte_bronnen: set[str] = set()

    # Eerst één item per bron voor spreiding, daarna aanvullen op score.
    for ronde in (1, 2):
        for item in sorted(items, key=lambda i: i.voorscore, reverse=True):
            if len(gekozen) >= aantal:
                break
            # Onder de ondergrens alleen nog aanvullen tot het minimum gehaald is.
            if item.voorscore < ondergrens and len(gekozen) >= minimaal:
                continue
            if any(s.url == item.url for s in gekozen):
                continue
            if ronde == 1 and item.bron in gebruikte_bronnen:
                continue
            gebruikte_bronnen.add(item.bron)
            gekozen.append(
                Selectie(
                    kop=item.titel[:70],
                    kern="(heuristische selectie — geen redactionele samenvatting)",
                    # Nooit de samenvatting van de uitgever overnemen: die tekst
                    # is auteursrechtelijk beschermd en dit is juist de route die
                    # aanslaat als de jury faalt. Alleen de eigen titel en een
                    # link; de lezer klikt maar door.
                    wat="(automatische selectie zonder redactie — zie de bron)",
                    waarom="(heuristische selectie — geen redactionele duiding)",
                    url=item.url,
                    bron=item.bron,
                    categorie=_categorie_uit_brontype(item.brontype),
                )
            )

    if len(gekozen) < aantal:
        log.info("editie telt %d items in plaats van %d — de rest haalde de "
                 "ondergrens niet", len(gekozen), aantal)
    return Editie(datum=datum, items=gekozen)


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
