"""Tests voor de offline delen van de pijplijn (alles behalve de LLM-jury)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from signaal import (  # noqa: E402
    dedupe, historie, koptoets, pipeline, rank, render, score, site,
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
        self.assertGreaterEqual(len(editie.items), 3)

    def test_schema_staat_een_kortere_editie_toe(self):
        schema = rank.bouw_schema(3, 6)
        self.assertEqual(schema["properties"]["items"]["minItems"], 3)
        self.assertEqual(schema["properties"]["items"]["maxItems"], 6)
        # Het origineel mag niet meeveranderen — anders lekt de ene run in de andere.
        self.assertEqual(rank.bouw_schema(1, 2)["properties"]["items"]["minItems"], 1)
        self.assertEqual(schema["properties"]["items"]["minItems"], 3)


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
            site.bouw(edities, uit)
            pagina = uit / editie.stam / editie.beschouwing.slug / "index.html"
            self.assertTrue(pagina.exists(), "het zondagsstuk heeft geen eigen pagina")
            html = pagina.read_text(encoding="utf-8")
            self.assertIn("Kees Cornelius", html)
            self.assertIn("is een mening, geen", html)


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

    def test_de_echte_config_is_nog_niet_publicatiegereed(self):
        """Bewaakt dat er niet per ongeluk live wordt gegaan zonder KvK-gegevens."""
        self.assertTrue(site.controleer_publicatiegereed(CONFIG))

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
        site.bouw(edities, uit, self.VOLLEDIG, indexeerbaar=indexeerbaar)
        return uit

    def test_beide_paginas_staan_in_de_gebouwde_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            edities, uit = Path(tmp) / "edities", Path(tmp) / "site"
            edities.mkdir()
            editie = fixture_editie()
            (edities / f"{editie.stam}.json").write_text(
                render.naar_json(editie), encoding="utf-8")
            site.bouw(edities, uit, self.VOLLEDIG)
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

            paden = site.bouw(edities, uit)
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
                site.bouw(edities, uit)

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
            site.bouw(edities, uit)

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

    def test_te_lange_kop(self):
        bezwaren = koptoets.controleer_kop("DNB " + "woord " * 20)
        self.assertTrue(any("te lang" in b for b in bezwaren))

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
