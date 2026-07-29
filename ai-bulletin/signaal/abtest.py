"""A/B-toetsing van onderwerpregels — en de vraag of toetsen zin heeft.

Dit is de enige laag in het systeem die conversie echt meet. De koptoets vangt
slechte koppen af en de score kiest tussen varianten, maar geen van beide weet
wat lezers werkelijk doen. Alleen verzendcijfers weten dat.

De belangrijkste functie hier is daarom niet de toets zelf maar
`benodigde_steekproef`: die vertelt je of je lijst groot genoeg is om het
verschil dat je zoekt überhaupt te kunnen zien. Bij de meeste beginnende
nieuwsbrieven is het antwoord nee, en dan is een A/B-test geen meting maar een
muntworp met extra stappen.

Rekenwijze: tweezijdige toets op twee proporties, 95% betrouwbaarheid en 80%
onderscheidend vermogen. Online rekenmachines geven vaak lagere aantallen
omdat ze eenzijdig toetsen of een andere variantieschatting gebruiken; deze
implementatie is bewust de conservatieve variant.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Standaardnormale kwantielen; hardgecodeerd zodat er geen scipy nodig is.
Z_TWEEZIJDIG_95 = 1.959964
Z_VERMOGEN_80 = 0.841621


@dataclass
class Steekproefadvies:
    per_variant: int
    totaal: int
    baseline: float
    doel: float
    haalbaar_bij: str

    def __str__(self) -> str:
        return (
            f"{self.per_variant:,} ontvangers per variant "
            f"({self.totaal:,} totaal) om {self.baseline:.1%} → {self.doel:.1%} "
            f"aan te tonen"
        ).replace(",", ".")


def benodigde_steekproef(
    baseline: float,
    verbetering: float,
    z_alpha: float = Z_TWEEZIJDIG_95,
    z_vermogen: float = Z_VERMOGEN_80,
) -> Steekproefadvies:
    """Hoeveel ontvangers per variant om `verbetering` aan te tonen.

    `baseline` en `verbetering` zijn absolute proporties: een basis van 0,25
    met een verbetering van 0,02 betekent 25% → 27%.
    """
    if not 0 < baseline < 1:
        raise ValueError("baseline moet tussen 0 en 1 liggen")
    if verbetering <= 0 or baseline + verbetering >= 1:
        raise ValueError("verbetering moet positief zijn en binnen bereik blijven")

    p1, p2 = baseline, baseline + verbetering
    gemiddeld = (p1 + p2) / 2

    teller = (
        z_alpha * math.sqrt(2 * gemiddeld * (1 - gemiddeld))
        + z_vermogen * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    ) ** 2
    n = math.ceil(teller / (verbetering ** 2))

    return Steekproefadvies(
        per_variant=n,
        totaal=n * 2,
        baseline=p1,
        doel=p2,
        haalbaar_bij=f"lijst vanaf {n * 2:,}".replace(",", "."),
    )


@dataclass
class Toetsuitslag:
    variant_a: float
    variant_b: float
    verschil: float
    p_waarde: float
    significant: bool
    conclusie: str


def toets(
    a_succes: int, a_totaal: int, b_succes: int, b_totaal: int, alpha: float = 0.05
) -> Toetsuitslag:
    """Tweezijdige z-toets op twee proporties.

    `succes` is het aantal opens of kliks, `totaal` het aantal verzonden mails.
    """
    if min(a_totaal, b_totaal) <= 0:
        raise ValueError("beide varianten moeten verzonden zijn")

    p_a, p_b = a_succes / a_totaal, b_succes / b_totaal
    gepoold = (a_succes + b_succes) / (a_totaal + b_totaal)
    noemer = math.sqrt(gepoold * (1 - gepoold) * (1 / a_totaal + 1 / b_totaal))

    if noemer == 0:
        return Toetsuitslag(p_a, p_b, 0.0, 1.0, False, "geen variatie om te toetsen")

    z = (p_b - p_a) / noemer
    p_waarde = 2 * (1 - _normale_cdf(abs(z)))
    significant = p_waarde < alpha

    if significant:
        winnaar = "B" if p_b > p_a else "A"
        conclusie = f"variant {winnaar} wint (p={p_waarde:.3f})"
    else:
        advies = benodigde_steekproef(max(p_a, 0.01), max(abs(p_b - p_a), 0.005))
        conclusie = (
            f"geen aantoonbaar verschil (p={p_waarde:.3f}). "
            f"Voor dit verschil had je {advies.per_variant} per variant nodig."
        )

    return Toetsuitslag(p_a, p_b, p_b - p_a, round(p_waarde, 4), significant, conclusie)


def _normale_cdf(x: float) -> float:
    """Verdelingsfunctie van de standaardnormale verdeling."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def adviestabel(baseline: float = 0.35) -> list[Steekproefadvies]:
    """Wat kun je zien bij welke lijstgrootte — de tabel die het gesprek stuurt."""
    return [benodigde_steekproef(baseline, v) for v in (0.10, 0.05, 0.03, 0.02, 0.01)]
