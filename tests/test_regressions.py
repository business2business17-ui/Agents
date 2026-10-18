"""Regression tests for the audit fixes (performance, number parsing, write safety, GTIN, report history).

Run:  python3 -m unittest discover -s tests -v      (needs openpyxl, lxml)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_amazon_tools import PI, SH, make_feed, run  # noqa: E402

sys.path.insert(0, SH)
import pricing_engine  # noqa: E402
import handoff_tool  # noqa: E402
from xlsm_patch import RowIndex  # noqa: E402


class Base(unittest.TestCase):
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


class NumberParsing(unittest.TestCase):
    def test_locale_formats(self):
        for text, want in [("24,99", "24.99"), ("1,234.50", "1234.50"), ("1.234,50", "1234.50"), ("1 234,50", "1234.50"),
                           ("1,234,567", "1234567"), ("1.234.567", "1234567"), ("24.99", "24.99"), ("-5,5", "-5.5")]:
            self.assertEqual(str(pricing_engine.dec(text)), want, text)

    def test_ambiguous_or_malformed_numbers_are_rejected(self):
        for text in ("1,500", "1,2,3.4", "1.234,5,6", "abc", "NaN"):
            with self.assertRaises(ValueError, msg=text):
                pricing_engine.dec(text)

    def test_ambiguous_price_is_not_silently_computed(self):
        with self.assertRaises(ValueError):
            pricing_engine.compute("1,500", marketplace="JP")


class WriteSafety(Base):
    def test_out_alias_of_source_is_refused(self):
        cells = self.write_json("c1.json", [{"cell": "B7", "value": "SKU-1"}])
        p = subprocess.run([sys.executable, os.path.join(SH, "xlsm_patch.py"), "--source", self.feed, "--cells", cells,
                            "--out", os.path.join(os.path.dirname(self.feed), ".", os.path.basename(self.feed)),
                            "--sheet", "Template"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertIn("must differ", p.stderr)

    def test_no_temp_file_left_and_rows_stay_ordered(self):
        cells = self.write_json("c2.json", [{"cell": "B9", "value": "a"}, {"cell": "B7", "value": "b"}, {"cell": "B8", "value": "c"},
                                            {"cell": "B300", "value": "d"}, {"cell": "A10", "value": "e"}])
        out = self.p("rows_out.xlsm")
        run(os.path.join(SH, "xlsm_patch.py"), "--source", self.feed, "--cells", cells, "--out", out, "--sheet", "Template")
        self.assertEqual([f for f in os.listdir(self.d) if ".tmp-" in f], [])
        with zipfile.ZipFile(out) as z:
            xml = z.read("xl/worksheets/sheet1.xml").decode()
        import re
        rows = [int(x) for x in re.findall(r'<row r="(\d+)"', xml)]
        self.assertEqual(rows, sorted(rows))
        self.assertTrue({7, 8, 9, 10, 300} <= set(rows))

    def test_row_index_inserts_in_order(self):
        from lxml import etree
        from xlsx_core import M
        sd = etree.Element(M + "sheetData")
        for r in (1, 5, 9):
            etree.SubElement(sd, M + "row", r=str(r))
        idx = RowIndex(sd)
        for r in (7, 3, 12, 6, 5):
            idx.get(r)
        self.assertEqual([int(x.get("r")) for x in sd], [1, 3, 5, 6, 7, 9, 12])

    def test_non_finite_number_is_refused(self):
        cells = self.write_json("c3.json", [{"cell": "B7", "value": "NaN", "type": "number"}])
        p = subprocess.run([sys.executable, os.path.join(SH, "xlsm_patch.py"), "--source", self.feed, "--cells", cells,
                            "--out", self.p("nan.xlsm"), "--sheet", "Template"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertFalse(os.path.exists(self.p("nan.xlsm")))

    def test_guard_still_detects_structure_tampering(self):
        cells = self.write_json("c4.json", [{"cell": "B7", "value": "SKU-1"}])
        out = self.p("g_ok.xlsm")
        run(os.path.join(SH, "xlsm_patch.py"), "--source", self.feed, "--cells", cells, "--out", out, "--sheet", "Template")
        bad = self.p("g_bad.xlsm")
        with zipfile.ZipFile(out) as zi, zipfile.ZipFile(bad, "w", zipfile.ZIP_DEFLATED) as zo:
            for n in zi.namelist():
                data = zi.read(n)
                if n == "xl/worksheets/sheet1.xml":
                    data = data.replace(b"<mergeCell ref=\"A1:C1\"/>", b"<mergeCell ref=\"A1:D1\"/>")
                zo.writestr(n, data)
        p = run(os.path.join(SH, "workbook_guard.py"), "--source", self.feed, "--output", bad, "--sheet", "Template",
                "--approved", cells, ok=(1,))
        self.assertRegex(p.stdout, r"FAIL\s+sheet_structure")


class FeedPipeline(Base):
    def test_pass_and_fail_paths(self):
        good = self.write_json("pl_good.json", [{"cell": "B7", "value": "SKU-1"}, {"cell": "E7", "value": "Blue"}])
        out = self.p("pl_out.xlsm")
        r = run(os.path.join(SH, "feed_pipeline.py"), "--source", self.feed, "--cells", good, "--out", out, "--sheet", "Template")
        self.assertIn("VERDICT: PASS_TO_FULL_AUDIT", r.stdout)
        self.assertTrue(os.path.exists(out))
        with open(self.p("pl_out_reports/pipeline.json"), encoding="utf-8") as f:
            self.assertEqual([s["name"] for s in json.load(f)["steps"]], ["validate", "patch", "guard"])
        bad = self.write_json("pl_bad.json", [{"cell": "E7", "value": "Purple"}])
        out2 = self.p("pl_out2.xlsm")
        r = run(os.path.join(SH, "feed_pipeline.py"), "--source", self.feed, "--cells", bad, "--out", out2, "--sheet", "Template", ok=(1,))
        self.assertIn("VERDICT: NOT_READY", r.stdout)
        self.assertFalse(os.path.exists(out2), "a failed dry run must never write the feed")


class Handoff(unittest.TestCase):
    def example(self):
        return handoff_tool.seal_one(handoff_tool.EXAMPLE, "B1", "2.0.0", "2026-10-08T00:00:00Z")

    def test_valid_example_and_gtin_checksum(self):
        self.assertEqual(handoff_tool.validate_one(self.example())[0], [])
        r = self.example()
        r["identifiers"]["ean"] = "4006381333932"
        r = handoff_tool.seal_one(r, "B1", "2.0.0", "2026-10-08T00:00:00Z")
        errs = handoff_tool.validate_one(r)[0]
        self.assertTrue(any("check digit mismatch" in e and "INVALID_GTIN" in e for e in errs), errs)

    def test_gtin_problem(self):
        self.assertIsNone(handoff_tool.gtin_problem("036000291452", "upc"))
        self.assertIsNone(handoff_tool.gtin_problem("4006381333931", "ean"))
        self.assertIn("12 digits", handoff_tool.gtin_problem("036000291452", "ean"))
        self.assertIn("not a digit", handoff_tool.gtin_problem("40063813339x1", "ean"))

    def test_malformed_record_reports_error_not_traceback(self):
        r = self.example()
        r["identifiers"] = None
        errs, _ = handoff_tool.validate_one(r)
        self.assertTrue(errs and "malformed" in errs[0])
        self.assertEqual(handoff_tool.validate_one([1, 2])[0], ["record must be a JSON object"])


class CompareReports(Base):
    def finding(self, code, sku="S1", attr="color_name"):
        return dict(marketplace="DE", sku=sku, attribute=attr, error_code=code, severity="ERROR", cell="E7")

    def test_two_errors_on_one_cell_count_one_attempt(self):
        prev = self.write_json("prev.json", {"findings": [self.finding("8541"), self.finding("8542")]})
        cur = self.write_json("cur.json", {"findings": [self.finding("8541"), self.finding("8542")]})
        out = self.p("cmp.json")
        run(os.path.join(SH, "compare_reports.py"), prev, cur, "--out", out)
        with open(out, encoding="utf-8") as f:
            res = json.load(f)
        self.assertEqual(list(res["history"].values()), [2])
        self.assertEqual(res["counts"]["ESCALATION_REQUIRED"], 0)


class Marketplaces(unittest.TestCase):
    def test_language_argument_does_not_swallow_code(self):
        p = run(os.path.join(SH, "marketplaces.py"), "DE", "--language", "DE", ok=(0, 1))
        self.assertTrue(p.stdout.startswith("DE:"))

    def test_missing_language_value(self):
        run(os.path.join(SH, "marketplaces.py"), "DE", "--language", ok=(2,))


class ProductIntelligenceCalcs(unittest.TestCase):
    def test_bad_lines_give_a_message(self):
        p = run(os.path.join(PI, "performance_calc.py"), "--cost", "9", "--referral-pct", "15", "--fba-fee", "3.2",
                "--channel", "fba", "--lines", "24.99", ok=(1,))
        self.assertIn("expected price:units", p.stderr)
        self.assertNotIn("Traceback", p.stderr)

    def test_ambiguous_decimal_comma_is_rejected(self):
        p = run(os.path.join(PI, "margin_calc.py"), "--cost", "1,500", "--referral-pct", "15", "--fba-fee", "3",
                "--channel", "fba", "--price", "40", ok=(1,))
        self.assertIn("ambiguous", p.stderr)


if __name__ == "__main__":
    unittest.main()
