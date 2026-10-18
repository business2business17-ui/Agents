"""Tests for the PPC agent scripts (shared/amazon/ppc_search_terms.py)."""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "shared", "amazon", "ppc_search_terms.py")
HDR = ["Campaign Name", "Ad Group Name", "Targeting", "Match Type", "Customer Search Term", "Impressions", "Clicks", "Spend",
       "7 Day Total Sales ", "7 Day Total Orders (#)"]
ROWS = [
    ["Auto", "AG", "close-match", "-", "blender smoothie", 5000, 40, "30.00", "$150.00", 5],
    ["Auto", "AG", "close-match", "-", "free blender recipes", 900, 30, "30.00", "$0.00", 0],
    ["Auto", "AG", "close-match", "-", "acme blender", 900, 30, "30.00", "$0.00", 0],
    ["Auto", "AG", "loose-match", "-", "b0abcdefgh", 300, 25, "25.00", "$120.00", 3],
    ["Auto", "AG", "close-match", "-", "portable blender", 1000, 30, "24.00", "$130.00", 4],
    ["Exact", "AG", "portable blender", "Exact", "portable blender", 2000, 50, "40.00", "$200.00", 6],
    ["Auto", "AG", "close-match", "-", "rare term", 100, 3, "2.00", "$25.00", 1],
    ["Auto", "AG", "loose-match", "-", "converts elsewhere", 100, 30, "30.00", "$0.00", 0],
    ["Exact", "AG", "converts elsewhere", "Exact", "converts elsewhere", 100, 20, "10.00", "$90.00", 3],
]


def run(*args, ok=(0,)):
    p = subprocess.run([sys.executable, SCRIPT, *map(str, args)], capture_output=True, text=True)
    assert p.returncode in ok, f"{args} -> {p.returncode}\n{p.stdout}\n{p.stderr}"
    return p


class PpcSearchTerms(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.csv = os.path.join(self.d.name, "st.csv")
        with open(self.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(HDR)
            w.writerows(ROWS)

    def tearDown(self):
        self.d.cleanup()

    def result(self, *extra):
        return json.loads(run(self.csv, "--target-acos", "30", "--json", *extra).stdout)

    def test_harvest_negative_and_watch(self):
        r = self.result("--brand", "acme")
        harvest = {h["term"] for h in r["keyword_harvest"]}
        self.assertIn("blender smoothie", harvest)
        self.assertNotIn("portable blender", harvest)  # already an exact keyword
        asin = [h for h in r["keyword_harvest"] if h["term"] == "b0abcdefgh"][0]
        self.assertIn("ASIN", asin["route"])
        neg = {n["term"] for n in r["negative_keywords"]}
        self.assertEqual(neg, {"free blender recipes"})
        watch = {w["term"]: w["reason"] for w in r["watch"]}
        self.assertIn("brand", watch["acme blender"])  # own brand is never negated automatically
        self.assertIn("another campaign", watch["converts elsewhere"])  # fix routing instead

    def test_bid_is_value_based_and_capped(self):
        r = self.result("--max-cpc", "0.5")
        exact = [b for b in r["bid_recommendations"] if b["match_type"] == "Exact" and b["targeting"] == "portable blender"][0]
        self.assertLessEqual(exact["suggested_bid"], 0.5)
        thin = [b for b in r["bid_recommendations"] if b["targeting"] == "close-match"][0]
        self.assertNotEqual(thin["action"], "watch")  # 160 clicks in total
        self.assertEqual(r["meta"]["rows"], len(ROWS))

    def test_xlsx_input_and_output(self):
        x = os.path.join(self.d.name, "st.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Some report title"])
        ws.append(HDR)
        for row in ROWS:
            ws.append(row)
        wb.save(x)
        out = os.path.join(self.d.name, "rec.xlsx")
        run(x, "--target-acos", "30", "--out", out)
        self.assertEqual(openpyxl.load_workbook(out).sheetnames,
                         ["Campaign Summary", "Bid Recommendations", "Negative Keywords", "Keyword Harvest", "Watch"])

    def test_bad_input(self):
        run(self.csv, "--target-acos", "0", ok=(2,))
        empty = os.path.join(self.d.name, "e.csv")
        with open(empty, "w") as fh:
            fh.write("a,b\n1,2\n")
        run(empty, "--target-acos", "30", ok=(2,))

    def test_european_number_format(self):
        p = os.path.join(self.d.name, "eu.csv")
        with open(p, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(HDR)
            w.writerow(["Auto", "AG", "k", "-", "term eins", "1.000", "30", "30,50", "150,00 €", "5"])
        r = json.loads(run(p, "--target-acos", "30", "--json").stdout)
        self.assertEqual(r["meta"]["spend"], 30.5)
        self.assertEqual(r["meta"]["sales"], 150.0)


if __name__ == "__main__":
    unittest.main()
