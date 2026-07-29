"""Tests voor de kop-werkbank: leesbaarheid, score, variantkeuze en A/B-rekenwerk."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from signaal import abtest, koptoets, kopscore, kopvarianten, leesbaarheid  # noqa: E402


class TestLeesbaarheid(unittest.TestCase):
    def test_lettergrepen_met_tweeklanken(self):
        # 'ui' en 'ij' zijn één lettergreep, geen twee.
        self.assertEqual(leesbaarheid.tel_lettergrepen("huis"), 1)
        self.assertEqual(leesbaarheid.tel_lettergrepen("wijn"), 1)
        self.assertEqual(leesbaarheid.tel_lettergrepen("banaan"), 2)
        self.assertEqual(leesbaarheid.tel_lettergrepen("computer"), 3)

    def test_lege_invoer_crasht_niet(self):
        self.assertEqual(leesbaarheid.tel_lettergrepen(""), 0)
        self.assertEqual(leesbaarheid.flesch_douma(""), 0.0)

    def test_korte_zinnen_scoren_hoger_dan_lange(self):
        makkelijk = leesbaarheid.flesch_douma("De kat zit op de mat. Hij slaapt.")
        moeilijk = leesbaarheid.flesch_douma(
            "De implementatie van de transparantieverplichtingen impliceert "
            "aanzienlijke organisatorische herstructureringsmaatregelen."
        )
        self.assertGreater(makkelijk, moeilijk)

    def test_niveau_labels(self):
        self.assertIn("A2", leesbaarheid.niveau(85))
        self.assertIn("B1", leesbaarheid.niveau(65))
        self.assertIn("C2", leesbaarheid.niveau(10))


class TestKopscore(unittest.TestCase):
    def test_specifieke_kop_verslaat_vage_variant(self):
        specifiek = kopscore.beoordeel("DNB: bij 73% van de aanvallen bestond de update nog niet")
        vaag = kopscore.beoordeel("Bijna driekwart van de aanvallen gebruikt een onbekend lek")
        self.assertGreater(specifiek.score, vaag.score)
        self.assertTrue(specifiek.bruikbaar)
        self.assertFalse(vaag.bruikbaar)

    def test_aanspreekvorm_verhoogt_de_score(self):
        met = kopscore.beoordeel("44% van de banken wijst je AI af bij hosting buiten Europa")
        zonder = kopscore.beoordeel("44% van de banken wijst AI af bij hosting buiten Europa")
        self.assertGreater(met.score, zonder.score)

    def test_stam_herkent_verbogen_gevolgwoord(self):
        # 'bezitten' moet 'bezit' uit de woordenlijst herkennen.
        self.assertEqual(
            kopscore._dim_gevolg("Drie bedrijven bezitten de AI's die jouw webshop vinden"),
            1.0,
        )

    def test_abstracte_kop_scoort_nul_op_gevolg(self):
        self.assertEqual(
            kopscore._dim_gevolg("Nieuwe ontwikkelingen in het AI-landschap"), 0.0
        )

    def test_voorlading_straft_late_kern(self):
        vroeg = kopscore._dim_voorlading("73% van de aanvallen misbruikt een onbekend gat vandaag")
        laat = kopscore._dim_voorlading(
            "Een onderzoek dat afgelopen periode is uitgevoerd toont 73% aan")
        self.assertGreater(vroeg, laat)

    def test_rangschikken_zet_geblokkeerde_koppen_achteraan(self):
        gerangschikt = kopscore.rangschik([
            "Bijna driekwart van de aanvallen gebruikt een lek",   # geblokkeerd
            "DNB: bij 73% van de aanvallen bestond de update nog niet",
        ])
        self.assertTrue(gerangschikt[0].bruikbaar)
        self.assertFalse(gerangschikt[-1].bruikbaar)

    def test_score_blijft_binnen_bereik(self):
        for kop in ["", "a", "DNB: 73% " * 10, "Zondag moet je chatbot iets zeggen"]:
            self.assertGreaterEqual(kopscore.beoordeel(kop).score, 0.0)
            self.assertLessEqual(kopscore.beoordeel(kop).score, 100.0)


class TestLijdendeVorm(unittest.TestCase):
    def test_lijdende_vorm_zonder_actor_wordt_afgekeurd(self):
        bezwaren = koptoets.controleer_kop("Het protocol wordt herbouwd in juli")
        self.assertTrue(any("lijdende vorm" in b for b in bezwaren))

    def test_met_handelende_partij_is_geen_bezwaar(self):
        bezwaren = koptoets.controleer_kop("Het protocol wordt herbouwd door Anthropic")
        self.assertFalse(any("lijdende vorm" in b for b in bezwaren))


class TestVariantkeuze(unittest.TestCase):
    def test_bestaande_kop_wint_als_die_het_beste_is(self):
        keuze = kopvarianten.kies_beste(
            "44% van de banken wijst je AI af als de servers buiten Europa staan",
            ["Banken en hun ontwikkelingen", "Er wordt iets besloten"],
        )
        self.assertEqual(
            keuze.gekozen, "44% van de banken wijst je AI af als de servers buiten Europa staan")
        self.assertEqual(keuze.verbetering, 0.0)

    def test_betere_variant_wordt_gekozen_en_winst_gemeld(self):
        keuze = kopvarianten.kies_beste(
            "Bijna driekwart van de aanvallen gebruikt een onbekend lek",
            ["DNB: bij 73% van de aanvallen bestond de update nog niet"],
        )
        self.assertIn("73%", keuze.gekozen)
        self.assertGreater(keuze.verbetering, 0)

    def test_er_is_altijd_een_reserve(self):
        keuze = kopvarianten.kies_beste("Zondag moet je chatbot zich melden", [])
        self.assertTrue(keuze.reserve)


class TestABTest(unittest.TestCase):
    def test_kleiner_verschil_vraagt_grotere_steekproef(self):
        groot = abtest.benodigde_steekproef(0.35, 0.10)
        klein = abtest.benodigde_steekproef(0.35, 0.01)
        self.assertGreater(klein.per_variant, groot.per_variant)

    def test_ongeldige_invoer_wordt_geweigerd(self):
        with self.assertRaises(ValueError):
            abtest.benodigde_steekproef(0.0, 0.05)
        with self.assertRaises(ValueError):
            abtest.benodigde_steekproef(0.35, 0.0)

    def test_duidelijk_verschil_is_significant(self):
        uitslag = abtest.toets(a_succes=300, a_totaal=1000, b_succes=450, b_totaal=1000)
        self.assertTrue(uitslag.significant)
        self.assertIn("B", uitslag.conclusie)

    def test_ruis_is_niet_significant_en_geeft_het_benodigde_aantal(self):
        uitslag = abtest.toets(a_succes=35, a_totaal=100, b_succes=37, b_totaal=100)
        self.assertFalse(uitslag.significant)
        self.assertIn("per variant nodig", uitslag.conclusie)

    def test_gelijke_uitkomst_crasht_niet(self):
        uitslag = abtest.toets(a_succes=0, a_totaal=50, b_succes=0, b_totaal=50)
        self.assertFalse(uitslag.significant)

    def test_adviestabel_loopt_van_grof_naar_fijn(self):
        tabel = abtest.adviestabel(0.35)
        aantallen = [a.per_variant for a in tabel]
        self.assertEqual(aantallen, sorted(aantallen))


if __name__ == "__main__":
    unittest.main(verbosity=2)
