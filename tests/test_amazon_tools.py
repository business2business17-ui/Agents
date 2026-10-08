"""Regression tests for the Amazon agents (Product Intelligence, Feed Compiler, Feed Error Agent): shared workbook tools and scripts.

Run:  python3 -m unittest discover -s tests -v      (needs openpyxl, lxml)
Builds a synthetic Amazon-like workbook (Template with example row 6, list validation via a defined name, hidden
sheet, merged cells, fake macro part) and checks the safety guarantees of patch / guard / dry-run / report parsing.
"""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

import openpyxl
from openpyxl.styles import PatternFill
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "shared", "amazon")
PI = os.path.join(ROOT, "plugins", "amazon-product-intelligence", "skills", "amazon-product-intelligence", "scripts")
ER = os.path.join(ROOT, "plugins", "amazon-feed-error-agent", "skills", "amazon-feed-error-agent", "scripts")


def run(script, *args, ok=(0,)):
    p = subprocess.run([sys.executable, script, *map(str, args)], capture_output=True, text=True)
    assert p.returncode in ok, f"{os.path.basename(script)} {args} -> {p.returncode}\n{p.stdout}\n{p.stderr}"
    return p


def make_feed(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws["A1"] = "TemplateType=x"
    ws.merge_cells("A1:C1")
    keys = ["feed_product_type", "item_sku", "external_product_id", "item_name", "color_name", "generic_keywords"]
    for i, k in enumerate(keys, 1):
        ws.cell(5, i, k)
        ws.cell(6, i, "example")
    dv = DataValidation(type="list", formula1="=ValidColors", allow_blank=True)
    ws.add_data_validation(dv)
    dv.add("E7:E200")
    dd = wb.create_sheet("Data Definitions")
    dd["A1"] = "Field"
    vv = wb.create_sheet("Valid Values")
    vv["A1"], vv["A2"] = "Blue", "Red"
    vv.sheet_state = "hidden"
    wb.defined_names["ValidColors"] = DefinedName("ValidColors", attr_text="'Valid Values'!$A$1:$A$2")
    tmp = path + ".tmp"
    wb.save(tmp)
    with zipfile.ZipFile(tmp) as zi, zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zo:
        for n in zi.namelist():
            zo.writestr(n, zi.read(n))
        zo.writestr("xl/vbaProject.bin", b"\x00FAKEVBA")
    os.remove(tmp)


class AmazonTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.feed = os.path.join(cls.d, "clean.xlsm")
        make_feed(cls.feed)

    def p(self, name):
        return os.path.join(self.d, name)

    def write_json(self, name, data):
        with open(self.p(name), "w", encoding="utf-8") as f:
            json.dump(data, f)
        return self.p(name)

    def test_pricing_policy_v3(self):
        run(os.path.join(SH, "pricing_engine.py"), "--self-test")
        out = json.loads(run(os.path.join(SH, "pricing_engine.py"), "--sale", "24.99", "--marketplace", "DE").stdout)
        self.assertEqual((out["standard_price"], out["business_price"]), (27.77, 24.99))

    def test_user_decided_tiers_and_b2b_min(self):
        out = json.loads(run(os.path.join(SH, "pricing_engine.py"), "--sale", "24.99", "--marketplace", "DE", "--tiers",
                             "2:5,4:10", "--tier-basis", "business", "--b2b-min", "deepest-tier").stdout)
        self.assertEqual(out["business_min_price"], out["quantity_tiers"][-1]["price"])
        self.assertEqual(out["guardrails"]["policy_status"], "USER_DECISION")
        nobasis = run(os.path.join(SH, "pricing_engine.py"), "--sale", "24.99", "--marketplace", "DE", "--tiers", "2:5", ok=(1,))
        self.assertIn("PRICE_DATA_REQUIRED", nobasis.stdout)

    def test_margin_calc_proposes_ladder_within_margin(self):
        args = ["--cost", "9", "--referral-pct", "15", "--fba-fee", "3.2", "--channel", "fba", "--vat-pct", "19",
                "--target-margin", "15", "--basis-price", "24.99", "--quantities", "2,4", "--json"]
        out = json.loads(run(os.path.join(SH, "margin_calc.py"), *args).stdout)["fba"]
        ladder = out["proposed_ladder"]["tiers"]
        self.assertEqual([t["quantity"] for t in ladder], [2, 4])
        for t in ladder:  # every proposed tier keeps the target margin
            self.assertGreaterEqual(float(t["margin"].rstrip("%")), 15.0)
        p = run(os.path.join(SH, "margin_calc.py"), "--cost", "9", "--referral-pct", "15", "--mfn-fee", "4.5", "--channel", "mfn",
                "--vat-pct", "19", "--target-margin", "25", "--price", "24.99", ok=(1,))
        self.assertIn("BELOW TARGET", p.stdout)

    def test_performance_metrics(self):
        base = ["--cost", "9", "--referral-pct", "15", "--fba-fee", "3.2", "--channel", "fba", "--vat-pct", "19",
                "--lines", "24.99:300,22.49:120", "--total-sales", "10195.80", "--json"]
        out = json.loads(run(os.path.join(SH, "performance_calc.py"), *base, "--ad-spend", "650", "--ad-sales", "2100",
                             "--target-margin", "10", ok=(0, 1)).stdout)
        self.assertEqual(out["gmv_gross"], "10195.80")
        self.assertEqual(out["acos"], "31.0%")
        self.assertEqual(out["tacos"], "6.4%")
        self.assertEqual(out["roas"], "3.23")
        self.assertEqual(out["net_profit"], "1264.53")
        p = run(os.path.join(SH, "performance_calc.py"), *base, "--ad-spend", "650", "--ad-sales", "2100",
                "--target-margin", "15", ok=(1,))
        self.assertIn("below target", p.stdout)

    def test_sales_basis_has_no_silent_default(self):
        args = ["--cost", "9", "--referral-pct", "15", "--fba-fee", "3.2", "--channel", "fba", "--vat-pct", "19",
                "--lines", "24.99:300", "--ad-spend", "100", "--ad-sales", "500"]
        p = run(os.path.join(SH, "performance_calc.py"), *args, ok=(1,))
        self.assertEqual(p.returncode, 1)
        self.assertIn("sales basis unknown", p.stderr)
        net = json.loads(run(os.path.join(SH, "performance_calc.py"), *args, "--total-sales", "6300", "--json", ok=(0, 1)).stdout)
        self.assertTrue(net["assumptions"]["sales_basis"].startswith("net (DETECTED"))

    def test_b2b_max_is_tied_to_sale_price(self):
        out = json.loads(run(os.path.join(SH, "pricing_engine.py"), "--sale", "24.99", "--marketplace", "DE", "--b2b-max-pct", "20").stdout)
        self.assertEqual(out["business_max_price"], 29.99)
        self.assertGreaterEqual(out["business_max_price"], out["sale_price"])
        self.assertIn("max(Business Price, Sale Price)", out["guardrails"]["business_max_rule"])

    def test_patch_guard_roundtrip(self):
        cells = self.write_json("c.json", [
            {"cell": "B7", "value": "SKU-1"}, {"cell": "C7", "value": "0012345678905", "type": "text"},
            {"cell": "D7", "value": "=evil()"}, {"cell": "E7", "value": "Blue"}])
        out = self.p("out.xlsm")
        run(os.path.join(SH, "xlsm_patch.py"), "--source", self.feed, "--cells", cells, "--out", out, "--sheet", "Template")
        run(os.path.join(SH, "workbook_guard.py"), "--source", self.feed, "--output", out, "--sheet", "Template", "--approved", cells)
        wb = openpyxl.load_workbook(out)
        ws = wb["Template"]
        self.assertEqual(ws["C7"].value, "0012345678905")
        self.assertEqual(ws["C7"].data_type, "s")
        self.assertEqual(ws["D7"].data_type, "s")  # text, not a formula
        self.assertEqual(ws["B6"].value, "example")
        with zipfile.ZipFile(out) as z:
            self.assertIn("xl/vbaProject.bin", z.namelist())

    def test_patch_refuses_protected_rows_and_overwrites(self):
        bad = self.write_json("bad.json", [{"cell": "B6", "value": "x"}])
        p = run(os.path.join(SH, "xlsm_patch.py"), "--source", self.feed, "--cells", bad, "--out", self.p("o1.xlsm"),
                "--sheet", "Template", ok=(1,))
        self.assertIn("READ-ONLY", p.stderr)
        self.assertFalse(os.path.exists(self.p("o1.xlsm")))
        same = run(os.path.join(SH, "xlsm_patch.py"), "--source", self.feed, "--cells", bad, "--out", self.feed,
                   "--sheet", "Template", ok=(1,))
        self.assertIn("differ", same.stderr)

    def test_guard_detects_tampering(self):
        cells = self.write_json("c2.json", [{"cell": "B7", "value": "SKU-2"}])
        out = self.p("out2.xlsm")
        run(os.path.join(SH, "xlsm_patch.py"), "--source", self.feed, "--cells", cells, "--out", out, "--sheet", "Template")
        wb = openpyxl.load_workbook(out)
        wb["Template"]["B6"] = "HACK"
        wb["Data Definitions"]["A1"] = "Changed"
        bad = self.p("tampered.xlsx")
        wb.save(bad)
        p = run(os.path.join(SH, "workbook_guard.py"), "--source", self.feed, "--output", bad, "--sheet", "Template",
                "--approved", cells, ok=(1,))
        self.assertIn("NOT READY", p.stdout)

    def test_dry_run_catches_enum_and_identifier_problems(self):
        cells = self.write_json("c3.json", [
            {"cell": "E7", "value": "blue"}, {"cell": "E8", "value": "Green"},
            {"cell": "C7", "value": 4006381333931, "type": "number"}, {"cell": "B7", "value": "S1"}, {"cell": "B8", "value": "S1"}])
        p = run(os.path.join(SH, "validate_cells.py"), "--source", self.feed, "--cells", cells, "--sheet", "Template",
                "--key-column", "B", ok=(1,))
        for code in ("ENUM_AMBIGUOUS", "ENUM_INVALID", "IDENTIFIER_NOT_TEXT", "DUPLICATE_FEED_ROW"):
            self.assertIn(code, p.stdout)

    def test_inspect_confirms_row7_boundary(self):
        run(os.path.join(SH, "xlsm_inspect.py"), self.feed, "--json", self.p("insp.json"))
        d = json.load(open(self.p("insp.json"), encoding="utf-8"))
        self.assertTrue(d["macros_present"])
        self.assertEqual(d["data_start_check"]["status"], "DATA_START_CONFIRMED")

    def test_processing_report_and_comparison(self):
        wb = openpyxl.load_workbook(self.feed)
        ws = wb["Template"]
        ws["B7"], ws["E7"] = "SKU-1", "Bluee"
        ws["E7"].fill = PatternFill("solid", fgColor="FFFFA500")
        s = wb.create_sheet("Feed Processing Summary", 0)
        s.append(["Error code", "Category of error", "Store", "Error message", "Affected field", "Impacted column", "Number of errors"])
        s.append([8058, "Error", "DE", "Invalid value", "color_name", "E", 1])
        rep = self.p("rep.xlsx")
        wb.save(rep)
        run(os.path.join(ER, "parse_processing_report.py"), rep, "--marketplace", "DE", "--json", self.p("p1.json"))
        d = json.load(open(self.p("p1.json"), encoding="utf-8"))
        self.assertEqual(d["totals"]["errors"], 1)
        self.assertEqual(d["findings"][0]["error_code"], "8058")
        d2 = dict(d, findings=[])
        self.write_json("p2.json", d2)
        p = run(os.path.join(ER, "compare_reports.py"), self.p("p1.json"), self.p("p2.json"))
        self.assertIn("Resolved: 1", p.stdout)

    def test_gtin_and_handoff(self):
        p = run(os.path.join(PI, "gtin_check.py"), "4006381333931", "4006381333932", ok=(1,))
        self.assertIn("GTIN_VALID", p.stdout)
        self.assertIn("check digit should be 1", p.stdout)
        ex = run(os.path.join(PI, "handoff_tool.py"), "--example").stdout
        path = self.p("h.json")
        open(path, "w").write(ex)
        run(os.path.join(PI, "handoff_tool.py"), "validate", path)
        rec = json.loads(ex)
        rec["pricing"]["standard_price"] = 1.0
        self.write_json("h_bad.json", rec)
        run(os.path.join(PI, "handoff_tool.py"), "validate", self.p("h_bad.json"), ok=(1,))

    def test_seo_import_tiers_and_marketplace_isolation(self):
        import csv as _csv
        de = self.p("cerebro_de.csv")
        with open(de, "w", newline="", encoding="utf-8-sig") as f:
            w = _csv.writer(f, delimiter=";")
            w.writerow(["Keyword Phrase", "Search Volume", "Cerebro IQ Score"])
            for r in [("handyhülle pixel 8", "12.400", 1), ("pixel 8 hülle", "9.800", 1), ("hülle pixel 8", "9.800", 1),
                      ("samsung galaxy hülle", "20.000", 1), ("bester handyhülle pixel 8", "300", 1),
                      ("kopfhörer bluetooth", "30.000", 1), ("pixel 8 handyhülle schwarz matt", "1.200", 1)]:
                w.writerow(r)
        out = self.p("seo.json")
        run(os.path.join(PI, "seo_import.py"), de, "--marketplace", "DE", "--product-terms", "pixel 8,hülle,handyhülle",
            "--competitors", "samsung", "--seo-date", "2026-10-01", "--out", out)
        d = json.load(open(out, encoding="utf-8"))
        by = {k["keyword"]: k for k in d["keywords"]}
        self.assertEqual(by["handyhülle pixel 8"]["tier"], "TIER_1_PRIMARY")
        self.assertEqual(by["pixel 8 handyhülle schwarz matt"]["tier"], "TIER_3_LONG_TAIL")
        self.assertEqual(by["samsung galaxy hülle"]["status"], "COMPETITOR_TERM")
        self.assertEqual(by["bester handyhülle pixel 8"]["status"], "PROHIBITED_TERM")
        self.assertEqual(by["kopfhörer bluetooth"]["status"], "IRRELEVANT")
        self.assertEqual(sum(k["status"] == "SEMANTIC_DUPLICATE" for k in d["keywords"]), 1)
        self.assertEqual(d["sanitization_report"]["competitor_terms"], 1)
        # an English (US) export must never be accepted for DE
        us = self.p("cerebro_us.csv")
        with open(us, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["Keyword Phrase", "Search Volume"])
            for r in [("phone case for pixel 8", 12000), ("case with stand for women", 5000), ("clear case for men", 4000)]:
                w.writerow(r)
        p = run(os.path.join(PI, "seo_import.py"), us, "--marketplace", "DE", "--product-terms", "pixel 8", ok=(1,))
        self.assertIn("SEO_MARKETPLACE_MISMATCH", p.stdout)
        # without product terms nothing is tiered
        r = run(os.path.join(PI, "seo_import.py"), de, "--marketplace", "DE", "--seo-date", "2026-10-01", "--out", self.p("s2.json"))
        self.assertIn("NEEDS_PRODUCT_TERMS", json.dumps(json.load(open(self.p("s2.json"), encoding="utf-8"))))

    def test_countries_and_languages(self):
        import openpyxl as _x
        def mk(name, rows):
            wb = _x.Workbook(); ws = wb.active
            ws.append(["Helium 10 Cerebro"]); ws.append([]); ws.append(["Keyword Phrase", "Search Volume"])  # title rows above the header
            for r in rows:
                ws.append(r)
            wb.save(self.p(name)); return self.p(name)
        seo = os.path.join(PI, "seo_import.py")
        # multi-language marketplace: language must be chosen
        ca = mk("ca.xlsx", [("phone case for pixel 8", 9000), ("pixel 8 case with stand", 4000)])
        p = run(seo, ca, "--marketplace", "CA", "--product-terms", "pixel 8", ok=(1,))
        self.assertIn("ask the user which language", p.stderr + p.stdout)
        p = run(seo, ca, "--marketplace", "CA", "--language", "fr", "--product-terms", "pixel 8", ok=(1,))
        self.assertIn("SEO_LANGUAGE_MISMATCH", p.stdout)
        run(seo, ca, "--marketplace", "CA", "--language", "en", "--product-terms", "pixel 8", "--seo-date", "2026-10-01")
        # script-based languages
        jp = mk("jp.xlsx", [("Pixel 8 ケース", 15000), ("スマホケース 耐衝撃", 20000), ("phone case for pixel 8", 3000)])
        out = self.p("jp.json")
        run(seo, jp, "--marketplace", "JP", "--product-terms", "pixel 8,ケース", "--seo-date", "2026-10-01", "--out", out)
        by = {k["keyword"]: k for k in json.load(open(out, encoding="utf-8"))["keywords"]}
        self.assertEqual(by["Pixel 8 ケース"]["language"], "ja")
        self.assertEqual(by["phone case for pixel 8"]["status"], "WRONG_LANGUAGE")
        ae = mk("ae.xlsx", [("جراب بكسل 8", 3000), ("غطاء هاتف", 2000)])
        run(seo, ae, "--marketplace", "AE", "--language", "ar", "--product-terms", "بكسل,جراب,غطاء", "--seo-date", "2026-10-01")
        # locale lists for content checks
        p = run(os.path.join(PI, "content_check.py"), "--title", "Acme etui na telefon", "--lang", "pl")
        self.assertIn("LOCALE_LIST_MISSING", p.stdout)
        # handoff: language required for multi-language marketplaces, currency must match the marketplace
        rec = json.loads(run(os.path.join(PI, "handoff_tool.py"), "--example").stdout)
        rec["marketplace"] = "CA"
        rec["content"].pop("language")
        self.write_json("h_ca.json", rec)
        run(os.path.join(PI, "handoff_tool.py"), "seal", self.p("h_ca.json"), self.p("h_ca.jsonl"))
        p = run(os.path.join(PI, "handoff_tool.py"), "validate", self.p("h_ca.jsonl"), ok=(1,))
        self.assertIn("content.language is required for CA", p.stdout)
        self.assertIn("CURRENCY_CONFLICT", p.stdout)

    def test_marketplace_table_matches_pricing_engine(self):
        sys.path.insert(0, SH)
        import marketplaces, pricing_engine
        for code, cur in pricing_engine.MARKETPLACE_CURRENCY.items():
            self.assertEqual(marketplaces.currency(code), cur, code)
        self.assertEqual(marketplaces.languages("JP"), ["ja"])
        self.assertTrue(marketplaces.needs_language_choice("BE"))

    def test_content_check(self):
        p = run(os.path.join(PI, "content_check.py"), "--title",
                "Acme Case Case Case for Phone best price 9,99 EUR", ok=(1,))
        self.assertIn("TITLE_WORD_REPETITION", p.stdout)
        self.assertIn("FORBIDDEN_TERM_FOUND", p.stdout)


if __name__ == "__main__":
    unittest.main()
