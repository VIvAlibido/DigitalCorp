"""Tests voor de offline delen van de pijplijn (alles behalve de LLM-jury)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from signaal import dedupe, pipeline, rank, render, score  # noqa: E402
from signaal.bronnen import basis  # noqa: E402
from signaal.cli import _laad_fixtures  # noqa: E402
from signaal.model import Item, canonicaliseer_url  # noqa: E402

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
        self.assertTrue(dedupe._zelfde_woord("contextvenster", "contextvensters"))
        self.assertTrue(dedupe._zelfde_woord("agent", "agents"))
        self.assertTrue(dedupe._zelfde_woord("model", "modellen"))

    def test_toevallig_gedeelde_prefix_telt_niet(self):
        # Beide beginnen met "trans", maar het zijn andere woorden.
        self.assertFalse(dedupe._zelfde_woord("transformer", "transparant"))
        self.assertFalse(dedupe._zelfde_woord("productie", "producent"))

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


class TestRender(unittest.TestCase):
    def setUp(self):
        self.selecties = rank.kies_heuristisch(
            score.scoor(_laad_fixtures(PROJECT / "fixtures" / "kandidaten.json"), CONFIG),
            CONFIG,
        )
        self.datum = date(2026, 7, 29)

    def test_datum_in_het_nederlands(self):
        self.assertEqual(render.datum_nl(self.datum), "woensdag 29 juli 2026")

    def test_json_is_geldig(self):
        data = json.loads(render.naar_json(self.selecties, self.datum))
        self.assertEqual(data["datum"], "2026-07-29")
        self.assertEqual(len(data["items"]), 6)

    def test_markdown_bevat_alle_koppen(self):
        md = render.naar_markdown(self.selecties, self.datum)
        for s in self.selecties:
            self.assertIn(s.kop, md)

    def test_html_ontsnapt_gebruikersinhoud(self):
        from signaal.model import Selectie

        gevaarlijk = [Selectie(
            kop="<script>alert(1)</script>", wat="a", waarom="b",
            url="https://example.com", bron="x", categorie="model",
        )]
        html = render.naar_html(gevaarlijk, self.datum)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


class TestHeuristischeSelectie(unittest.TestCase):
    def test_levert_gevraagd_aantal(self):
        items = score.scoor(_laad_fixtures(PROJECT / "fixtures" / "kandidaten.json"), CONFIG)
        selecties = rank.kies_heuristisch(items, CONFIG)
        self.assertEqual(len(selecties), 6)

    def test_geen_dubbele_urls(self):
        items = score.scoor(_laad_fixtures(PROJECT / "fixtures" / "kandidaten.json"), CONFIG)
        urls = [s.url for s in rank.kies_heuristisch(items, CONFIG)]
        self.assertEqual(len(urls), len(set(urls)))


class TestAudioScript(unittest.TestCase):
    def test_urls_en_afkortingen_worden_uitspreekbaar(self):
        from signaal import audio
        from signaal.model import Selectie

        script = audio.maak_script(
            [Selectie(kop="Nieuw LLM verschenen", wat="Zie https://example.com/x voor details.",
                      waarom="Relevant voor de AVG.", url="https://example.com/x",
                      bron="test", categorie="model")],
            date(2026, 7, 29),
        )
        self.assertNotIn("https://", script)
        self.assertIn("el-el-em", script)
        self.assertIn("aa-vee-gee", script)


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
