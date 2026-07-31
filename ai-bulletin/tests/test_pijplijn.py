"""Tests voor de offline delen van de pijplijn (alles behalve de LLM-jury)."""

from __future__ import annotations

import html as html_module
import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from signaal import (  # noqa: E402
    dedupe, historie, keuring, koptoets, pipeline, rank, render, score, site,
    verzenden,
)
from signaal.bronnen import basis  # noqa: E402
from signaal.cli import _laad_fixtures  # noqa: E402
from signaal.model import (  # noqa: E402
    Beschouwing, Editie, Item, Selectie, Toepassing, canonicaliseer_url,
)

PROJECT = Path(__file__).resolve().parent.parent
CONFIG = pipeline.laad_config(PROJECT / "config.yaml")


def maak_item(titel, url, brontype="rss", uren=1, bron="test", **metriek) -> Item:
    return Item(
        titel=titel,
        url=url,
        bron=bron,
        brontype=brontype,
        gepubliceerd=datetime.now(timezone.utc) - timedelta(hours=uren),
        samenvatting=titel,
        metriek=metriek,
    )


class TestURL(unittest.TestCase):
    def test_tracking_params_verdwijnen(self):
        self.assertEqual(
            canonicaliseer_url("https://WWW.Example.com/pad/?utm_source=x&id=7#kop"),
            "https://example.com/pad?id=7",
        )

    def test_trailing_slash_is_gelijk(self):
        self.assertEqual(
            canonicaliseer_url("https://example.com/a/"),
            canonicaliseer_url("https://example.com/a"),
        )

    def test_id_is_stabiel_over_varianten(self):
        a = maak_item("x", "https://example.com/a?utm_medium=mail")
        b = maak_item("x", "https://www.example.com/a/")
        self.assertEqual(a.id, b.id)


class TestFeedParser(unittest.TestCase):
    RSS = """<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>Eerste bericht</title><link>https://example.com/1</link>
      <description>&lt;p&gt;Met HTML&lt;/p&gt;</description>
      <pubDate>Tue, 29 Jul 2026 08:00:00 +0000</pubDate></item>
    </channel></rss>"""

    ATOM = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Atom bericht</title>
      <link rel="alternate" href="https://example.com/2"/>
      <summary>Samenvatting</summary>
      <published>2026-07-29T08:00:00Z</published></entry>
    </feed>"""

    def test_rss(self):
        entries = basis.parse_feed(self.RSS)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["titel"], "Eerste bericht")
        self.assertEqual(entries[0]["gepubliceerd"].year, 2026)

    def test_atom(self):
        entries = basis.parse_feed(self.ATOM)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["url"], "https://example.com/2")

    def test_kapotte_xml_geeft_lege_lijst(self):
        self.assertEqual(basis.parse_feed("<niet echt xml"), [])

    def test_strip_html(self):
        self.assertEqual(basis.strip_html("<p>Hallo &amp; tot ziens</p>"), "Hallo & tot ziens")


class TestScoring(unittest.TestCase):
    def test_recenter_scoort_hoger(self):
        vers = maak_item("A", "https://example.com/a", uren=1)
        oud = maak_item("B", "https://example.com/b", uren=30)
        score.scoor([vers, oud], CONFIG)
        self.assertGreater(vers.voorscore, oud.voorscore)

    def test_nl_relevantie_wordt_herkend(self):
        item = maak_item("Nieuwe regels onder de EU AI Act", "https://example.com/c")
        score.scoor([item], CONFIG)
        self.assertTrue(item.nl_relevant)

    def test_nl_relevantie_geeft_bonus(self):
        met = maak_item("Amsterdam bouwt model", "https://example.com/d", uren=5)
        zonder = maak_item("Someone builds a model", "https://example.com/e", uren=5)
        score.scoor([met, zonder], CONFIG)
        self.assertGreater(met.voorscore, zonder.voorscore)

    def test_leeftijdsfilter(self):
        items = [
            maak_item("vers", "https://example.com/f", uren=2),
            maak_item("oud", "https://example.com/g", uren=99),
        ]
        self.assertEqual(len(score.filter_op_leeftijd(items, 36)), 1)

    def test_shortlist_reserveert_plek_voor_nl(self):
        # Twintig sterke internationale items plus één zwak NL-item.
        items = [
            maak_item(f"Internationaal {n}", f"https://example.com/i{n}",
                      brontype="hackernews", uren=1, punten=900)
            for n in range(20)
        ]
        items.append(maak_item("Klein bericht uit Delft", "https://example.com/nl", uren=30))
        score.scoor(items, CONFIG)
        top = score.shortlist(items, 4)
        self.assertTrue(any(i.nl_relevant for i in top), "NL-quotum werd niet toegepast")


class TestDedupe(unittest.TestCase):
    def test_zelfde_url_verdwijnt(self):
        items = [
            maak_item("Titel een", "https://example.com/x"),
            maak_item("Heel andere titel", "https://example.com/x/"),
        ]
        self.assertEqual(len(dedupe.ontdubbel(items)), 1)

    def test_gelijkende_titels_clusteren(self):
        a = maak_item("Anthropic verlengt contextvenster voor agents",
                      "https://a.example.com/1", bron="A")
        b = maak_item("Anthropic verlengt het contextvenster voor agents",
                      "https://b.example.com/2", bron="B")
        over = dedupe.ontdubbel([a, b])
        self.assertEqual(len(over), 1)
        self.assertIn("B", over[0].metriek.get("ook_gemeld_door", []) + ["B"])

    def test_verschillende_onderwerpen_blijven_staan(self):
        items = [
            maak_item("Mistral brengt nieuw model uit", "https://example.com/m"),
            maak_item("Toezichthouder publiceert leidraad", "https://example.com/t"),
        ]
        self.assertEqual(len(dedupe.ontdubbel(items)), 2)

    def test_verbuigingen_tellen_als_hetzelfde_woord(self):
        self.assertTrue(dedupe.zelfde_woord("contextvenster", "contextvensters"))
        self.assertTrue(dedupe.zelfde_woord("agent", "agents"))
        self.assertTrue(dedupe.zelfde_woord("model", "modellen"))

    def test_toevallig_gedeelde_prefix_telt_niet(self):
        # Beide beginnen met "trans", maar het zijn andere woorden.
        self.assertFalse(dedupe.zelfde_woord("transformer", "transparant"))
        self.assertFalse(dedupe.zelfde_woord("productie", "producent"))

    def test_een_gedeeld_woord_clustert_niet(self):
        # Twee losse OpenAI-berichten mogen niet samengevoegd worden.
        a = maak_item("OpenAI verlaagt prijzen voor batchverwerking", "https://example.com/p1")
        b = maak_item("OpenAI opent kantoor in Dublin", "https://example.com/p2")
        self.assertEqual(len(dedupe.ontdubbel([a, b])), 2)

    def test_hoogste_voorscore_wint_het_cluster(self):
        zwak = maak_item("Model X uitgebracht door lab", "https://zwak.example.com/1")
        sterk = maak_item("Model X uitgebracht door het lab", "https://sterk.example.com/1")
        zwak.voorscore, sterk.voorscore = 1.0, 9.0
        over = dedupe.ontdubbel([zwak, sterk])
        self.assertEqual(len(over), 1)
        self.assertEqual(over[0].url, "https://sterk.example.com/1")


DATUM = date(2026, 7, 29)


def maak_editie(items, **kw) -> Editie:
    return Editie(datum=DATUM, items=items, **kw)


def fixture_editie() -> Editie:
    items = score.scoor(_laad_fixtures(PROJECT / "fixtures" / "kandidaten.json"), CONFIG)
    return rank.kies_heuristisch(items, CONFIG, DATUM)


class TestRender(unittest.TestCase):
    def setUp(self):
        self.editie = fixture_editie()

    def test_datum_in_het_nederlands(self):
        self.assertEqual(render.datum_nl(DATUM), "woensdag 29 juli 2026")

    def test_json_is_geldig(self):
        data = json.loads(render.naar_json(self.editie))
        self.assertEqual(data["datum"], "2026-07-29")
        self.assertEqual(len(data["items"]), 6)

    def test_json_rondreis_behoudt_de_editie(self):
        self.editie.toepassing = Toepassing(
            titel="Zet dit vandaag aan", intro="Kost vijf minuten.",
            stappen=["Eén", "Twee", "Drie"], niet_doen="Niets installeren.", tijd="5 min")
        self.editie.voor_bedrijven = "Voor mkb'ers met een klantenbestand."
        terug = Editie.from_dict(json.loads(render.naar_json(self.editie)))
        self.assertEqual(terug.datum, DATUM)
        self.assertEqual(terug.toepassing.stappen, ["Eén", "Twee", "Drie"])
        self.assertEqual(terug.voor_bedrijven, self.editie.voor_bedrijven)
        self.assertEqual([i.kop for i in terug.items], [i.kop for i in self.editie.items])

    def test_markdown_bevat_alle_koppen(self):
        md = render.naar_markdown(self.editie)
        for s in self.editie.items:
            self.assertIn(s.kop, md)

    def test_datum_van_de_gebeurtenis_wordt_getoond(self):
        self.assertEqual(render.kort_datum("2026-07-27"), "27 juli")
        self.assertEqual(render.kort_datum("2026-07"), "juli")
        # Onparseerbare invoer mag niet crashen maar blijft zichtbaar.
        self.assertEqual(render.kort_datum("binnenkort"), "binnenkort")

    def test_kanttekening_verschijnt_alleen_als_die_er_is(self):
        met = Selectie(kop="k", kern="s", wat="w", waarom="d", url="https://a.nl",
                       bron="b", categorie="model", kanttekening="Eén bron.")
        zonder = Selectie(kop="k", kern="s", wat="w", waarom="d", url="https://a.nl",
                          bron="b", categorie="model")
        self.assertIn("Kanttekening", render.naar_markdown(maak_editie([met])))
        self.assertNotIn("Kanttekening", render.naar_markdown(maak_editie([zonder])))

    def test_kernzin_staat_in_beide_formaten(self):
        s = Selectie(kop="Kop", kern="Dit is de kernzin zonder jargon.", wat="w",
                     waarom="d", url="https://a.nl", bron="b", categorie="model")
        editie = maak_editie([s])
        self.assertIn("Dit is de kernzin zonder jargon.", render.naar_markdown(editie))
        self.assertIn("Dit is de kernzin zonder jargon.", render.naar_html(editie))

    def test_mail_linkt_door_naar_de_eigen_pagina(self):
        s = Selectie(kop="Toezichthouder tikt drie banken op de vingers", kern="k",
                     wat="w", waarom="d", url="https://bron.nl/a", bron="b")
        html = render.naar_html(maak_editie([s]))
        self.assertIn(
            "https://aibulletin.nl/2026-07-29/toezichthouder-tikt-drie-banken-op-de-vingers",
            html)

    def test_intro_is_optioneel(self):
        md_met = render.naar_markdown(maak_editie(self.editie.items,
                                                  intro="Vandaag twee thema's."))
        md_zonder = render.naar_markdown(self.editie)
        self.assertIn("Vandaag twee thema's.", md_met)
        self.assertNotIn("Vandaag twee thema's.", md_zonder)

    def test_leestijd_schaalt_mee_en_is_minstens_een_minuut(self):
        kort = maak_editie([Selectie(kop="k", kern="s", wat="w", waarom="d",
                                     url="https://a.nl", bron="b")])
        lang = maak_editie([Selectie(kop="k", kern="s", wat="w", waarom="woord " * 400,
                                     url="https://a.nl", bron="b")])
        self.assertEqual(render.leestijd(kort), 1)
        self.assertGreater(render.leestijd(lang), render.leestijd(kort))
        self.assertIn("minuten lezen", render.naar_markdown(lang))

    def test_toepassing_verschijnt_in_beide_formaten(self):
        editie = maak_editie(self.editie.items, toepassing=Toepassing(
            titel="Controleer je eigen chatbot", intro="Kost vijf minuten.",
            stappen=["Open de bot", "Stel de vraag", "Noteer het antwoord"],
            niet_doen="Je hoeft geen software te kopen.", tijd="5 min"))
        for uitvoer in (render.naar_markdown(editie), render.naar_html(editie)):
            self.assertIn("Vandaag toepassen", uitvoer)
            self.assertIn("Controleer je eigen chatbot", uitvoer)
            self.assertIn("Noteer het antwoord", uitvoer)
            self.assertIn("níét hoeft te doen", uitvoer)

    def test_toepassing_staat_boven_de_zes(self):
        """Het kenmerk van dit product hoort niet onder zes nieuwsberichten."""
        editie = maak_editie(self.editie.items, toepassing=Toepassing(
            titel="Controleer je eigen chatbot", intro="Vijf minuten.",
            stappen=["Een", "Twee", "Drie"], tijd="5 min"))
        for uitvoer in (render.naar_markdown(editie), render.naar_html(editie)):
            self.assertLess(uitvoer.index("Vandaag toepassen"),
                            uitvoer.index(editie.items[0].kop),
                            "de toepassing staat ónder het eerste bericht")

    def test_methodeverantwoording_staat_in_beide_formaten(self):
        for uitvoer in (render.naar_markdown(self.editie), render.naar_html(self.editie)):
            self.assertIn("Hoe deze editie tot stand kwam".lower(), uitvoer.lower())
            self.assertIn("correcties", uitvoer.lower())

    def test_html_ontsnapt_gebruikersinhoud(self):
        gevaarlijk = maak_editie([Selectie(
            kop="<script>alert(1)</script>", kern="k", wat="a", waarom="b",
            url="https://example.com", bron="x", categorie="model",
        )])
        html = render.naar_html(gevaarlijk)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


class TestHeuristischeSelectie(unittest.TestCase):
    def test_levert_gevraagd_aantal(self):
        self.assertEqual(len(fixture_editie().items), 6)

    def test_geen_dubbele_urls(self):
        urls = [s.url for s in fixture_editie().items]
        self.assertEqual(len(urls), len(set(urls)))

    def test_neemt_geen_brontekst_over(self):
        """Auteursrecht: een samenvatting van de uitgever mag niet in de editie."""
        items = score.scoor(_laad_fixtures(PROJECT / "fixtures" / "kandidaten.json"), CONFIG)
        samenvattingen = {i.samenvatting for i in items if i.samenvatting}
        for s in rank.kies_heuristisch(items, CONFIG, DATUM).items:
            self.assertNotIn(s.wat, samenvattingen)


class TestHistorie(unittest.TestCase):
    """Het geheugen tussen edities — zonder dit stuur je dagen achtereen hetzelfde."""

    def _archief(self, tmp: Path, datum: date, items: list[dict]) -> Path:
        map_ = tmp / "edities"
        map_.mkdir(exist_ok=True)
        (map_ / f"{datum.isoformat()}.json").write_text(
            json.dumps({"datum": datum.isoformat(), "items": items}), encoding="utf-8")
        return map_

    def test_zelfde_url_wordt_geweerd(self):
        with tempfile.TemporaryDirectory() as tmp:
            map_ = self._archief(Path(tmp), date(2026, 7, 28), [
                {"kop": "Mistral brengt nieuw model uit", "url": "https://a.nl/mistral"}])
            h = historie.laad(map_, vandaag=DATUM)
            item = maak_item("Heel andere titel", "https://a.nl/mistral")
            self.assertEqual(historie.oordeel(item, h)[0], "blokkeer")

    def test_url_varianten_tellen_als_dezelfde(self):
        with tempfile.TemporaryDirectory() as tmp:
            map_ = self._archief(Path(tmp), date(2026, 7, 28), [
                {"kop": "K", "url": "https://www.a.nl/mistral/?utm_source=mail"}])
            h = historie.laad(map_, vandaag=DATUM)
            item = maak_item("K", "https://a.nl/mistral")
            self.assertEqual(historie.oordeel(item, h)[0], "blokkeer")

    def test_gelijkende_kop_via_andere_bron_wordt_gestraft(self):
        """Het scenario waarvoor dit bestaat: maandag Tweakers, woensdag Emerce."""
        with tempfile.TemporaryDirectory() as tmp:
            map_ = self._archief(Path(tmp), date(2026, 7, 28), [{
                "kop": "Autoriteit Persoonsgegevens publiceert leidraad voor gezichtsherkenning",
                "url": "https://tweakers.net/1"}])
            h = historie.laad(map_, vandaag=DATUM)
            item = maak_item(
                "Autoriteit Persoonsgegevens publiceert een leidraad voor gezichtsherkenning",
                "https://emerce.nl/2")
            self.assertEqual(historie.oordeel(item, h)[0], "straf")

    def test_ander_onderwerp_blijft_ongemoeid(self):
        with tempfile.TemporaryDirectory() as tmp:
            map_ = self._archief(Path(tmp), date(2026, 7, 28), [
                {"kop": "Mistral brengt nieuw model uit", "url": "https://a.nl/1"}])
            h = historie.laad(map_, vandaag=DATUM)
            item = maak_item("DNB waarschuwt banken voor cyberdreiging", "https://b.nl/2")
            self.assertIsNone(historie.oordeel(item, h))

    def test_editie_van_vandaag_blokkeert_zichzelf_niet(self):
        """Anders levert een herdraai van dezelfde dag een lege editie op."""
        with tempfile.TemporaryDirectory() as tmp:
            map_ = self._archief(Path(tmp), DATUM, [
                {"kop": "Mistral brengt nieuw model uit", "url": "https://a.nl/1"}])
            h = historie.laad(map_, vandaag=DATUM)
            self.assertEqual(len(h), 0)

    def test_te_oude_editie_telt_niet_meer_mee(self):
        with tempfile.TemporaryDirectory() as tmp:
            map_ = self._archief(Path(tmp), date(2026, 1, 1), [
                {"kop": "Oud bericht", "url": "https://a.nl/oud"}])
            self.assertEqual(len(historie.laad(map_, dagen=30, vandaag=DATUM)), 0)

    def test_kapot_archiefbestand_stopt_de_editie_niet(self):
        with tempfile.TemporaryDirectory() as tmp:
            map_ = Path(tmp) / "edities"
            map_.mkdir()
            (map_ / "2026-07-28.json").write_text("{kapot", encoding="utf-8")
            self.assertEqual(len(historie.laad(map_, vandaag=DATUM)), 0)

    def test_ontbrekende_map_geeft_lege_historie(self):
        self.assertEqual(len(historie.laad(Path("/bestaat/niet"))), 0)

    def test_pas_toe_weert_en_straft(self):
        with tempfile.TemporaryDirectory() as tmp:
            map_ = self._archief(Path(tmp), date(2026, 7, 28), [
                {"kop": "Mistral brengt nieuw model uit", "url": "https://a.nl/1"}])
            h = historie.laad(map_, vandaag=DATUM)

            geweerd = maak_item("Wat dan ook", "https://a.nl/1")
            gestraft = maak_item("Mistral brengt een nieuw model uit", "https://b.nl/2")
            vrij = maak_item("DNB waarschuwt banken", "https://c.nl/3")
            for i in (geweerd, gestraft, vrij):
                i.voorscore = 10.0

            over = historie.pas_toe([geweerd, gestraft, vrij], h, CONFIG)
            self.assertEqual({i.url for i in over}, {gestraft.url, vrij.url})
            self.assertLess(gestraft.voorscore, vrij.voorscore)
            self.assertEqual(gestraft.metriek["eerder_gepubliceerd"], "2026-07-28")


class TestOndergrens(unittest.TestCase):
    """Een editie mag korter zijn dan zes. Vulling is duurder dan stilte."""

    def _items(self, scores: list[float]) -> list[Item]:
        items = []
        for n, s in enumerate(scores):
            item = maak_item(f"Bericht {n} over een onderwerp", f"https://x.nl/{n}",
                             bron=f"bron{n}")
            item.voorscore = s
            items.append(item)
        return items

    def test_zwakke_staart_valt_af(self):
        # Drie sterke items, drie die ver onder de kop van het veld zitten.
        editie = rank.kies_heuristisch(self._items([10, 9, 8, 1, 0.5, 0.2]), CONFIG, DATUM)
        self.assertEqual(len(editie.items), 3)

    def test_sterke_dag_levert_gewoon_zes(self):
        editie = rank.kies_heuristisch(self._items([10, 9, 9, 8, 8, 7, 7]), CONFIG, DATUM)
        self.assertEqual(len(editie.items), 6)

    def test_minimum_wordt_gehaald_ook_als_alles_zwak_is(self):
        """Eén uitschieter met een zwakke rest mag geen editie van één opleveren."""
        editie = rank.kies_heuristisch(self._items([10, 0.1, 0.1, 0.1]), CONFIG, DATUM)
        self.assertGreaterEqual(len(editie.items), 1)

    def test_schema_bevat_geen_sleutels_die_de_api_weigert(self):
        """De fout die run 30541853787 rood maakte, in één regel vastgelegd.

        De API antwoordde met 400: "For 'array' type, property 'maxItems' is
        not supported". Geen enkele van de 120 tests kon dat zien, want het
        schema werd nooit tegen de API gehouden. Deze test kan dat evenmin —
        wat hij wel doet is voorkomen dat de sleutel er ooit weer in sluipt.
        """
        self.assertEqual(rank.verboden_schemasleutels(rank.SCHEMA), [])
        self.assertEqual(rank.verboden_schemasleutels(rank.bouw_schema(1, 6)), [])
        # En de controle zelf moet wél aanslaan, anders bewijst hij niets.
        self.assertEqual(
            rank.verboden_schemasleutels({"a": {"b": {"maxItems": 6}}}),
            ["a.b.maxItems"])

    def test_bouw_schema_geeft_een_eigen_kopie(self):
        """Anders lekt de ene run in de andere."""
        schema = rank.bouw_schema()
        schema["properties"]["items"]["type"] = "aangetast"
        self.assertEqual(rank.SCHEMA["properties"]["items"]["type"], "array")


class TestKeuring(unittest.TestCase):
    """Eén poort waar alles doorheen moet — beide routes, niet alleen de automatische.

    Elke test hieronder is een fout die deze week daadwerkelijk is gepubliceerd
    omdat de handgeschreven route geen enkele controle had.
    """

    def echt(self, naam: str = "2026-07-29") -> Editie:
        pad = PROJECT / "redactie" / f"{naam}-selectie.json"
        return Editie.from_dict(json.loads(pad.read_text(encoding="utf-8")))

    def test_te_lange_duiding_wordt_gezien(self):
        editie = self.echt()
        editie.items[0].waarom = "woord " * 80
        self.assertTrue(any("duiding" in b.wat for b in keuring.keur(editie)))

    def test_abstracte_kop_wordt_gezien(self):
        editie = self.echt()
        editie.items[0].kop = "De AI-wet is uitgesteld en gaat vandaag gewoon in"
        self.assertTrue(any("abstract onderwerp" in b.wat for b in keuring.keur(editie)))

    def test_zondagsstuk_zonder_auteur_blokkeert(self):
        editie = self.echt("2026-08-02")
        editie.beschouwing.auteur = ""
        blok = keuring.blokkades(keuring.keur(editie))
        self.assertTrue(any("geen auteur" in b.wat for b in blok))

    def test_leeg_verplicht_veld_blokkeert(self):
        editie = self.echt()
        editie.items[0].bron = ""
        self.assertTrue(any(b.wat == "leeg veld: bron" for b in keuring.blokkades(keuring.keur(editie))))

    def test_dubbele_bron_blokkeert(self):
        editie = self.echt()
        editie.items[1].url = editie.items[0].url
        self.assertTrue(any("twee keer" in b.wat for b in keuring.blokkades(keuring.keur(editie))))

    def test_placeholders_blokkeren_alleen_streng(self):
        """De heuristische terugval mag placeholders opleveren; handwerk niet."""
        items = score.scoor(_laad_fixtures(PROJECT / "fixtures" / "kandidaten.json"), CONFIG)
        editie = rank.kies_heuristisch(items, CONFIG, DATUM)
        editie.onderwerp = "Een onderwerpregel van goede lengte"
        soepel = keuring.blokkades(keuring.keur(editie, streng=False))
        streng = keuring.blokkades(keuring.keur(editie, streng=True))
        self.assertGreater(len(streng), len(soepel))

    def test_handgeschreven_route_weigert_te_publiceren(self):
        """De route waarlangs elke redactionele fout binnenkwam, blokkeert nu."""
        with tempfile.TemporaryDirectory() as tmp:
            editie = self.echt("2026-08-02")
            editie.beschouwing.auteur = ""
            pad = Path(tmp) / "kapot.json"
            pad.write_text(render.naar_json(editie), encoding="utf-8")
            with self.assertRaises(pipeline.KeuringsFout):
                pipeline.render_selectie(pad, Path(tmp) / "uit")

    def test_automatische_route_blokkeert_niet_maar_rapporteert_wel(self):
        """De ochtendmail moet de deur uit; de bevindingen gaan mee naar de proefmail."""
        items = _laad_fixtures(PROJECT / "fixtures" / "kandidaten.json")
        with tempfile.TemporaryDirectory() as tmp:
            resultaat = pipeline.draai(CONFIG, uitvoermap=Path(tmp), vandaag=DATUM,
                                       heuristisch=True, vooraf_verzameld=items)
            self.assertTrue(resultaat.bestanden, "editie is niet geschreven")
            self.assertTrue(resultaat.bevindingen, "keuring rapporteerde niets")

    def test_wat_gepubliceerd_wordt_is_schoon(self):
        """Bewaakt edities/ — dát is wat de site bouwt, niet redactie/.

        En met een kanarie erbij: een test die alleen op een lege lijst
        controleert, slaagt ook als de keuring helemaal stuk is.
        """
        gepubliceerd = sorted((PROJECT / "edities").glob("*.json"))
        self.assertTrue(gepubliceerd, "geen gepubliceerde edities gevonden")
        for pad in gepubliceerd:
            editie = Editie.from_dict(json.loads(pad.read_text(encoding="utf-8")))
            blok = keuring.blokkades(keuring.keur(editie, streng=True))
            self.assertEqual(blok, [], f"{pad.name}: {[str(b) for b in blok]}")

            kapot = Editie.from_dict(json.loads(pad.read_text(encoding="utf-8")))
            kapot.items and setattr(kapot.items[0], "bron", "")
            kapot.onderwerp = ""
            self.assertTrue(keuring.blokkades(keuring.keur(kapot, streng=True)),
                            "de keuring vindt niets op een kapotte editie — hij is dood")

    def test_de_site_publiceert_geen_afgekeurde_editie(self):
        """De route naar de lezer. Zonder deze controle helpt blokkeren elders niet."""
        with tempfile.TemporaryDirectory() as tmp:
            edities, uit = Path(tmp) / "edities", Path(tmp) / "site"
            edities.mkdir()
            editie = self.echt()
            editie.items[0].bron = ""
            (edities / f"{editie.stam}.json").write_text(
                render.naar_json(editie), encoding="utf-8")
            with self.assertRaises(site.OngekeurdeEditie):
                site.bouw(edities, uit, {})


class TestZondagsstuk(unittest.TestCase):
    """Zes dagen machinewerk, één dag mensenwerk — en dat moet zichtbaar zijn."""

    ZONDAG = PROJECT / "redactie" / "2026-08-02-selectie.json"

    def editie(self) -> Editie:
        return Editie.from_dict(json.loads(self.ZONDAG.read_text(encoding="utf-8")))

    def test_de_auteur_staat_erbij(self):
        """Een stuk met een mening zonder naam is het slechtste van twee werelden."""
        b = self.editie().beschouwing
        self.assertEqual(b.auteur, "Kees Cornelius")
        for uitvoer in (render.naar_markdown(self.editie()), render.naar_html(self.editie())):
            self.assertIn("Kees Cornelius", uitvoer)

    def test_tussenkoppen_worden_koppen(self):
        b = Beschouwing(titel="T", kern="k", auteur="A",
                        alineas=["# Een tussenkop", "Gewone tekst."])
        html = render.naar_html(maak_editie([], beschouwing=b))
        self.assertIn("<h3", html)
        self.assertNotIn("# Een tussenkop", html)
        self.assertIn("Een tussenkop", html)

    def test_woorden_telt_de_tussenkoppen_niet_mee(self):
        b = Beschouwing(titel="T", kern="k", alineas=["# Kop hier", "een twee drie vier"])
        self.assertEqual(b.woorden, 4)

    def test_essay_telt_mee_in_de_leestijd(self):
        """Anders belooft de zondagseditie één minuut voor een stuk van 400 woorden."""
        leeg = maak_editie([])
        met = maak_editie([], beschouwing=self.editie().beschouwing)
        self.assertGreater(render.leestijd(met), render.leestijd(leeg))

    def test_rondreis_door_json(self):
        terug = Editie.from_dict(json.loads(render.naar_json(self.editie())))
        self.assertEqual(terug.beschouwing.auteur, "Kees Cornelius")
        self.assertEqual(terug.beschouwing.alineas, self.editie().beschouwing.alineas)

    def test_editie_zonder_beschouwing_blijft_werken(self):
        editie = maak_editie([])
        self.assertIsNone(editie.beschouwing)
        self.assertNotIn("Zondagsstuk", render.naar_html(editie))

    def test_eigen_pagina_op_de_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            edities, uit = Path(tmp) / "edities", Path(tmp) / "site"
            edities.mkdir()
            editie = self.editie()
            (edities / f"{editie.stam}.json").write_text(
                render.naar_json(editie), encoding="utf-8")
            # Het stuk is van 2 augustus; zonder die datum houdt bouw() het
            # terecht tegen als toekomstige editie.
            site.bouw(edities, uit, vandaag=editie.datum)
            pagina = uit / editie.stam / editie.beschouwing.slug / "index.html"
            self.assertTrue(pagina.exists(), "het zondagsstuk heeft geen eigen pagina")
            html = pagina.read_text(encoding="utf-8")
            self.assertIn("Kees Cornelius", html)
            self.assertIn("is een mening, geen", html)


class TestHerkomstVanCijfers(unittest.TestCase):
    """Beslissing 20: elk cijfer heeft een herkomst, of het bericht gaat eruit.

    Onder elke editie staat de belofte. Op 30 juli stond "900 miljoen wekelijkse
    gebruikers van ChatGPT" zonder kanttekening terwijl vergelijkbare cijfers er
    wél een kregen. Zo'n inconsequentie maakt de belofte onbetrouwbaar, en de
    belofte is het product.
    """

    def bericht(self, wat: str, kanttekening: str = "") -> Selectie:
        return Selectie(
            kop="Een kop die iets zegt over wat er is gebeurd",
            kern="De kern van het bericht.", wat=wat,
            waarom="Wat het voor je werk betekent.",
            url="https://example.com/x", bron="Bron", categorie="bedrijf",
            datum="2026-07-30", kanttekening=kanttekening)

    def test_het_cijfer_van_30_juli_wordt_nu_gevangen(self):
        s = self.bericht("Daarmee kunnen de 900 miljoen wekelijkse gebruikers "
                         "van ChatGPT bij de diensten van Bolt.")
        self.assertEqual(keuring.cijfers_zonder_herkomst(s), ["900 miljoen"])

    def test_soorten_cijfers_die_een_herkomst_nodig_hebben(self):
        for tekst, verwacht in [
            ("Van de instellingen stelt 44 procent die eis.", "44 procent"),
            ("Een foutmarge van 0,0041%.", "0,0041%"),
            ("De EU legt 10 miljard euro neer.", "10 miljard"),
            ("Het rapport telt 3.700 pagina's.", "3.700"),
            ("Ongeveer 1 op de 24.000 teksten.", "1 op de 24"),
        ]:
            with self.subTest(tekst=tekst):
                gevonden = keuring.cijfers_zonder_herkomst(self.bericht(tekst))
                self.assertTrue(any(verwacht in x for x in gevonden),
                                f"{verwacht!r} niet gevonden in {gevonden}")

    def test_een_kanttekening_lost_het_op(self):
        s = self.bericht("Van de instellingen stelt 44 procent die eis.",
                         kanttekening="Het cijfer komt uit het eigen onderzoek "
                                      "van de leverancier.")
        self.assertEqual(keuring.cijfers_zonder_herkomst(s), [])

    def test_jaartallen_en_wetsartikelen_tellen_niet_mee(self):
        """Een verwijzing is geen bewering over de wereld."""
        s = self.bericht("Artikel 50 lid 2 gaat in 2026 in, na uitstel tot 2027.")
        self.assertEqual(keuring.cijfers_zonder_herkomst(s), [])

    def test_natelbare_aantallen_tellen_niet_mee(self):
        """"Zeven fabrieken" is in de bron na te tellen; een percentage niet."""
        s = self.bericht("De EU wil 7 gigafabrieken en koos 3 bedrijven.")
        self.assertEqual(keuring.cijfers_zonder_herkomst(s), [])

    def test_het_is_een_blokkade_en_geen_waarschuwing(self):
        """Een waarschuwing had dit precies zo laten passeren als op 30 juli."""
        editie = maak_editie([self.bericht("Ruim 84 procent van de markt.")],
                             onderwerp="Een onderwerpregel van de juiste lengte")
        blok = keuring.blokkades(keuring.keur(editie))
        self.assertTrue([x for x in blok if "herkomst" in x.wat])

    def test_alle_gepubliceerde_edities_voldoen(self):
        for pad in sorted((PROJECT / "edities").glob("*.json")):
            with self.subTest(editie=pad.name):
                editie = Editie.from_dict(json.loads(pad.read_text(encoding="utf-8")))
                for n, s in enumerate(editie.items, 1):
                    self.assertEqual(
                        keuring.cijfers_zonder_herkomst(s), [],
                        f"{pad.name} bericht {n} heeft een cijfer zonder herkomst")


class TestBronnenlijst(unittest.TestCase):
    """Beslissing 21: elke editie publiceert zijn bronnen, bij naam.

    Grond: ACM FAccT 2026 — een AI-melding kost vertrouwen, een uitgebreide
    verantwoording maakt het erger, en het publiceren van de gebruikte bronnen
    doet het effect grotendeels teniet. De oude verantwoording deed dus precies
    het verkeerde.
    """

    def editie(self) -> Editie:
        return maak_editie(
            [], onderwerp="Een onderwerpregel van de juiste lengte",
            kandidaten=88, bronlijst=["Emerce", "GitHub", "Tweakers"])

    def test_de_bronnen_staan_er_bij_naam_in(self):
        tekst = render.methodeverantwoording(self.editie())
        for bron in ("Emerce", "GitHub", "Tweakers"):
            self.assertIn(bron, tekst)
        self.assertIn("88", tekst)

    def test_de_verantwoording_blijft_kort(self):
        """Een langere verantwoording verlaagt het vertrouwen juist — zie boven."""
        zinnen = render.methodeverantwoording(self.editie()).count(". ")
        self.assertLessEqual(zinnen, 4, "de verantwoording dijt weer uit")

    def test_een_oude_editie_zonder_namen_valt_terug_op_het_aantal(self):
        oud = maak_editie([], onderwerp="Een onderwerpregel van de juiste lengte",
                          kandidaten=214, bronnen=31)
        tekst = render.methodeverantwoording(oud)
        self.assertIn("31 bronnen", tekst)

    def test_de_lijst_overleeft_een_rondje_json(self):
        terug = Editie.from_dict(json.loads(render.naar_json(self.editie())))
        self.assertEqual(terug.bronlijst, ["Emerce", "GitHub", "Tweakers"])
        self.assertEqual(terug.bronnen, 3, "het aantal loopt uit de pas met de lijst")

    def test_de_pijplijn_vult_de_lijst(self):
        items = _laad_fixtures(PROJECT / "fixtures" / "kandidaten.json")
        with tempfile.TemporaryDirectory() as tmp:
            resultaat = pipeline.draai(
                CONFIG, uitvoermap=Path(tmp), vandaag=DATUM,
                heuristisch=True, vooraf_verzameld=items)
            self.assertTrue(resultaat.editie.bronlijst)
            self.assertEqual(resultaat.editie.bronnen,
                             len(resultaat.editie.bronlijst))


class TestToekomstigeEdities(unittest.TestCase):
    """Een stuk van aanstaande zondag hoort donderdag niet op de voorpagina.

    Het zondagsstuk wordt vooruit geschreven en ligt dus in `edities/` vóór de
    dag zelf. De site sorteert op datum en toonde daardoor op 30 juli de editie
    van 2 augustus als nieuwste. Voor een nieuwssite is dat geen
    schoonheidsfout maar een onwaarheid over wat er vandaag speelt.
    """

    def _map(self, tmp: Path, *datums: date) -> Path:
        edities = tmp / "edities"
        edities.mkdir()
        for d in datums:
            editie = Editie(
                datum=d, onderwerp=f"Editie van {d.isoformat()} met genoeg tekens",
                items=[Selectie(kop="Een kop die ergens over gaat en je iets vertelt",
                                kern="De kern.", wat="Wat er gebeurd is.",
                                waarom="Wat het voor je betekent.",
                                url=f"https://example.com/{d.isoformat()}",
                                bron="Bron", categorie="bedrijf", datum=d.isoformat())])
            (edities / f"{editie.stam}.json").write_text(
                render.naar_json(editie), encoding="utf-8")
        return edities

    def test_een_editie_van_later_komt_niet_op_de_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            edities = self._map(tmp, date(2026, 7, 30), date(2026, 8, 2))
            site.bouw(edities, tmp / "site", keuren=False, vandaag=date(2026, 7, 30))
            self.assertTrue((tmp / "site" / "2026-07-30").exists())
            self.assertFalse((tmp / "site" / "2026-08-02").exists(),
                             "editie van later staat al op de site")

    def test_de_homepage_toont_de_editie_van_vandaag(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            edities = self._map(tmp, date(2026, 7, 30), date(2026, 8, 2))
            site.bouw(edities, tmp / "site", keuren=False, vandaag=date(2026, 7, 30))
            homepage = (tmp / "site" / "index.html").read_text(encoding="utf-8")
            self.assertIn("2026-07-30", homepage)
            self.assertNotIn("2026-08-02", homepage)

    def test_op_de_dag_zelf_verschijnt_hij_alsnog(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            edities = self._map(tmp, date(2026, 7, 30), date(2026, 8, 2))
            site.bouw(edities, tmp / "site", keuren=False, vandaag=date(2026, 8, 2))
            self.assertTrue((tmp / "site" / "2026-08-02").exists())


class TestUitgever(unittest.TestCase):
    """Een nieuwssite die op betrouwbaarheid concurreert kan niet anoniem zijn."""

    VOLLEDIG = {"uitgever": {
        "naam": "Testuitgever B.V.", "handelsnaam": "AI Bulletin",
        "adres": "Teststraat 1", "postcode": "1000 AA", "plaats": "Amsterdam",
        "land": "Nederland", "kvk": "12345678", "btw": "NL001234567B01",
        "email": "post@example.nl", "correcties": "correcties@example.nl"}}

    def test_lege_config_blokkeert_publicatie(self):
        blokkades = site.controleer_publicatiegereed({})
        self.assertTrue(blokkades)
        self.assertTrue(any("kvk" in b for b in blokkades))

    def test_de_echte_config_is_publicatiegereed(self):
        """Sinds 30 juli zijn de uitgeversgegevens bekend en mag de site live.

        Deze test stond hiervóór omgekeerd: hij bewaakte dat er níét live werd
        gegaan zolang de gegevens ontbraken. Nu bewaakt hij het omgekeerde —
        dat ze niet stilletjes weer uit config.yaml verdwijnen.
        """
        self.assertEqual(site.controleer_publicatiegereed(CONFIG), [])

    def test_een_weggevallen_veld_blokkeert_de_echte_config_alsnog(self):
        """De poort moet blijven werken nu hij eenmaal open staat."""
        for veld in ("naam", "adres", "kvk", "email"):
            with self.subTest(veld=veld):
                kaal = {"uitgever": dict(CONFIG["uitgever"], **{veld: ""})}
                self.assertTrue(site.controleer_publicatiegereed(kaal),
                                f"leeg {veld} werd niet opgemerkt")

    def test_het_registratienummer_heet_niet_zomaar_kvk(self):
        """De uitgever is een Estse OÜ; "KvK-nummer" zou een onwaarheid zijn."""
        labels = [label for label, _ in site._uitgever_regels(CONFIG)]
        self.assertFalse([x for x in labels if x.startswith("KvK")],
                         f"colofon noemt een Estse registrikood een KvK-nummer: {labels}")
        self.assertTrue([x for x in labels if x.startswith("Registratienummer")])

    def test_volledige_gegevens_geven_groen_licht(self):
        self.assertEqual(site.controleer_publicatiegereed(self.VOLLEDIG), [])

    def test_ontbrekend_correctieadres_wordt_apart_gemeld(self):
        config = {"uitgever": dict(self.VOLLEDIG["uitgever"], correcties="", email="")}
        self.assertTrue(any("correctie" in b for b in site.controleer_publicatiegereed(config)))

    def test_email_dekt_het_correctieadres_af(self):
        config = {"uitgever": dict(self.VOLLEDIG["uitgever"], correcties="")}
        self.assertEqual(site.controleer_publicatiegereed(config), [])

    def test_colofon_toont_de_gegevens_en_geen_waarschuwing(self):
        html = site._colofon(self.VOLLEDIG).inhoud
        for verwacht in ("Testuitgever B.V.", "12345678", "NL001234567B01",
                         "correcties@example.nl", "Teststraat 1", "1000 AA Amsterdam"):
            self.assertIn(verwacht, html)
        self.assertNotIn("nog niet ingevuld", html)
        self.assertNotIn("niet compleet", html)

    def test_onvolledig_colofon_waarschuwt_zichtbaar(self):
        html = site._colofon({}).inhoud
        self.assertIn("nog niet ingevuld", html)
        self.assertIn("niet live", html)
        # Postcode en plaats delen één regel: samen één keer de melding.
        self.assertNotIn("— nog niet ingevuld — — nog niet ingevuld —", html)

    def test_deels_ingevulde_woonplaats_toont_wat_er_is(self):
        config = {"uitgever": {"plaats": "Rotterdam"}}
        self.assertIn("<td>Rotterdam</td>", site._colofon(config).inhoud)

    def test_privacy_noemt_de_verwerkingsverantwoordelijke(self):
        html = site._privacy(self.VOLLEDIG).inhoud
        self.assertIn("Testuitgever B.V.", html)
        self.assertIn("verwerkingsverantwoordelijke", html)
        self.assertIn("Autoriteit Persoonsgegevens", html)

    def test_verzendadres_ligt_vast_in_config(self):
        """De opdrachtgever wil elke editie ontvangen; dat mag niet wegvallen."""
        self.assertIn("kees@telemedia.es", CONFIG["verzending"]["altijd_naar"])

    def test_voorvertoning_wordt_niet_geindexeerd(self):
        """Een preview-URL die rankt, concurreert met de echte site."""
        with tempfile.TemporaryDirectory() as tmp:
            uit = self._bouw(Path(tmp), indexeerbaar=False)
            robots = (uit / "robots.txt").read_text(encoding="utf-8")
            self.assertIn("Disallow: /", robots)
            self.assertNotIn("Allow: /", robots)

    def test_productie_wordt_wel_geindexeerd_en_wijst_naar_de_sitemap(self):
        with tempfile.TemporaryDirectory() as tmp:
            uit = self._bouw(Path(tmp), indexeerbaar=True)
            robots = (uit / "robots.txt").read_text(encoding="utf-8")
            self.assertIn("Allow: /", robots)
            self.assertIn("aibulletin.nl/sitemap.xml", robots)

    def _bouw(self, tmp: Path, indexeerbaar: bool) -> Path:
        edities, uit = tmp / "edities", tmp / "public"
        edities.mkdir()
        editie = fixture_editie()
        (edities / f"{editie.stam}.json").write_text(
            render.naar_json(editie), encoding="utf-8")
        site.bouw(edities, uit, self.VOLLEDIG, indexeerbaar=indexeerbaar, keuren=False)
        return uit

    def test_beide_paginas_staan_in_de_gebouwde_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            edities, uit = Path(tmp) / "edities", Path(tmp) / "site"
            edities.mkdir()
            editie = fixture_editie()
            (edities / f"{editie.stam}.json").write_text(
                render.naar_json(editie), encoding="utf-8")
            site.bouw(edities, uit, self.VOLLEDIG, keuren=False)
            for pad in ("colofon/index.html", "privacy/index.html"):
                self.assertTrue((uit / pad).exists(), f"{pad} ontbreekt")
            # En vanaf elke pagina bereikbaar.
            self.assertIn('href="../colofon/"', (uit / "archief/index.html").read_text())


class TestSite(unittest.TestCase):
    def test_bouwt_alle_paginas(self):
        with tempfile.TemporaryDirectory() as tmp:
            edities, uit = Path(tmp) / "edities", Path(tmp) / "site"
            edities.mkdir()
            editie = fixture_editie()
            editie.toepassing = Toepassing(
                titel="Doe deze test", intro="Vijf minuten.",
                stappen=["Een", "Twee", "Drie"], tijd="5 min")
            (edities / f"{editie.stam}.json").write_text(
                render.naar_json(editie), encoding="utf-8")

            paden = site.bouw(edities, uit, keuren=False)
            self.assertTrue(paden)
            for verwacht in ("index.html", "stijl.css", "sitemap.xml",
                             "archief/index.html", "werkwijze/index.html",
                             f"{editie.stam}/index.html"):
                self.assertTrue((uit / verwacht).exists(), f"{verwacht} ontbreekt")
            # Elk bericht krijgt een eigen pagina — dat is waar de mail naartoe linkt.
            for item in editie.items:
                self.assertTrue((uit / editie.stam / item.slug / "index.html").exists())

    def test_lege_map_is_een_fout(self):
        """Liever hard falen dan een lege site over de bestaande heen publiceren."""
        with tempfile.TemporaryDirectory() as tmp:
            edities, uit = Path(tmp) / "edities", Path(tmp) / "site"
            edities.mkdir()
            with self.assertRaises(ValueError):
                site.bouw(edities, uit, keuren=False)

    def test_toepassing_staat_boven_de_zes_op_de_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            edities, uit = Path(tmp) / "edities", Path(tmp) / "site"
            edities.mkdir()
            editie = fixture_editie()
            editie.toepassing = Toepassing(
                titel="Doe deze test", intro="Vijf minuten.",
                stappen=["Een", "Twee", "Drie"], tijd="5 min")
            (edities / f"{editie.stam}.json").write_text(
                render.naar_json(editie), encoding="utf-8")
            site.bouw(edities, uit, keuren=False)

            for pad in ("index.html", f"{editie.stam}/index.html"):
                html = (uit / pad).read_text(encoding="utf-8")
                self.assertLess(html.index("Vandaag toepassen"),
                                html.index(editie.items[0].kop),
                                f"{pad}: de toepassing staat ónder de berichten")

    def test_de_belofte_gaat_over_doen_niet_over_nieuws(self):
        """Het ene kenmerk is 'toepasbaar'; de homepage moet dat zeggen."""
        self.assertIn("doen", site.BESCHRIJVING)

    def test_slug_is_stabiel_en_url_veilig(self):
        s = Selectie(kop="ACM: 40% méér meldingen — “fors” gestegen", kern="k", wat="w",
                     waarom="d", url="https://a.nl", bron="b")
        self.assertEqual(s.slug, "acm-40-meer-meldingen-fors-gestegen")


class TestAudioScript(unittest.TestCase):
    def test_urls_en_afkortingen_worden_uitspreekbaar(self):
        from signaal import audio
        from signaal.model import Selectie

        script = audio.maak_script(
            [Selectie(kop="Nieuw LLM verschenen", kern="Een nieuw model.",
                      wat="Zie https://example.com/x voor details.",
                      waarom="Relevant voor de AVG.", url="https://example.com/x",
                      bron="test", categorie="model")],
            date(2026, 7, 29),
        )
        self.assertNotIn("https://", script)
        self.assertIn("el-el-em", script)
        self.assertIn("aa-vee-gee", script)


class TestKoptoets(unittest.TestCase):
    def test_vage_hoeveelheid_wordt_afgekeurd(self):
        # De kop die deze hele controle heeft uitgelokt.
        bezwaren = koptoets.controleer_kop(
            "Bijna driekwart van de aanvallen gebruikt een onbekend lek")
        self.assertTrue(any("vage hoeveelheid" in b for b in bezwaren))

    def test_specifieke_variant_komt_erdoor(self):
        self.assertEqual(
            koptoets.controleer_kop("DNB: bij 73% van de aanvallen bestond de update nog niet"),
            [],
        )

    def test_naamwoordstijl_en_uitroepteken(self):
        bezwaren = koptoets.controleer_kop("De invoering van de AI-wet begint!")
        self.assertTrue(any("naamwoordstijl" in b for b in bezwaren))
        self.assertIn("uitroepteken", bezwaren)

    def test_kop_zonder_houvast(self):
        bezwaren = koptoets.controleer_kop("het protocol werd opnieuw ontworpen")
        self.assertTrue(any("niets specifieks" in b for b in bezwaren))

    def test_tijdstip_telt_als_houvast(self):
        self.assertEqual(
            koptoets.controleer_kop("Zondag moet je chatbot zeggen dat hij een chatbot is"),
            [],
        )

    def test_abstract_onderwerp_zonder_lezer_wordt_afgekeurd(self):
        """De kop die deze controle heeft uitgelokt: waar, en zegt niemand iets."""
        bezwaren = koptoets.controleer_kop("De AI-wet is uitgesteld en gaat vandaag gewoon in")
        self.assertTrue(any("abstract onderwerp" in b for b in bezwaren))

    def test_abstractie_mag_als_de_lezer_erin_staat(self):
        self.assertEqual(
            koptoets.controleer_kop("De AI-wet is uitgesteld — behalve voor jouw chatbot"), [])

    def test_concrete_koppen_krijgen_geen_vals_alarm(self):
        for kop in ("DNB: bij 73% van de aanvallen bestond de update nog niet",
                    "Kimi K3 is gratis te downloaden en onbetaalbaar om te draaien",
                    "Drie bedrijven bezitten de AI's die jouw webshop moeten vinden"):
            self.assertEqual(koptoets.controleer_kop(kop), [], kop)

    def test_te_lange_kop(self):
        bezwaren = koptoets.controleer_kop("DNB " + "woord " * 20)
        self.assertTrue(any("te lang" in b for b in bezwaren))

    def test_de_kop_van_het_zondagsstuk_voldoet_ook(self):
        """Een essay heeft dezelfde koppentoets nodig als een nieuwsbericht."""
        for pad in sorted((PROJECT / "redactie").glob("*-selectie.json")):
            data = json.loads(pad.read_text(encoding="utf-8"))
            b = data.get("beschouwing")
            if b:
                self.assertEqual(koptoets.controleer_kop(b["titel"]), [],
                                 f"{pad.name}: zwakke kop boven het zondagsstuk")

    def test_gepubliceerde_edities_voldoen_aan_de_kopregels(self):
        """Elke editie in redactie/ moet door de eigen toets komen."""
        mappen = sorted((PROJECT / "redactie").glob("*-selectie.json"))
        self.assertTrue(mappen, "geen edities gevonden om te toetsen")
        for pad in mappen:
            data = json.loads(pad.read_text(encoding="utf-8"))
            fouten = koptoets.toets_editie([i["kop"] for i in data["items"]])
            self.assertEqual(fouten, {}, f"{pad.name} bevat zwakke koppen: {fouten}")

    def test_onderwerpregel_blijft_binnen_de_inboxbreedte(self):
        for pad in sorted((PROJECT / "redactie").glob("*-selectie.json")):
            data = json.loads(pad.read_text(encoding="utf-8"))
            onderwerp = data.get("onderwerp", "")
            if not onderwerp:
                continue
            # Op mobiel — goed voor het merendeel van de opens — wordt een
            # onderwerpregel na ongeveer 50 tekens afgekapt.
            self.assertLessEqual(len(onderwerp), 50, f"{pad.name}: onderwerp te lang")
            self.assertGreaterEqual(len(onderwerp), 20, f"{pad.name}: onderwerp te kort")
            self.assertNotIn("nieuwsbrief", onderwerp.lower())


class TestVolledigeRun(unittest.TestCase):
    def test_pijplijn_draait_offline_en_schrijft_bestanden(self):
        items = _laad_fixtures(PROJECT / "fixtures" / "kandidaten.json")
        with tempfile.TemporaryDirectory() as tmp:
            resultaat = pipeline.draai(
                CONFIG,
                uitvoermap=Path(tmp),
                vandaag=date(2026, 7, 29),
                heuristisch=True,
                vooraf_verzameld=items,
            )
            self.assertEqual(len(resultaat.selecties), 6)
            self.assertLess(resultaat.na_ontdubbelen, resultaat.kandidaten,
                            "fixtures bevatten een duplicaat dat niet is samengevoegd")
            for pad in resultaat.bestanden:
                self.assertTrue(pad.exists() and pad.stat().st_size > 0)


class TestVerzenden(unittest.TestCase):
    """De enige route naar de lezer die niet terug te draaien is.

    Een fout op de website herstel je met een commit. Een fout in een verzonden
    mail staat in andermans inbox. Vandaar dat hier meer wordt geweigerd dan
    elders, en dat elk van die weigeringen een test heeft.
    """

    EDITIE = PROJECT / "redactie" / "2026-07-29-selectie.json"

    def editie(self) -> Editie:
        return Editie.from_dict(json.loads(self.EDITIE.read_text(encoding="utf-8")))

    def config(self, **overschrijf) -> dict:
        basis_cfg = {
            "verzending": {"altijd_naar": ["kees@telemedia.es"]},
            "uitgever": dict(CONFIG.get("uitgever") or {}, email="post@aibulletin.nl"),
        }
        basis_cfg.update(overschrijf)
        return basis_cfg

    def test_de_mail_toont_de_kanttekeningen_die_hij_belooft(self):
        """De methodeverantwoording beloofde ze; de mail toonde er nul.

        Op de site en in de Markdown stonden ze wel. Zolang er niets verstuurd
        werd was dat een schoonheidsfout — met een verzendlaag is het een
        belofte die de deur uit gaat zonder wat erbij hoort.
        """
        editie = self.editie()
        mail = render.naar_html(editie)
        self.assertIn("kanttekening over de herkomst", mail)
        met_kanttekening = [s for s in editie.items if getattr(s, "kanttekening", "")]
        self.assertTrue(met_kanttekening, "testeditie heeft geen enkele kanttekening")
        for s in met_kanttekening:
            self.assertIn(html_module.escape(s.kanttekening), mail)

    def test_de_vaste_ontvanger_valt_nooit_weg(self):
        """Beslissing 12: elke editie gaat altijd naar kees@telemedia.es."""
        self.assertIn("kees@telemedia.es", verzenden.ontvangers(CONFIG))

    def test_proefdraai_bouwt_de_mail_maar_verstuurt_niets(self):
        v = verzenden.verstuur(self.editie(), self.config(), proef=True)
        self.assertFalse(v.verstuurd)
        self.assertEqual(v.ontvangers, ["kees@telemedia.es"])
        self.assertEqual(v.onderwerp, self.editie().onderwerp)
        self.assertEqual(len(v.berichten), 1)

    def test_de_mail_heeft_zowel_tekst_als_html(self):
        """Wie HTML uitzet hoort dezelfde editie te krijgen, geen lege mail."""
        bericht = verzenden.verstuur(self.editie(), self.config(), proef=True).berichten[0]
        soorten = {deel.get_content_type() for deel in bericht.walk()}
        self.assertIn("text/plain", soorten)
        self.assertIn("text/html", soorten)

    def test_het_sjabloonhaakje_staat_niet_meer_in_de_verstuurde_mail(self):
        """Zonder ESP vult niemand {{unsubscribe}} in; dan leest de lezer dat letterlijk."""
        bericht = verzenden.verstuur(self.editie(), self.config(), proef=True).berichten[0]
        html = bericht.get_body(("html",)).get_content()
        self.assertNotIn("{{unsubscribe}}", html)
        self.assertIn("Uitschrijven", html)

    def test_een_editie_met_een_blokkade_gaat_de_deur_niet_uit(self):
        """De poort van keuring.py geldt ook hier — juist hier."""
        kapot = self.editie()
        kapot.items[0].kop = "TODO nog een kop verzinnen"
        with self.assertRaises(verzenden.VerzendFout) as fout:
            verzenden.verstuur(kapot, self.config(), proef=True)
        self.assertIn("verzendgereed", str(fout.exception))

    def test_zonder_afzender_wordt_er_niets_verstuurd(self):
        leeg = self.config(uitgever={})
        with self.assertRaises(verzenden.VerzendFout) as fout:
            verzenden.verstuur(self.editie(), leeg, proef=True)
        self.assertIn("afzender", str(fout.exception))

    def test_zonder_ontvangers_wordt_er_niets_verstuurd(self):
        with self.assertRaises(verzenden.VerzendFout):
            verzenden.verstuur(self.editie(), self.config(verzending={}), proef=True)

    def test_naar_vreemden_mag_pas_als_de_uitgeversgegevens_er_zijn(self):
        """Bij één ontvanger — de uitgever zelf — beschermt een colofon niemand.

        Zodra er iemand anders meeleest gelden de identiteitsverplichtingen wel,
        en die moeten dan ergens vandaan komen.
        """
        # Expliciet een uitschrijflink meegeven, anders struikelt hij daar eerst
        # over en bewijst de test niet wat hij beweert.
        zonder_gegevens = self.config(uitgever={"naam": "X", "email": "x@x.nl"})
        with self.assertRaises(verzenden.VerzendFout) as fout:
            verzenden.verstuur(self.editie(), zonder_gegevens,
                               naar=["iemand@anders.nl"],
                               uitschrijflink="https://aibulletin.nl/uit", proef=True)
        self.assertIn("uitgeversgegevens", str(fout.exception))

    def test_naar_vreemden_mag_wel_met_volledige_gegevens(self):
        """Anders bewijst de vorige test alleen dat er íéts misgaat."""
        volledig = self.config(uitgever=dict(CONFIG["uitgever"]))
        v = verzenden.verstuur(self.editie(), volledig, naar=["iemand@anders.nl"],
                               uitschrijflink="https://aibulletin.nl/uit", proef=True)
        self.assertEqual(v.ontvangers, ["iemand@anders.nl"])

    def test_echt_versturen_gaat_via_de_verbinding_en_niet_verder(self):
        """Eén ontvanger, één send_message — geen stille tweede aanroep."""

        class NepSmtp:
            def __init__(self):
                self.verzonden = []

            def send_message(self, bericht):
                self.verzonden.append(bericht["To"])

        nep = NepSmtp()
        v = verzenden.verstuur(self.editie(), self.config(), smtp=nep)
        self.assertTrue(v.verstuurd)
        self.assertEqual(nep.verzonden, ["kees@telemedia.es"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
