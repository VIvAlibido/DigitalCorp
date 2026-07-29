# NL-AI-Signaal

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
```

Zonder API-sleutel of internet, met meegeleverde voorbeelddata:

```bash
python -m signaal.cli --fixtures fixtures/kandidaten.json --heuristisch
python -m unittest discover -s tests
```

Output belandt in `edities/` als JSON (archief/API), Markdown (web) en
HTML (e-mail, met inline styles zodat Outlook het niet sloopt).

## Hoe het werkt

```
bronnen  →  leeftijdsfilter  →  voorscore  →  ontdubbelen  →  shortlist  →  jury  →  render
 ~200        ~150               ~150          ~120            40           6        3 formaten
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

**6. Audio** (`signaal/audio.py`) — het voorleesscript is níét de mailtekst.
URL's worden verwijderd, afkortingen fonetisch gespeld (`LLM` → `el-el-em`,
`AVG` → `aa-vee-gee`), haakjes worden komma's. ElevenLabs `eleven_multilingual_v2`
is geïmplementeerd; het Engelstalige model spreekt Nederlands met een Engels
accent uit en is onbruikbaar. Azure Neural (`nl-NL-FennaNeural`,
`nl-NL-MaartenNeural`) is het voor de hand liggende alternatief, maar is nog
niet geïmplementeerd — `genereer()` weigert nu netjes met een uitleg.

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

`.github/workflows/nl-ai-signaal.yml` draait op werkdagen om 05:15 UTC. Vereist
`ANTHROPIC_API_KEY` als repository secret; `ELEVENLABS_API_KEY` en
`ELEVENLABS_VOICE_ID` alleen als je audio aanzet.
