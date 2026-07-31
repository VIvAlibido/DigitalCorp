# AI Bulletin — werkgeheugen

Dit bestand is het geheugen van dit project. Het wordt automatisch geladen aan
het begin van elke sessie. Staat iets hier niet in, dan bestaat het de volgende
keer niet meer.

**Onderhoudsregel:** elke afgeronde beslissing komt hier binnen dezelfde sessie
in te staan. Niet in een samenvatting, niet in een chatbericht — hier.

---

## Wat we bouwen

> **Dit is de doelstelling. Vastgelegd op 30 juli 2026 op uitdrukkelijk verzoek
> van de opdrachtgever, met de opdracht er nooit van af te wijken.**
>
> Wijkt een voorstel — van de assistent of van een agent — hiervan af, dan wordt
> dat eerst benoemd en niet stil uitgevoerd. Verandert de doelstelling zelf, dan
> gebeurt dat hier en met een datum erbij.

**AI Bulletin is een Nederlandstalige dagelijkse AI-nieuwsbrief met een
website-archief, die twee dingen doet die de andere niet doen:**

**1. Elke dag één ding dat je kunt dóén.**
De anderen duiden — wat er gebeurd is en waarom het uitmaakt. Wij laten
handelen. Elke editie bevat één toepassing die de lezer vandaag kan uitvoeren,
met een eerlijke tijdsindicatie. Is er geen echte handeling, dan is er geen
rubriek; er wordt nooit een handeling verzonnen om de rubriek te vullen.

**2. Laten zien wat we niet zeker weten.**
Dit is niet bescheidenheid maar het bewijsstuk. Peer-reviewed onderzoek (ACM
FAccT 2026; Toff & Simon 2025): lezers vertrouwen als AI gelabeld nieuws
mínder, en een uitgebreide verantwoording maakt het erger — behalve wanneer de
gebruikte bronnen worden gepubliceerd, want dán wordt het effect grotendeels
tenietgedaan. Concreet, en niet onderhandelbaar:

  - **elk cijfer heeft een herkomst** — of het bericht gaat eruit;
  - **elke editie publiceert zijn bronnen**, bij naam en met tellingen;
  - **elke editie laat zien wat het níét haalde** en waarom.

De belofte in één zin, en dit is de zin waar alles aan getoetst wordt:

> ### De enige AI-nieuwsbrief die laat zien wat hij niet zeker weet.

Die zin kan AI Report niet zeggen — geen machine die het bijhoudt. En The
Rundown wíl hem niet zeggen. Wat voor een menselijke redactie duur werk is, is
voor ons een bijproduct: de pijplijn wéét al hoeveel kandidaten er waren, uit
welke bronnen, en wat afviel.

### Wat we niet worden

- **Niet de grootste.** AI Report zit op ~48.000 abonnees met een bekende naam
  en drie jaar voorsprong. Dat gevecht voeren we niet. Ben's Bites bewijst het
  alternatief: 120.000 goed gekozen lezers verslaan 1,75 miljoen willekeurige.
- **Niet de eerste.** TheAIDaily.nl doet al een dagelijkse Nederlandse
  AI-nieuwsbrief om 07:00. Dat is een gegeven, geen probleem: lezers zitten op
  meerdere nieuwsbrieven tegelijk.
- **Niet een kopie.** Vuistregel van de opdrachtgever, 30 juli: **kopieer de
  machinerie — formaat, tijdstip, ritme, platform, aanbevelingsruil — maar
  nooit de reden van bestaan.** De lezer vraagt niet "is er plek voor nog één",
  maar "waarom lees ik deze náást wat ik al krijg". De twee punten hierboven
  zijn dat antwoord.
- **Niet doorverkocht aan wie we bespreken.** Advertenties van AI-leveranciers
  zijn het makkelijkste verdienmodel en vernietigen punt 2. Nog te beslissen,
  maar niet stilzwijgend.

**Domein:** aibulletin.nl · **Merknaam:** AI Bulletin · Later: een podcast.

### De lezer

**De geïnteresseerde professional.** Werkt niet in AI maar moet er wel iets mee:
ondernemer, marketeer, HR, jurist, zorgmanager. Snapt zijn eigen vak, niet de
techniek.

Praktische gevolgen: geen jargon zonder uitleg, geen benchmarks, geen
modelvergelijkingen om het vergelijken. Elk bericht beantwoordt impliciet
"raakt dit mijn werk?". De toepassing is werkgerelateerd, nooit een hobbytoepassing.

### Het ene kenmerk

**Toepasbaar — elke dag één ding dat je kunt dóén.**

Gekozen boven "begrijpelijk", "controleerbaar" en "kort". Begrijpelijkheid
blijft een volledige eis aan het werk maar is niet wat we zéggen.

**Herzien op 30 juli:** controleerbaarheid is niet langer alleen een eis aan
het werk — het is het tweede punt van de doelstelling geworden, omdat het
onderzoek uitwijst dat het het enige is dat het vertrouwensverlies van een
AI-nieuwsbrief compenseert. Toepasbaar is nog steeds waar we om bekend willen
staan; aantoonbaar is waaróm je ons gelooft. Werkafspraak 2 ("geen nieuw
kenmerk zonder dat er één afvalt") blijft gelden: er is geen derde bij gekomen
en er komt er ook geen.

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

0. **Elke controle sluit aan op álle routes — vraag welk bestand de lezer ziet.**
   Bij de eerste poging zat de keuring op twee van de drie routes, en niet op
   `site.bouw()` — juist de route die de site opbouwt uit `edities/`. De
   tegenspreker vond dat binnen drie minuten met de vraag: *welk bestand ziet
   de lezer werkelijk, en welke code heeft dát bestand gekeurd?* De fouten in dit project kwamen
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
| 18 | **Alle redactionele controles staan in `keuring.py`** en draaien op drie routes: `render_selectie()`, `draai()` en **`site.bouw()`**. De laatste is de route die de lezer bereikt en werd bij de eerste poging vergeten | blokkeren in render_selectie() helpt niet als het JSON-bestand daarna nog met de hand wordt bijgewerkt. `site.bouw(keuren=False)` bestaat alleen voor structuurtests |
| 17 | De dagelijkse editie gebruikt **géén ik-vorm, geen uitweidingen, geen gespeelde oneerbiedigheid** | 6 berichten × 7 dagen = 42 meningen per week; die heeft niemand. Nagedane branietaal is binnen twee edities doorzichtig |
| 9 | Eerst **goedkeuren vóór verzenden**, later omschakelen naar een annuleervenster | opdrachtgever heeft nu veel tijd, straks weinig; de omschakeling moet één regel config zijn, geen verbouwing |
| 10 | Colofon en privacyverklaring worden **uit `uitgever:` in config.yaml gegenereerd** | één plek voor deze gegevens, zodat er geen tweede versie kan verouderen; publicatie wordt geblokkeerd zolang ze ontbreken |
| 11 | Hosting op **Vercel**, gekoppeld aan deze repo. Root directory `ai-bulletin` | opdrachtgever, 29 juli. Let op: de repo-root bevat een ándere website; zonder die instelling publiceert Vercel die |
| 19 | **Vercel is de enige publicatieroute.** De GitHub Pages-deploy is op 30 juli uit de workflow gehaald | opdrachtgever, 30 juli. Twee routes naast elkaar leveren twee versies van de site op twee adressen; dan is niet meer te zeggen welke de lezer ziet. De workflow publiceert nu door de editie te committen — die push laat Vercel bouwen |
| 12 | **Elke editie gaat altijd naar kees@telemedia.es** | opdrachtgever, 29 juli. Vastgelegd in `verzending.altijd_naar`; een test bewaakt dat het niet wegvalt |
| 20 | **Elk cijfer heeft een herkomst, of het bericht gaat eruit.** Blokkade in `keuring.py`, geen redactionele keuze | opdrachtgever, 30 juli. Op 30 juli stond "900 miljoen wekelijkse ChatGPT-gebruikers" zonder kanttekening terwijl vergelijkbare cijfers er wél een kregen. Inconsequentie is hier erger dan strengheid: de belofte staat onder elke editie |
| 21 | **Elke editie publiceert zijn bronnen**, bij naam en met tellingen — niet "89 berichten uit 6 bronnen" maar wélke 6 | opdrachtgever, 30 juli, op grond van ACM FAccT 2026: het publiceren van de bronnenlijst is wat het vertrouwensverlies van een AI-melding grotendeels tenietdoet. Een langere verantwoording doet het tegenovergestelde |
| 22 | **Elke editie laat zien wat het níét haalde**, met de reden | opdrachtgever, 30 juli. Voor een menselijke redactie duur werk, voor ons een bijproduct: de shortlist en de afvalredenen lopen al door de pijplijn. Geen enkele onderzochte nieuwsbrief doet dit |

## Beslissingen die openstaan — deze blokkeren werk

| # | Vraag | Wat het blokkeert |
|---|---|---|
| **D** | **Beantwoord op 30 juli — zie hieronder.** Rest: welk adres hoort in de colofon, en is aibulletin.nl geregistreerd? | Zie "Feiten die vaststaan". |
| **E** | Wat betekent "nummer één" in een getal — abonnees, bezoekers, iets anders? | Kunnen beoordelen of een keuze over zes maanden heeft gewerkt. **Context sinds 30 juli:** AI Report zit op ~48.000 abonnees. "Nummer één" op breedte is daarmee geen doel maar een fantasie; zie plan/groei.md §1 |
| **F** | **Wordt de doelgroep toetsbaar gemaakt** — een beroepsgroep, of een andere vorm van "voor wie is dit"? | De selectie. Niet omdat de markt bezet zou zijn (dat is hij niet, zie hieronder), maar omdat er bij "de geïnteresseerde professional" niets te toetsen valt en de editie dan terugglijdt naar algemeen AI-nieuws. Zie plan/groei.md §3 fase 0 |
| **G** | **Blijft de ESP Laposta, of wordt het Substack?** | Fase 2 van de groei. Laposta heeft geen aanbevelingsnetwerk en dat netwerk is 30–50% van de groei van een nieuwe nieuwsbrief. Advies staat in plan/groei.md §4: Substack tot 1.000, aibulletin.nl blijft archief |

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
- **De LLM-jury heeft gedraaid op 30 juli** (run 30542389141): 89 kandidaten,
  6 berichten, keuring doorstaan, 26 pagina's gebouwd. Twee lessen: het schema
  mag geen `minItems`/`maxItems` bevatten (400 van de API), en vier van de elf
  feeds stonden op 404 — waaronder drie van de zes Nederlandse. Eén bericht
  (Gemma 4) had een willekeurige GitHub-repo als bron; de feitenchecker moet
  daaroverheen vóór er ooit iets verstuurd wordt.
- **Een editie mag korter zijn dan zes** — opgelost op 29 juli. De jury krijgt
  een bereik van 3 tot 6; de heuristische terugval gebruikt een verhouding tot
  de sterkste kandidaat van die dag. Die verhouding vangt een zwakke staart,
  niet een middelmatige dag: dat laatste kan alleen de jury zien, en die heeft
  nog nooit gedraaid.
- **De pijplijn heeft geheugen tussen edities** — `historie.py`, opgelost op
  29 juli. Zelfde bron-URL wordt geweerd, een sterk gelijkende kop gestraft.
- **De markt is niet leeg — uitgezocht op 30 juli, zie plan/groei.md.**
  **TheAIDaily.nl** doet exact ons product: elke werkdag om 07:00 een mail van
  vijf minuten met "wat er nieuw is en waarom het uitmaakt", voor Nederlandse
  bedrijven. **AI Report** (Klöpping) heeft ~48.000 abonnees en is de grootste
  Nederlandstalige Substack. Dit had vóór de eerste regel code uitgezocht
  moeten worden. Niet opnieuw gaan onderzoeken; wel de gevolgen trekken.
  **Maar: dat is geen reden om af te haken, en die conclusie was een
  overcorrectie van mij.** Lezers zitten op meerdere nieuwsbrieven tegelijk;
  48.000 is een fractie van de Nederlandse beroepsbevolking. De vraag is niet
  of er plek is (die is er) maar waarom iemand ons leest *náást* wat hij al
  krijgt. Vuistregel, vastgelegd door de opdrachtgever op 30 juli: **kopieer de
  machinerie — formaat, tijdstip, ritme, platform, aanbevelingsruil — maar niet
  de reden van bestaan.** Zij duiden, wij laten handelen.
- **Een AI-melding kost vertrouwen; een bronnenlijst wint het terug.**
  Peer-reviewed (ACM FAccT 2026; Toff & Simon 2025): lezers vertrouwen nieuws
  dat als AI-gemaakt is gelabeld mínder, ook als het niet onnauwkeuriger is —
  en een *uitgebreide* verantwoording verlaagt het vertrouwen verder dan een
  korte regel. Wat het effect grotendeels tenietdoet is het publiceren van de
  gebruikte bronnen. Onze methodeverantwoording doet dus op dit moment het
  verkeerde: veel uitleg, geen bronnenlijst. Zie plan/onderscheid.md deel B.
- **De nieuwsbrief is het gevolg van een publiek, niet de oorzaak.**
  AlphaSignal heeft 200.000+ LinkedIn-volgers en bereikt 10 miljoen mensen per
  maand; AI Report begon als podcast met een bekende naam. Wij bouwen het
  omgekeerd, en dat is de grootste risicofactor in dit project.
- **Nieuwssamenvattingen ranken niet.** Google zet de primaire bron boven een
  samenvatting daarvan. Het archief is geen SEO-bezit; de toepassingen en de
  naslagpagina's zijn dat wel. Zie "SEO" hieronder.
- **De uitgever is `Digitalcorp OÜ`** — aan elkaar geschreven, zoals het Estse
  handelsregister hem noemt. Registrikood **16962575**, opgericht 9 april 2024,
  statutair adres Tornimäe tn 5, 10145 Tallinn, EMTAK 61101 (telecom),
  aandelenkapitaal €800. **Geen btw-nummer** — het register meldt "VAT
  identification number: Missing". Contact: kees@telemedia.es, +34 666 431 167.
  Bron: inforegister.ee, doorgegeven door de opdrachtgever op 30 juli.
  Sinds die invulling geeft `site.controleer_publicatiegereed()` **geen
  blokkades meer**: de site mag live.
- **Het colofonlabel is niet "KvK-nummer".** Een Estse registrikood onder een
  Nederlands label zetten is een onwaarheid op precies de pagina die de
  identiteit moet bewijzen. `uitgever.register` bepaalt het label; een test
  bewaakt dat er geen "KvK" meer boven staat.
- **Twee dingen om in de gaten te houden** (opgemerkt bij het invullen, niet
  door de opdrachtgever genoemd): het adres Koninginneweg 11, 1217 KP Hilversum
  is doorgegeven als werkadres maar staat in geen enkel register — daarom staat
  het (nog) niet in de colofon. En het jaarverslag over 2025 stond op
  inforegister.ee rood doorgestreept, wat op een achterstallige deponering
  wijst; in Estland kan dat uiteindelijk tot doorhaling leiden.
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
GitHub Actions-workflow die de editie vastlegt, en `vercel.json` +
`bouw_site.py` voor Vercel — met een publicatieblokkade zolang de
uitgeversgegevens ontbreken.

**Aantoonbaarheid** (31 juli) — punt 2 van de doelstelling, twee van de drie af:
- **Beslissing 20 draait.** `keuring._keur_herkomst()` blokkeert elk bericht met
  een percentage, bedrag, groot getal of verhouding zonder kanttekening.
  Natelbare aantallen ("7 gigafabrieken"), jaartallen en wetsartikelen tellen
  niet mee. De regel vond meteen de verzonnen "3.700 pagina's" in de editie van
  29 juli; die is verwijderd, niet van een kanttekening voorzien — een
  kanttekening bij een verzinsel maakt het verzinsel officieel.
- **Beslissing 21 draait.** `Editie.bronlijst` bevat de namen; de
  methodeverantwoording noemt ze. Die tekst is bewust ingekort: onderzoek zegt
  dat een lángere verantwoording het vertrouwen verder verlaagt. Oude edities
  zonder namen vallen terug op het aantal.
- **Beslissing 22 staat nog open**: "wat het niet haalde". Vereist dat de
  afvalredenen meelopen in de shortlist.

**Verzenden** (30 juli): `verzenden.py` stuurt de editie per SMTP naar
`verzending.altijd_naar`, met tekst én HTML, en vervangt `{{unsubscribe}}` —
zonder ESP vult niemand dat haakje in. Het is de derde en strengste poort:
weigert bij elke blokkade uit `keuring.keur()`, bij een ontbrekende afzender,
bij een lege uitschrijflink, en bij verzenden naar iemand anders dan de vaste
ontvanger zolang de uitgeversgegevens ontbreken. Reden: een fout op de site
herstel je met een commit, een fout in een mail staat in andermans inbox.
Geheimen komen uit de omgeving (`SMTP_HOST`, `SMTP_POORT`, `SMTP_GEBRUIKER`,
`SMTP_WACHTWOORD`, `SMTP_AFZENDER`), nooit uit config.yaml. De workflow slaat
de stap over zolang `SMTP_HOST` leeg is.

**Ontbreekt:** ESP-koppeling en abonneebeheer (nodig vanaf de tweede lezer),
weekendformaten,
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
