# AI Bulletin — werkgeheugen

Dit bestand is het geheugen van dit project. Het wordt automatisch geladen aan
het begin van elke sessie. Staat iets hier niet in, dan bestaat het de volgende
keer niet meer.

**Onderhoudsregel:** elke afgeronde beslissing komt hier binnen dezelfde sessie
in te staan. Niet in een samenvatting, niet in een chatbericht — hier.

---

## Wat we bouwen

Een Nederlandstalig AI-nieuwsplatform: elke dag een editie met de belangrijkste
berichten, een website met een archief dat vindbaar is in Google, en later een
podcast.

**Doel:** nummer één worden in het eigen vakgebied op de Nederlandse markt.

**Domein:** aibulletin.nl · **Merknaam:** AI Bulletin

### De lezer

**De geïnteresseerde professional.** Werkt niet in AI maar moet er wel iets mee:
ondernemer, marketeer, HR, jurist, zorgmanager. Snapt zijn eigen vak, niet de
techniek.

Praktische gevolgen: geen jargon zonder uitleg, geen benchmarks, geen
modelvergelijkingen om het vergelijken. Elk bericht beantwoordt impliciet
"raakt dit mijn werk?". De toepassing is werkgerelateerd, nooit een hobbytoepassing.

### Het ene kenmerk

**Toepasbaar — elke dag één ding dat je kunt dóén.**

Gekozen boven "begrijpelijk", "controleerbaar" en "kort". Begrijpelijkheid en
controleerbaarheid blijven volledige eisen aan het werk, maar zijn niet wat we
zéggen.

Waarom dit werkt: het is het enige kenmerk waarbij datgene waar je om bekend
staat ook datgene is dat zoekverkeer oplevert. Mensen zoeken op *"hoe gebruik ik
AI voor offertes"*, niet op *"AI-nieuws 12 maart"*. Positionering en SEO wijzen
dezelfde kant op.

Het risico: het format komt van The Rundown en is in een week te kopiëren. De
verdediging is niet het format maar de stapel — een doorzoekbare bibliotheek van
250 toepassingen na een jaar is niet in te halen. **Daarom is de bibliotheek geen
bijproduct maar het hoofdbezit.**

Wat dit afdwong in de bouw — uitgevoerd op 29 juli:
- De toepassing staat bóven de zes berichten, in de mail, op de homepage en op
  de editiepagina. Tests bewaken die volgorde.
- De homepagebelofte gaat over doen: "Elke dag één ding dat je met AI kunt doen.
  Plus het nieuws dat je moet weten, in vier minuten."
- De bibliotheek staat in de navigatie en met een rooster op de homepage.

---

## Werkafspraken

Vastgelegd op verzoek van de opdrachtgever, na terechte kritiek dat ik elke
opmerking omzette in werk zonder tegen te spreken.

0. **Elke controle sluit aan op álle routes.** De fouten in dit project kwamen
   niet doordat er regels ontbraken, maar doordat de controles alleen op de
   automatische run zaten en niet op `render_selectie()` — de route waarlangs
   handgeschreven edities binnenkomen. Bouw je een nieuwe controle, sluit hem
   dan aan in `keuring.keur()` en nergens anders. Eén poort, beide wegen.
1. **Tegenspreken hoort bij het werk.** Een opdracht die botst met eerder
   onderzoek, met een eerdere beslissing of met het doel, wordt eerst benoemd.
   Daarna pas uitgevoerd of aangepast — maar de tegenspraak komt eerst.
2. **Geen nieuw kenmerk zonder dat er één afvalt.** Het kenmerk is
   *toepasbaar*; zie hierboven. Dit project heeft al één keer vijf
   onderscheidende kenmerken gekregen waar het onderzoek er één voorschreef.
3. **Niets beweren zonder bewijs.** Geen verzonnen cijfers, geen "dat werkt
   goed" zonder bron of test. Bij twijfel: opzoeken of het onbekend noemen.
4. **Afmaken voor doorgaan.** Een half werkend onderdeel is geen voortgang.
5. **De opdrachtgever is niet de vakman.** Ontbrekende expertise aanvullen is
   onderdeel van de opdracht, niet iets om op te wachten.

---

## Beslissingen die vastliggen

Hier niet meer over discussiëren tenzij er nieuwe informatie is.

| # | Beslissing | Waarom |
|---|---|---|
| 1 | Naam **AI Bulletin**, domein aibulletin.nl | gekozen na afwijzen van "Het Kwartje" (leek op satire) |
| 2 | 6 berichten per editie, 7 dagen per week | opdrachtgever, 29 juli |
| 3 | Verzending om **06:00** via ingeplande ESP-campagne, niet via cron | GitHub Actions-cron loopt 15 min tot 2+ uur uit; zie plan/dagelijks-publiceren.md §1 |
| 4 | ESP wordt **Laposta**, maar pas vanaf de tweede lezer | NL, EU-hosting, apart schedule-endpoint (nodig voor #3). Een ESP dient lijstbeheer, opt-in en afleverbaarheid; bij één lezer is dat overhead |
| 13 | Tot de tweede abonnee gaat de editie **via de Gmail-connector** naar kees@telemedia.es | scheelt een dag bouwwerk en een abonnement; de AVG gaat pas spelen zodra iemand anders zich moet kunnen uitschrijven |
| 5 | Eigen tekst, nooit tekst van anderen overnemen | feiten zijn vrij, formulering niet; art. 15/15a Aw |
| 6 | Feit (`wat`) en duiding (`waarom`) blijven zichtbaar gescheiden | geloofwaardigheid is de enige verdediging tegen "zoveelste AI-nieuwsbrief" |
| 14 | `waarom` is **hoogstens twee zinnen / 60 woorden**, bewaakt door `rank.toets_verhouding()` | de mail toont alleen `kern` en `waarom`; bij langere duiding bestaat de nieuwsbrief voor 80% uit onze mening. Gemeten op de editie van 29 juli: 79–84% |
| 15 | Het duidingslabel heet **"Wat het betekent"**, klein en ingesprongen, met één uitleg boven De zes | zes keer een vetgedrukt "Waarom" leest als geschreeuw; de scheiding moet zichtbaar zijn, niet luid |
| 7 | Weekend krijgt een **ander formaat** dan doordeweeks | za/zo is de dunste invoer van de week; zie plan §6 |
| 8 | Zondagstuk wordt **niet geautomatiseerd** en verschijnt onder de naam **Kees Cornelius** | het enige deel dat niet te scrapen is, moet mensenwerk zijn; een mening zonder naam is het slechtste van twee werelden |
| 16 | De dagelijkse editie leent **vier technieken** van essayisten als Alberto Romero: spanning boven mededeling, scène boven definitie, een cijfer dat blijft hangen, duiding die oordeelt | de vorm schaalt niet naar 180 woorden, het gereedschap wel |
| 18 | **Alle redactionele controles staan in `keuring.py`** en draaien op beide routes; handgeschreven edities worden hard geblokkeerd, de automatische run alleen gerapporteerd | de ochtendmail moet de deur uit, een handmatige editie heeft geen deadline en dus geen excuus |
| 17 | De dagelijkse editie gebruikt **géén ik-vorm, geen uitweidingen, geen gespeelde oneerbiedigheid** | 6 berichten × 7 dagen = 42 meningen per week; die heeft niemand. Nagedane branietaal is binnen twee edities doorzichtig |
| 9 | Eerst **goedkeuren vóór verzenden**, later omschakelen naar een annuleervenster | opdrachtgever heeft nu veel tijd, straks weinig; de omschakeling moet één regel config zijn, geen verbouwing |
| 10 | Colofon en privacyverklaring worden **uit `uitgever:` in config.yaml gegenereerd** | één plek voor deze gegevens, zodat er geen tweede versie kan verouderen; publicatie wordt geblokkeerd zolang ze ontbreken |
| 11 | Hosting op **Vercel**, gekoppeld aan deze repo. Root directory `ai-bulletin` | opdrachtgever, 29 juli. Let op: de repo-root bevat een ándere website; zonder die instelling publiceert Vercel die |
| 12 | **Elke editie gaat altijd naar kees@telemedia.es** | opdrachtgever, 29 juli. Vastgelegd in `verzending.altijd_naar`; een test bewaakt dat het niet wegvalt |

## Beslissingen die openstaan — deze blokkeren werk

| # | Vraag | Wat het blokkeert |
|---|---|---|
| **D** | De uitgeversgegevens: statutaire naam, adres, postcode, plaats, KvK-nummer, btw-nummer, e-mail en correctie-adres. Ook: is aibulletin.nl geregistreerd? | **Lancering.** De machinerie staat klaar — `uitgever:` in config.yaml invullen en het is af. `site.controleer_publicatiegereed()` blokkeert de workflow tot dat gebeurd is. Bron nieuwsradio.com was niet bereikbaar vanuit deze omgeving (proxy 403). |
| **E** | Wat betekent "nummer één" in een getal — abonnees, bezoekers, iets anders? | Kunnen beoordelen of een keuze over zes maanden heeft gewerkt |

*(A, B en C zijn beantwoord op 29 juli — zie "De lezer", "Het ene kenmerk" en
beslissing 9.)*

---

## Feiten die vaststaan — niet opnieuw uitzoeken

- **Deze omgeving heeft nauwelijks uitgaand netwerk.** WebSearch werkt; de
  proxy weigert vrijwel alle domeinen met een 403 op de CONNECT-tunnel —
  geverifieerd voor vercel.com, api.vercel.com en nieuwsradio.com. Live bronnen,
  LLM-aanroepen en deploys zijn hier niet uit te voeren. Alles is getest met
  fixtures.
- **Geen credentials in de omgeving.** Geen Vercel-token, geen SMTP, geen ESP.
  Deployen moet de opdrachtgever zelf doen; beloof het niet.
- **Er is géén Vercel-connector**, ook al heeft de opdrachtgever een
  Vercel-account (met o.a. nexradio erop). Gecontroleerd via ListConnectors op
  29 juli: beschikbaar zijn Canva, Gmail, Google Calendar en Google Drive.
  Niet opnieuw gaan zoeken.
- **Gmail is wél gekoppeld** maar stond op 29 juli uit voor de chat. Zodra dat
  aanstaat is dat het verzendkanaal — zie beslissing 13.
- **De LLM-jury heeft nog nooit echt gedraaid.** De editie van 2026-07-29 op de
  site is met de hand geschreven en zegt niets over wat de automaat produceert.
- **Een editie mag korter zijn dan zes** — opgelost op 29 juli. De jury krijgt
  een bereik van 3 tot 6; de heuristische terugval gebruikt een verhouding tot
  de sterkste kandidaat van die dag. Die verhouding vangt een zwakke staart,
  niet een middelmatige dag: dat laatste kan alleen de jury zien, en die heeft
  nog nooit gedraaid.
- **De pijplijn heeft geheugen tussen edities** — `historie.py`, opgelost op
  29 juli. Zelfde bron-URL wordt geweerd, een sterk gelijkende kop gestraft.
- **Nieuwssamenvattingen ranken niet.** Google zet de primaire bron boven een
  samenvatting daarvan. Het archief is geen SEO-bezit; de toepassingen en de
  naslagpagina's zijn dat wel. Zie "SEO" hieronder.
- **AI Bulletin valt zelf onder art. 50 AI-verordening** vanaf 2 augustus 2026:
  de teksten zijn door een taalmodel geschreven en dat moet kenbaar zijn. De
  methodeverantwoording doet dat al.

---

## Stand van de bouw

**Werkt en is getest** (119 tests): verzamelen uit 8 brontypes, scoren,
ontdubbelen, geheugen tussen edities, ondergrens, shortlist, LLM-jury met terugval, koptoets/kopscore/kopvarianten,
zondagsstuk met eigen sjabloon en auteursnaam,
render naar JSON/Markdown/mail-HTML, statische sitegenerator inclusief
colofon en privacyverklaring, robots.txt met noindex op voorvertoningen,
GitHub Actions-workflow met Pages-deploy, en `vercel.json` + `bouw_site.py`
voor Vercel — met een publicatieblokkade zolang de uitgeversgegevens ontbreken.

**Ontbreekt:** verzendlaag (ESP), abonneebeheer, weekendformaten,
SEO-technisch fundament (zie hieronder), en de uitgeversgegevens zelf —
zie openstaand punt D.

**Agenten:** `.claude/agents/` — eindredacteur en feitenchecker vóór elke
verzending, zondagslezer vóór elke zondag, tegenspreker bij elk plan van de
assistent. Volgorde die geldt: **code → agent → mens**. Vangt een agent iets dat
in een regel te vatten is, verplaats het dan naar `keuring.py`.

**Plannen:** `plan/nieuwsbrief-plan.md` (strategie, marktonderzoek) ·
`plan/dagelijks-publiceren.md` (automatisering om 06:00)

---

## SEO — wat nu ontbreekt en waarom het nu moet

De opdracht is expliciet: het archief moet goed vindbaar zijn in Google, en dat
moet vanaf het begin meegenomen worden. Huidige stand van de gegenereerde site:

| Aanwezig | Ontbreekt |
|---|---|
| `<title>`, `meta description` | `rel=canonical` |
| `og:title`, `og:description`, `og:type` | JSON-LD (`NewsArticle`, `Organization`, `HowTo`) |
| `sitemap.xml` | `robots.txt` |
| semantische HTML, snel, geen JS | RSS-feed, `og:url`, `og:image`, `article:published_time` |

Belangrijker dan de techniek is de inhoudsstrategie: **een archief van
180-woordssamenvattingen van andermans persberichten rankt niet en hoort niet te
ranken.** Het zoekverkeer moet komen van de toepassingenpagina's (mensen zoeken
op *"hoe gebruik ik AI voor offertes"*) en van onderhouden naslagpagina's over
terugkerende begrippen en regels. Dat is besloten in het gesprek van 29 juli en
staat nog niet in code.
