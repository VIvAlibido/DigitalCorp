# AI Bulletin

Verzamelt elke werkdag AI-nieuws uit acht bronsoorten, ontdubbelt, en laat
Claude de **6 items kiezen die er werkelijk toe doen** — geschreven in het
Nederlands, met expliciete duiding voor de Nederlandse markt.

Gebouwd als Nederlandstalige tegenhanger van AlphaSignal, met twee verschillen
die bewust zijn gekozen: Nederlandse bronnen en Nederlandse duiding wegen mee in
de selectie, en er is een audio-editie.

## Snel draaien

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

python -m signaal.cli                 # volledige run met LLM-jury
python -m signaal.cli --audio         # inclusief gesproken editie
python -m signaal.cli --site          # bouw de website uit alle edities
```

Zonder API-sleutel of internet, met meegeleverde voorbeelddata:

```bash
python -m signaal.cli --fixtures fixtures/kandidaten.json --heuristisch
python -m unittest discover -s tests
```

Output belandt in `edities/` als JSON (archief/API), Markdown (web) en
HTML (e-mail, met inline styles zodat Outlook het niet sloopt).
`--site` leest die JSON-bestanden en schrijft de complete statische site naar
`site/`. De site is dus volledig af te leiden uit `edities/` en staat daarom
niet in de repo — alleen het archief zelf.

## Wat er in één editie zit

Zes berichten, en twee dingen die het nieuws niet zelf oplevert:

- **Elk bericht** heeft een kop, een `kern` (één zin zonder jargon die het hele
  bericht draagt), `wat` (het verifieerbare feit), `waarom` (de duiding, apart
  gelabeld zodat de lezer ziet waar het feit ophoudt), bron, datum van de
  gebeurtenis, en waar nodig een `kanttekening` bij het cijfer zelf.
- **Vandaag toepassen** — drie stappen die de lezer vandaag kan doen, met
  expliciet erbij wat níét hoeft. Dit is het enige onderdeel dat niet uit een
  bron komt en dus niet te scrapen is door een concurrent.
- **Voor jouw bedrijf** — wat de dag betekent voor wie iets moet beslissen.

De mail is korter dan de site: hij bevat kop, kern en waarom, en linkt per
bericht door naar `aibulletin.nl/{datum}/{slug}` voor het volledige feitenrelaas.
Dat houdt de belofte van een paar minuten haalbaar en geeft de site
bestaansrecht.

## Hoe het werkt

```
bronnen → leeftijdsfilter → voorscore → ontdubbelen → shortlist → jury → render → site
 ~200      ~150              ~150        ~120          40          6      3 formaten  HTML
```

**1. Bronnen** (`signaal/bronnen/`) — arXiv, GitHub (sterren-per-dag, niet totaal:
een repo van drie jaar met 40k sterren is geen nieuws), Hugging Face trending,
Hacker News via Algolia, RSS van labs en vendors, en **RSS van Nederlandse
vakmedia** (Tweakers, Emerce, AG Connect, Computable, Autoriteit
Persoonsgegevens). Elke bron mag falen zonder de run te breken.

**2. Voorscore** (`signaal/score.py`) — recency met exponentieel verval,
log-geschaalde engagement, gewicht per brontype, en een bonus voor items die
raken aan de Nederlandse of Europese context. Dit is bewust dom: het bepaalt
alleen wie de jury te zien krijgt, niet wat er geplaatst wordt.

**3. Ontdubbelen** (`signaal/dedupe.py`) — één modelrelease staat tegelijk op
Hacker News, de vendor-blog en Tweakers. Dat is één feit. Clustering gaat op
gecanonicaliseerde URL, tekengelijkenis én woordoverlap met tolerantie voor
Nederlandse verbuigingen (`contextvenster` = `contextvensters`). Dat een verhaal
door meerdere bronnen wordt opgepikt is zelf een signaal en levert score op.

**4. Shortlist** — top 40, met een gereserveerd quotum voor NL-relevante items.
Zonder dat quotum verdrinken Nederlandse berichten in de internationale volumes,
en dan is er geen reden meer om deze nieuwsbrief boven AlphaSignal te verkiezen.

**5. Jury** (`signaal/rank.py`) — Claude Opus 5 met adaptief denken, `effort:
high` en structured outputs. Het model kiest 6 items en schrijft per item: wat
er is gebeurd (2 zinnen, met cijfers) en waarom het ertoe doet voor een
Nederlandse professional. De systeemprompt verbiedt expliciet holle frasen en
speculatie. Faalt de jury, dan valt de pijplijn terug op een heuristische
selectie — een mindere editie is beter dan geen editie.

**6. Website** (`signaal/site.py`) — leest alle edities uit `edities/` en
genereert een statische site: homepage, editiepagina, een eigen pagina per
bericht (waar de mail naartoe linkt), een doorzoekbare bibliotheek van alle
"Vandaag toepassen"-stukken, archief, voorkeuren, werkwijze en een sitemap.
Geen build-tooling, geen JavaScript, één stylesheet — te hosten op elke statische
host en snel genoeg op een telefoon met slecht bereik.

**7. Audio** (`signaal/audio.py`) — het voorleesscript is níét de mailtekst.
URL's worden verwijderd, afkortingen fonetisch gespeld (`LLM` → `el-el-em`,
`AVG` → `aa-vee-gee`), haakjes worden komma's. ElevenLabs `eleven_multilingual_v2`
is geïmplementeerd; het Engelstalige model spreekt Nederlands met een Engels
accent uit en is onbruikbaar. Azure Neural (`nl-NL-FennaNeural`,
`nl-NL-MaartenNeural`) is het voor de hand liggende alternatief, maar is nog
niet geïmplementeerd — `genereer()` weigert nu netjes met een uitleg.

## Koppen: het driestapsplan

Een script kan geen hoge conversie garanderen. Onderzoek naar kop-analysetools
is daarover eensluidend: de correlatie tussen hun scores en werkelijke
prestaties is zwak, omdat ze structuur meten en niet of de kop de juiste lezer
op het juiste moment raakt. Voor een publiek dat honderden vergelijkbare koppen
heeft gezien, zijn de "bewezen patronen" die zulke tools belonen juist de
patronen die genegeerd worden.

Wat wél kan, in aflopende volgorde van betrouwbaarheid:

### Stap 1 — Afkeuren wat aantoonbaar slecht is (`koptoets.py`)

Blokkeert vage hoeveelheden, naamwoordstijl, lijdende vorm zonder handelende
partij, uitroeptekens, overlengte, en koppen zonder enig concreet houvast.
Hoog vertrouwen, want dit gaat over de afwezigheid van gebreken en niet over de
aanwezigheid van magie. Draait automatisch in de pijplijn en in de tests.

```bash
python -m signaal.koppen --editie redactie/2026-07-29-selectie.json
```

### Stap 2 — Kiezen uit varianten (`kopvarianten.py`, `kopscore.py`)

Eén kop schrijven is een gok; acht koppen schrijven en de beste kiezen is een
selectie. De score is een zwakke absolute voorspeller maar een bruikbare
*vergelijker*: bij varianten van hetzelfde bericht blijven onderwerp, bron en
belang gelijk en verschilt alleen de formulering. Zes dimensies, waarvan
specificiteit het zwaarst weegt omdat daarvoor het bewijs het sterkst is.

De bestaande kop doet mee als kandidaat — is die al de sterkste, dan verandert
er niets. De runner-up wordt bewaard als B-variant.

```bash
python -m signaal.koppen --editie redactie/... --varianten --schrijf
```

### Stap 3 — Meten (`abtest.py`)

Het enige dat conversie echt vaststelt. En meteen het ongemakkelijke deel:

```bash
python -m signaal.koppen --steekproef 800 --baseline 0.35
```

Bij 800 ontvangers en 35% opens kun je alleen een verschil van 10 procentpunt
aantonen. Voor 2 procentpunt heb je ruim 18.000 ontvangers nodig. **Onder de
paar duizend abonnees is A/B-toetsen op onderwerpregels geen meting maar een
muntworp met extra stappen** — laat stap 1 en 2 dan het werk doen en toets
alleen grote, structurele keuzes.

De rekenwijze is tweezijdig met 95% betrouwbaarheid en 80% onderscheidend
vermogen. Online rekenmachines geven vaak lagere aantallen omdat ze eenzijdig
toetsen of een andere variantieschatting gebruiken; dit is bewust de
conservatieve variant.

### Wat dit plan niet doet

Er zit geen lijst met "power words" in. Die scoren goed in tools die op
contentmarketing zijn geijkt en vallen bij een technisch of zakelijk publiek
juist door de mand. Er is ook geen absoluut oordeel: `kopscore` geeft geen
"83 van de 100, dus goed", omdat dat cijfer alleen betekenis heeft ten opzichte
van een alternatief.

## Instagram-accounts volgen

Kort antwoord: **niet via een officiële API, voor willekeurige accounts.**

Meta's Instagram Graph API geeft alleen toegang tot je eigen Business- of
Creator-account. Er is één uitzondering, en die is geïmplementeerd:

| Route | Wat het kan | Beperking |
|---|---|---|
| **`business_discovery`** ✅ geïmplementeerd | Publieke profielvelden en recente media van een ánder account | Alleen zakelijke accounts; vereist je eigen IG Business-account + token; geen Stories, geen persoonlijke accounts |
| oEmbed | Eén specifieke, bekende post embedden | Geen feed, geen ontdekking |
| Commerciële scrapers (Apify, Bright Data, Phyllo) | Werkt in de praktijk voor elk publiek account | Kost geld, schuurt met Instagram's voorwaarden, risico ligt bij jou |
| Zelf scrapen | — | Afgeraden: schendt de voorwaarden, breekt continu, leidt tot IP- en accountblokkades |

`business_discovery` aanzetten:

```yaml
instagram:
  actief: true
  provider: graph_business_discovery
  accounts: [openai, anthropic, huggingface]
```

```bash
export IG_USER_ID=...        # jouw eigen Instagram Business-account-ID
export IG_ACCESS_TOKEN=...   # long-lived token met instagram_basic
```

De adapter voor een betaalde provider staat als `NotImplementedError` klaar in
`signaal/bronnen/instagram.py` — bewust niet ingevuld, want elke provider heeft
een eigen schema en een eigen contract dat je zelf moet accepteren.

**Mijn advies: sla Instagram over.** Voor technisch AI-nieuws is het het zwakste
kanaal — de inhoud is doorgaans een doorplaatsing van iets dat al op X, GitHub of
een blog stond, en je betaalt met geld of met ToS-risico voor data die je
elders gratis en officieel krijgt.

## Wat er nog niet in zit

Eerlijk over de grenzen van wat hier staat:

- **Verzenden.** De HTML is klaar met `{{unsubscribe}}`-placeholders, maar er is
  geen koppeling met een ESP. Voor de Nederlandse markt zijn Laposta of Flexmail
  (EU-hosting, AVG-verwerkersovereenkomst standaard) praktischer dan Mailchimp.
- **Abonneebeheer.** Dubbele opt-in en bewaartermijnen zijn AVG-verplichtingen,
  geen features — regel dat in de ESP, niet hier.
- **Podcast-RSS.** De MP3 wordt geschreven, maar er is nog geen feed omheen.
- **Kwaliteitsmeting.** Er is geen loop die meet of de gekozen zes achteraf de
  juiste zes waren. Dat is op termijn het belangrijkste dat ontbreekt: zonder
  meting kun je de prompt niet gericht verbeteren.
- **Livetest.** De pijplijn is end-to-end getest met fixtures; de netwerkbronnen
  en de LLM-aanroep zijn nooit live gedraaid, omdat de omgeving waarin dit is
  gebouwd geen uitgaand internet heeft. Reken op kleine correcties bij de eerste
  echte run — vermoedelijk in de RSS-feed-URL's, die verhuizen nogal eens.

## Kosten

Ruwe schatting per editie: circa 25.000 input-tokens (40 kandidaten) en 2.000
output-tokens op Claude Opus 5, plus denk-tokens. Dat is in de orde van enkele
tientallen dollarcenten per dag — verwaarloosbaar naast de tijd die het scheelt.
Wordt het volume groter, dan is `effort: medium` de eerste knop om aan te
draaien, niet een goedkoper model.

## Automatisch draaien

`.github/workflows/ai-bulletin.yml` draait elke dag om 05:15 UTC: tests, editie
samenstellen, site proefbouwen, controleren of publiceren mag, en het archief
terugcommitten. Vereist `ANTHROPIC_API_KEY` als repository secret;
`ELEVENLABS_API_KEY` en `ELEVENLABS_VOICE_ID` alleen als je audio aanzet.

**Publiceren doet Vercel, niet deze workflow.** Vercel is aan de repo gekoppeld
en bouwt bij elke push opnieuw via `vercel.json`; de commit met de nieuwe editie
ís de publicatie. Zet in Vercel de root directory op `ai-bulletin` — de repo-root
bevat een andere website. Er staat bewust geen GitHub Pages-deploy meer in de
workflow: twee routes leveren twee versies van de site op twee adressen.
