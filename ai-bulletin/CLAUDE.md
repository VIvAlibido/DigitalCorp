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

---

## Werkafspraken

Vastgelegd op verzoek van de opdrachtgever, na terechte kritiek dat ik elke
opmerking omzette in werk zonder tegen te spreken.

1. **Tegenspreken hoort bij het werk.** Een opdracht die botst met eerder
   onderzoek, met een eerdere beslissing of met het doel, wordt eerst benoemd.
   Daarna pas uitgevoerd of aangepast — maar de tegenspraak komt eerst.
2. **Geen nieuw kenmerk zonder dat er één afvalt.** Zie het openstaande punt B
   hieronder. Dit project heeft al één keer vijf onderscheidende kenmerken
   gekregen waar het onderzoek er één voorschreef.
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
| 4 | ESP wordt **Laposta** | NL, EU-hosting, en heeft een apart schedule-endpoint — noodzakelijk voor #3 |
| 5 | Eigen tekst, nooit tekst van anderen overnemen | feiten zijn vrij, formulering niet; art. 15/15a Aw |
| 6 | Feit (`wat`) en duiding (`waarom`) blijven zichtbaar gescheiden | geloofwaardigheid is de enige verdediging tegen "zoveelste AI-nieuwsbrief" |
| 7 | Weekend krijgt een **ander formaat** dan doordeweeks | za/zo is de dunste invoer van de week; zie plan §6 |
| 8 | Zondagstuk wordt **niet geautomatiseerd** | het enige deel dat niet te scrapen is, moet mensenwerk zijn |

## Beslissingen die openstaan — deze blokkeren werk

| # | Vraag | Wat het blokkeert |
|---|---|---|
| **A** | **Wie is de lezer?** "Consumenten en bedrijven" is geen doelgroep. | Toon, welke 6 items, wat de toepassing is, elke kop |
| **B** | **Welk één kenmerk?** Nu zijn het er vijf, het onderzoek zegt één. | Homepage, onderwerpregels, SEO-focus, waar de zondag over gaat |
| **C** | Hoeveel tijd per dag is er echt beschikbaar? | Of het annuleervenster echt is of theater |
| **D** | Is aibulletin.nl geregistreerd? Is er een bedrijf/KvK achter? | Lancering, colofon, privacyverklaring, AVG-verantwoordelijke |

---

## Feiten die vaststaan — niet opnieuw uitzoeken

- **Deze omgeving heeft geen uitgaand netwerk.** WebSearch werkt, WebFetch en
  curl niet. Live bronnen en LLM-aanroepen zijn hier niet te testen. Alles is
  getest met fixtures.
- **De LLM-jury heeft nog nooit echt gedraaid.** De editie van 2026-07-29 op de
  site is met de hand geschreven en zegt niets over wat de automaat produceert.
- **De pijplijn kan niet zeggen "vandaag was er weinig".** `kies_heuristisch`
  neemt `selecties[:6]`; de prompt dwingt zes items af. Er is geen ondergrens.
  Dit moet opgelost worden vóór automatisering (plan §5.2).
- **De pijplijn heeft geen geheugen tussen edities.** Ontdubbelen werkt binnen
  één run; hetzelfde verhaal kan drie dagen achtereen terugkomen (plan §3.1).
- **Nieuwssamenvattingen ranken niet.** Google zet de primaire bron boven een
  samenvatting daarvan. Het archief is geen SEO-bezit; de toepassingen en de
  naslagpagina's zijn dat wel. Zie "SEO" hieronder.
- **AI Bulletin valt zelf onder art. 50 AI-verordening** vanaf 2 augustus 2026:
  de teksten zijn door een taalmodel geschreven en dat moet kenbaar zijn. De
  methodeverantwoording doet dat al.

---

## Stand van de bouw

**Werkt en is getest** (70 tests): verzamelen uit 8 brontypes, scoren,
ontdubbelen, shortlist, LLM-jury met terugval, koptoets/kopscore/kopvarianten,
render naar JSON/Markdown/mail-HTML, statische sitegenerator, GitHub
Actions-workflow met Pages-deploy.

**Ontbreekt:** verzendlaag (ESP), abonneebeheer, historie tussen edities,
ondergrens in plaats van quotum, weekendformaten, SEO-technisch fundament
(zie hieronder), correctie-e-mailadres, colofon/privacyverklaring.

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
