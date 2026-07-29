# Elke ochtend om 6 uur — bouwplan

Doel: elke dag van de week om 06:00 Nederlandse tijd staat de nieuwe editie op
aibulletin.nl en ligt hij in de inbox van de abonnees. Zonder dat iemand iets
hoeft te doen.

Dit document beschrijft wat daarvoor nog moet worden gebouwd, in welke volgorde,
en welke ene beslissing jij moet nemen voordat ik begin.

Zeven dagen per week is een zwaardere eis dan vijf, en niet alleen omdat het er
twee meer zijn — zie §6. Die twee dagen zijn de enige plek in dit hele product
waar iets kan ontstaan wat concurrenten niet kunnen kopiëren, maar alleen als je
er iets anders neerzet dan meer van hetzelfde.

---

## 1. De kern: "om 6 uur" kan niet met een cron

Het meest voor de hand liggende ontwerp — zet de GitHub Actions-cron op 06:00 en
klaar — werkt niet. Niet door een fout in onze code, maar door hoe GitHub's
planner werkt.

GitHub voert geplande workflows uit op gedeelde infrastructuur. De vertraging
tussen het geplande tijdstip en de daadwerkelijke start is normaal 15 minuten en
loopt tijdens drukke uren op tot meer dan twee uur. Dat is geen instelling die je
kunt aanzetten; het zit vóór de wachtrij van de runner. GitHub heeft sinds maart
2026 wél een `timezone`-veld naast `cron` (dat lost onze zomertijd/wintertijd-
kwestie netjes op), maar in de discussie waarin dat werd aangekondigd is het
eerste dat gebruikers melden precies dit: de tijdzone klopt, de uitvoering is
uren te laat.

Voor een product waarvan de belofte letterlijk "elke ochtend om 6" is, is dat
fataal. Eén ochtend om 07:40 is erger dan een dag overslaan: het is de belofte
die je verkoopt.

**De oplossing is de bouwtijd loskoppelen van de verzendtijd.**

De pijplijn draait ruim vóór zessen en mag rustig zwabberen. Hij levert het
resultaat af bij twee partijen die wél op de klok kunnen leveren:

- de e-mail gaat als *ingeplande campagne* naar de ESP, met verzendtijd 06:00 —
  op tijd versturen is hun kernproduct, niet iets wat wij moeten nabouwen;
- de website gaat naar GitHub Pages, waar publicatietijd niet uitmaakt zolang
  het vóór 06:00 gebeurt.

Daarmee wordt de vertraging van GitHub een marge in plaats van een probleem.
Start je om 04:20, dan heb je 100 minuten speling voordat de belofte breekt — en
we bouwen een controle die je waarschuwt zodra die marge opraakt.

---

## 2. Wat er al staat

Om niet te verkopen wat er al is:

| Onderdeel | Status |
|---|---|
| Verzamelen uit 8 brontypes | code klaar, **nooit live gedraaid** |
| Scoren, ontdubbelen, shortlist | klaar en getest |
| LLM-jury die 6 items kiest en schrijft | code klaar, **nooit live gedraaid** |
| Terugval op heuristische selectie als de jury faalt | klaar en getest |
| Koppentoets | klaar, draait in de pijplijn |
| Mail-HTML, Markdown, JSON | klaar en getest |
| Statische website uit alle edities | klaar en getest |
| Workflow met cron, tests, Pages-deploy | klaar, **timing onbetrouwbaar (§1)** |

Wat ontbreekt is alles tussen "er is een editie gerenderd" en "de lezer heeft
hem". Dat is §3.

---

## 3. De vijf gaten in de machinerie

### 3.1 De pijplijn heeft geen geheugen — dit is de ernstigste

Het ontdubbelen werkt binnen één run: dezelfde modelrelease op Hacker News, de
vendor-blog en Tweakers wordt één item. Maar er is niets dat een run vergelijkt
met de run van gisteren.

Een verhaal dat drie dagen achter elkaar door verschillende media wordt opgepikt,
kan drie dagen achter elkaar in de editie belanden. Bij één handmatige editie
merk je dat niet. Bij dagelijkse automatische publicatie is het de eerste klacht
die je krijgt, en terecht — je stuurt mensen oud nieuws als nieuw.

**Bouwen:** een index van wat al gepubliceerd is.

```python
# signaal/historie.py
def laad_index(map_: Path, dagen: int = 30) -> Historie
def is_al_gepubliceerd(item: Item, historie: Historie) -> str | None   # geeft de datum terug
def filter_nieuw(items: list[Item], historie: Historie) -> list[Item]
```

De index wordt afgeleid uit `edities/*.json` — geen aparte database die uit de
pas kan lopen. Vergelijken gaat op drie sleutels, in aflopende hardheid:
gecanonicaliseerde URL, titelgelijkenis via de bestaande `dedupe`-logica, en de
`bron`+`datum`-combinatie. De laatste vangt het geval waarin een tweede uitgever
hetzelfde persbericht overschrijft.

Bewust géén harde blokkade maar een aftrek in de voorscore voor bijna-treffers:
een vervolgstap in een lopend verhaal ("de AI-wet gaat nu écht in") is legitiem
nieuws, een herhaling niet. Alleen een exacte URL-match wordt hard geweigerd.

### 3.2 Er is geen verzendlaag

Er staat geen regel code die een mail de deur uit doet. De HTML is klaar met
`{{unsubscribe}}`, verder niets.

**Keuze: Laposta.** Nederlands, EU-hosting, verwerkersovereenkomst standaard, en
de API doet precies wat §1 nodig heeft: campagne aanmaken, vullen met onze HTML,
en apart inplannen via `POST /v2/campaign/{id}/action/schedule`. Dat inplannen is
het scharnierpunt van het hele ontwerp — een ESP die alleen "nu versturen" kan,
dwingt ons terug in het cron-probleem.

**Bouwen:**

```python
# signaal/verzenden.py
class VerzendFout(RuntimeError): ...

def maak_campagne(editie: Editie, html: str, config: dict) -> str   # → campagne-id
def plan_in(campagne_id: str, wanneer: datetime, config: dict) -> None
def annuleer(campagne_id: str, config: dict) -> None
def status(campagne_id: str, config: dict) -> str
```

Twee dingen die in deze laag horen en makkelijk vergeten worden:

- **Idempotentie.** Draait de workflow twee keer (handmatig opnieuw, of een
  retry), dan mag er geen tweede campagne komen. Sleutel op de editiedatum; is er
  al een campagne voor vandaag, dan die bijwerken in plaats van een nieuwe maken.
- **De onderwerpregel** komt uit `editie.onderwerp` en de preheader uit
  `editie.preheader`. Die worden nu wel geschreven en getoetst, maar nergens
  gebruikt — de ESP is de eerste plek waar ze echt terechtkomen.

### 3.3 De live bronnen zijn nooit gedraaid

De hele pijplijn is end-to-end getest met fixtures. De netwerkbronnen en de
LLM-aanroep zijn nooit één keer echt uitgevoerd, omdat de omgeving waarin dit is
gebouwd geen uitgaand internet heeft.

Reken op stukgelopen feed-URL's — die verhuizen voortdurend — en op kleine
verrassingen in de vorm van de LLM-uitvoer. Dit is geen ontwerpwerk maar
schoonmaakwerk, en het moet gebeuren vóórdat er iets automatisch de deur uitgaat.

**Bouwen:** `python -m signaal.cli --bronnen-check`, dat elke feed één keer
ophaalt en per bron rapporteert: aantal items, nieuwste datum, HTTP-status. Eén
commando dat je ook later kunt draaien als een bron stil lijkt te vallen. Daarna
één echte run met `--heuristisch` (geen LLM-kosten) en één met de jury.

### 3.4 Niemand merkt het als het misgaat

Een dagelijks product faalt stil. De workflow wordt rood op een tabblad dat
niemand openheeft, en de eerste die het merkt is een lezer.

**Bouwen:** een controle die ná zessen kijkt of het gelukt is, niet ervoor.

```yaml
# tweede workflow, 06:15 Europe/Amsterdam
- editie van vandaag aanwezig in edities/?
- campagne-status bij de ESP is "verzonden"?
- aibulletin.nl/{datum}/ geeft HTTP 200?
```

Bij een nee: een GitHub-issue met het label `uitgevallen` én een mail naar de
redactie. Bewust twee kanalen — een issue is makkelijk te missen om 06:15.

Daarbij een harde afkap in de hoofdworkflow: is het na **05:30** en is de
campagne nog niet ingepland, dan stopt de run met een duidelijke fout in plaats
van alsnog een campagne te maken die om 06:40 vertrekt. Te laat is dan een
zichtbare fout in plaats van een stille gebroken belofte.

### 3.5 Abonneebeheer bestaat niet

Het aanmeldformulier op de site post nu naar `#`. Dat moet naar Laposta, met
dubbele opt-in (AVG-verplichting, geen feature), en de voorkeurenpagina
— dagelijks / wekelijks / alleen groot nieuws — moet echte lijsten of segmenten
worden in plaats van een plaatje.

Dat is grotendeels configuratiewerk in de ESP, niet in onze code. Wat wél onze
code raakt: de drie frequenties zijn drie verschillende verzendingen. Wekelijks
en "groot nieuws" zijn geen aparte edities maar samenvattingen van bestaande —
dat is fase 4, niet fase 1.

---

## 4. De dagindeling

| Tijd (Europe/Amsterdam) | Wat |
|---|---|
| 04:20 | Workflow start, alle zeven dagen. Ruim vóór de belofte; §1 verklaart waarom. |
| 04:20–04:40 | Verzamelen, filteren tegen de historie, scoren, ontdubbelen, jury. Op zaterdag geen live bronnen maar het eigen archief (§6). |
| | **Kwaliteitspoort in code:** minstens 3 items boven de drempel? Koppen door de toets? Geen item dat al gepubliceerd is? Minstens 3 verschillende bronnen? Zo nee → terugval of stop, met melding. |
| 04:40 | Site naar Pages. Campagne aangemaakt bij de ESP, **ingepland op 06:00**. |
| 04:42 | Proefmail naar de redactie met een link om te annuleren. |
| 05:30 | Harde afkap: niets ingepland → fout + melding, geen late verzending. |
| 06:00 | De ESP verstuurt. Betrouwbaar, want dat is hun vak. |
| 06:15 | Controleworkflow: verzonden? site live? Zo nee → issue + mail. |

---

## 5. "Wordt dit een goede site met echte artikelen?"

Eerlijk antwoord: **zoals het er nu staat, nee.** Drie redenen, waarvan de derde
de vervelendste.

### 5.1 Het zijn geen artikelen

Eén bericht is nu een kop, één kernzin, drie tot vier zinnen feit en drie tot
vier zinnen duiding. Ongeveer 180 woorden. Dat is een uitstekend nieuwsbericht
voor in een mail, maar het is geen artikel.

Op de site krijgt elk bericht een eigen pagina, waardoor het er *uitziet* als een
artikel. Wie via Google binnenkomt en een artikel verwacht, vindt zes alinea's
die zijn afgeleid van andermans publicatie. Dat is precies het profiel van een
pagina die zoekmachines wegdrukken, en terecht: er staat niets in wat niet ergens
anders al stond.

De mail is dus goed. De site is nu een mooi vormgegeven archief van die mail.
Dat is iets anders dan een publicatie.

### 5.2 Het systeem kan niet zeggen "vandaag was er weinig"

Dit is de ernstigste en hij zit in de code. `kies_heuristisch` doet
`selecties[:6]` — de zes hoogst scorende, wat die score ook is. En de
systeemprompt zegt: *"Als een kandidaat te dun is om over te schrijven, kies een
andere."* Dat dwingt het model om er altijd zes te vinden.

Er bestaat geen pad waarin de uitvoer vier items is. Op een stille zondag
produceert de pijplijn zes berichten met exact hetzelfde zelfvertrouwen als op
een drukke maandag. De lezer kan het verschil niet zien — en leert daardoor dat
de zes niet betekenen dat er zes dingen waren.

Zes vaste items is een *formaat*, geen redactionele keuze. Iedere nieuwsbrief met
een vast aantal heeft dit probleem; de meeste lossen het op met vulling.

### 5.3 De pijplijn heeft nog nooit gedraaid

De editie die nu op de site staat, heb ik met de hand geschreven. Dat is geen
bewijs over wat de automaat produceert — het is bewijs over wat ik produceer.

De LLM-jury is nooit één keer echt aangeroepen. Alles is getest met fixtures. De
vraag "wordt de kwaliteit goed" is op dit moment dus niet met bewijs te
beantwoorden, door niemand, ook niet door mij. Wie zegt van wel, gokt.

### 5.4 Wat het wél goed maakt

**Een ondergrens in plaats van een quotum.** Verander "altijd zes" in "hoogstens
zes, minimaal drie, en alleen items boven een relevantiedrempel". Een editie van
vier sterke berichten verslaat zes met twee vullers, elke dag van de week.

Dit is ook het enige onderdeel van dit product waarvan ik zeker weet dat de
concurrentie het niet kopieert: je kunt publiek opschrijven *"soms sturen we er
vier, omdat het er vier waren"*, en niemand met een vast formaat kan dat nazeggen
zonder toe te geven dat het hunne is opgevuld. Het kost je niets en het is direct
geloofwaardig.

Concreet: `score.py` krijgt een absolute drempel naast de bestaande relatieve
rangschikking, de systeemprompt krijgt expliciet toestemming om er minder dan zes
te leveren, en het schema laat 3 tot 6 items toe in plaats van precies 6.

**Eén echt artikel per week.** Zie §6 — dat is waar de zondag voor is.

---

## 6. Zeven dagen: waarom dat geen zeven keer hetzelfde moet zijn

In het weekend publiceren labs niets, toezichthouders niets, en de vakmedia
draaien op halve kracht. De invoer van zaterdag en zondag is structureel de
dunste van de week, terwijl §5.2 zegt dat de pijplijn er evengoed zes uit perst.

Zeven identieke edities betekent dus twee zwakke per week — en dat zijn precies
de edities die mensen afleren te openen. De grote dagelijkse nieuwsbrieven doen
dit daarom nergens: Axios en Morning Brew draaien doordeweeks hun nieuwsformat en
in het weekend iets anders.

Zeven dagen kan wél, en wordt zelfs je sterkste kaart, als de weekenddagen een
ander product zijn:

| Dag | Formaat | Bron |
|---|---|---|
| ma–vr | De zes van vandaag | live bronnen |
| **za** | **De week in zes** — wat er van deze week over een maand nog toe doet | het eigen archief, geen nieuwe bronnen nodig |
| **zo** | **Eén stuk van 800–1200 woorden** | niet afgeleid van een persbericht |

Zaterdag is bijna gratis: de zes van de week kiezen uit `edities/` is een
selectieprobleem op materiaal dat je al hebt, en het is oprecht nuttig voor
iedereen die drie dagen niet heeft gekeken. Dat draait volledig automatisch.

Zondag is het antwoord op je vraag over echte artikelen. Eén stuk per week dat
níét van een persbericht komt: een rapport van de AP, DNB of het Rathenau
Instituut daadwerkelijk lezen en uitleggen, of naast elkaar zetten wat drie
leveranciers over hetzelfde beweren. Dat is het enige deel van dit product dat
niet te scrapen valt, het enige dat mensen doorsturen, en het enige waar Google
een reden heeft om je boven de bron te zetten.

**Mijn advies over die zondag: automatiseer hem niet.** Zes dagen commodity laten
draaien door de machine is precies waar de machine goed in is. De zevende is waar
jouw tijd het meeste waard is. Het model kan een concept leveren op basis van het
rapport, maar het stuk dat je site een publicatie maakt in plaats van een archief,
moet iemand echt geschreven hebben.

Dat is ook eerlijk richting de lezer: zes dagen machinewerk met verantwoording
eronder, één dag mensenwerk. Dat verschil mag je opschrijven.

---

## 7. De ene beslissing die van jou is

Publiceer je elke ochtend automatisch wat het taalmodel heeft geschreven, zonder
dat een mens het heeft gezien?

Dat is niet vrijblijvend. De hele geloofwaardigheidsopbouw van dit product —
feiten gescheiden van duiding, kanttekening bij elk ongetoetst cijfer, bron en
datum per item, correctiebeleid — belooft impliciet dat er iemand oplet. Nooit
kijken is daarmee in tegenspraak.

Tegelijk: elke ochtend moeten goedkeuren is precies de automatisering die je hebt
gevraagd, weggegooid.

**Mijn voorstel is een annuleervenster in plaats van een goedkeuringspoort.**

De campagne wordt om 04:40 ingepland voor 06:00 en de redactie krijgt direct een
proefmail met één knop: *stoppen*. Doe je niets, dan gaat hij. Dat behoudt de
belofte volledig — geen mens nodig — en geeft je toch een noodrem van bijna
anderhalf uur. Wie op vakantie is, hoeft niets te doen.

Uitzondering: **de eerste drie weken andersom.** Dan gaat hij alleen als je
actief op *ja* drukt. In die periode ken je de faalmodi van je eigen pijplijn nog
niet, en één verzonnen feit in week één kost meer dan drie gemiste edities. Na
drie weken zet je één regel in de config om en draait het vanzelf.

Dit is een keuze, geen technische noodzaak — zeg het als je liever meteen volledig
automatisch gaat, dan bouw ik het zo.

---

## 8. Bouwvolgorde

**Blok A — de kwaliteitsvraag beantwoorden (1 dag)**
Dit staat bewust vóór alle automatisering. Zolang §5.3 geldt, weten we niet wat
we gaan verspreiden.

1. `--bronnen-check` bouwen, alle feeds één keer ophalen, kapotte URL's
   repareren.
2. De jury drie keer echt draaien op drie verschillende dagen aan invoer, en de
   uitkomst naast de handgeschreven editie van 29 juli leggen. Dát is de meting
   die je vraag beantwoordt.
3. De ondergrens uit §5.4 inbouwen: minimaal 3, hoogstens 6, drempel in
   `score.py`, schema en prompt aangepast.
4. `historie.py` met tests, zodat een verhaal niet drie dagen achtereen
   terugkomt.

Pas als 2 een acceptabele uitkomst geeft, heeft de rest zin. Geeft het dat niet,
dan is de prompt het werk — niet de workflow.

**Blok B — verzenden (1 dag)**
Laposta-account, lijst met dubbele opt-in, `verzenden.py` met tests tegen
opgenomen antwoorden (geen live API in de testsuite). Aanmeldformulier op de site
aansluiten. Eerst handmatig één campagne naar een testlijst van drie adressen.

**Blok C — de klok (½ dag)**
Workflow om naar 04:20 met `timezone: Europe/Amsterdam`, zeven dagen,
kwaliteitspoort, afkap om 05:30, proefmail met annuleerknop, controleworkflow om
06:15.

**Blok D — het weekend (½ dag)**
De zaterdageditie uit het archief (§6). Volledig automatisch en goedkoop: geen
LLM-jury over live bronnen, maar een selectie over `edities/` van de afgelopen
zeven dagen. De zondag krijgt alleen een sjabloon en een plek in de workflow —
het schrijven blijft mensenwerk.

**Blok E — na de lancering**
Wekelijkse en "groot nieuws"-varianten voor wie minder wil, podcast-RSS om de
audio heen, en de meting die op termijn het belangrijkste is: waren de gekozen
zes achteraf de juiste zes? Zonder die lus kun je de prompt niet gericht
verbeteren.

Blok A is de enige die je niet kunt overslaan. C is een halve dag werk die niets
waard is zonder A.

---

## 9. Twee dingen die makkelijk vergeten worden

**Jullie vallen zelf onder artikel 50.** De transparantieplicht uit de editie van
29 juli geldt vanaf 2 augustus ook voor AI Bulletin: de teksten worden door een
taalmodel geschreven. De methodeverantwoording zegt dat al met zoveel woorden en
staat onder elke mail en op de werkwijzepagina — dat is waarschijnlijk voldoende.
Maar het is wel iets om bewust te controleren in plaats van per ongeluk goed te
hebben, zeker voor een uitgever die erover publiceert.

**Kosten.** De LLM-run is enkele tientallen dollarcenten per editie; dat is niet
waar het geld zit. De ESP-staffel is dat wel, en die loopt op met het aantal
abonnees. Uitzoeken vóór blok B, niet erna.

---

## 10. Wat ik niet kan garanderen

De omgeving waarin dit is gebouwd heeft geen uitgaand netwerk. Alles in §3 is te
bouwen en te testen met opgenomen antwoorden, maar de eerste echte aanraking met
de bronnen, de LLM en de ESP gebeurt op jouw machine of in de Actions-runner.
Reken op een dag schoonmaakwerk daar, en plan de lancering niet op de dag dat
blok C af is.
