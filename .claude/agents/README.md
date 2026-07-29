# De vier agenten van AI Bulletin

## Wanneer welke

| Agent | Wanneer | Wat hij vangt |
|---|---|---|
| **eindredacteur** | vóór elke verzending | koppen die niets zeggen, duiding die niets toevoegt, onuitgelegd jargon, een toepassing die je niet kunt uitvoeren |
| **feitenchecker** | vóór elke verzending | cijfers die niet in de bron staan, leverancierclaims zonder kanttekening, overgenomen formuleringen |
| **zondagslezer** | vóór elke zondagspublicatie | een betoog dat niet sluit, stellingen die niet te verdedigen zijn, tekst die klinkt als een machine die een essayist nadoet |
| **tegenspreker** | bij elk plan of elke bewering van de assistent | ongefundeerde claims, controles die maar op één route zitten, sluipende scope, werk dat af heet |

## Hoe je ze aan het werk zet

In een sessie, gewoon in gewone taal:

```
Laat de eindredacteur en de feitenchecker naar de editie van vandaag kijken.
```

```
Zet de tegenspreker op dit plan voordat we gaan bouwen.
```

Twee agenten tegelijk op dezelfde editie is prima en gaat sneller — ze werken
onafhankelijk van elkaar. De eindredacteur en de feitenchecker overlappen
bewust niet: de een oordeelt over betekenis, de ander over waarheid.

## De volgorde die er echt toe doet

```
code  →  agent  →  mens
```

**Code eerst.** Alles wat je in `signaal/keuring.py` kunt vastleggen, hoort daar
en niet bij een agent. Code oordeelt elke keer hetzelfde, kost niets en wordt
nooit moe. Kun je een regel opschrijven als "dit mag niet", dan is het een
keuring en geen agent.

**Dan de agent**, voor oordelen die je niet in een regel kunt vangen: zégt deze
kop iets, klópt dit cijfer, klinkt dit als een mens.

**Dan de mens**, voor smaak en voor alles waar een naam onder staat. Het
zondagsstuk verschijnt onder een echte naam; een agent mag daarover adviseren,
maar niet beslissen.

## Wat je hier niet van moet verwachten

Een agent is hetzelfde taalmodel als de assistent die het werk maakte. Hij heeft
dezelfde neigingen en dezelfde blinde vlekken. Wat hij wél mist, is de redenering
van de schrijver — daardoor verdedigt hij die niet, en dat is precies waar de
winst zit.

Maar: **een agent die goedkeurt, is geen bewijs dat het goed is.** Vier agenten
die alle vier niets vinden, betekent dat vier keer hetzelfde model niets vond.
Voor de dingen die er echt toe doen — een cijfer in een kop, een claim onder je
eigen naam, een juridische bewering — blijft er een mens nodig.

## Onderhoud

Vangt een agent iets dat je in code had kunnen vastleggen, verplaats het dan naar
`keuring.py`. De agenten horen ná verloop van tijd mínder te vinden, niet meer.
Vindt een agent maandenlang niets, dan is zijn opdracht te vaag geworden of het
werk is echt beter geworden — dat verschil moet je zelf vaststellen.
