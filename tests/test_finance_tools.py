"""Tests for the Finance agent scripts: reference examples from references/formulas.md and report detection."""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "plugins", "amazon-finance", "skills", "amazon-finance")
CALC = os.path.join(SK, "scripts", "finance_calc.py")
DETECT = os.path.join(SK, "scripts", "report_detect.py")


def run(script, *args, ok=(0,)):
    p = subprocess.run([sys.executable, script, *map(str, args)], capture_output=True, text=True)
    assert p.returncode in ok, f"{os.path.basename(script)} {args} -> {p.returncode}\n{p.stdout}\n{p.stderr}"
    return p


class FinanceCalc(unittest.TestCase):
    def unit(self, *a):
        return json.loads(run(CALC, "unit", *a, "--json").stdout)

    def test_u1_with_vat(self):  # formulas.md U1
        r = self.unit("--price", 29.99, "--vat-pct", 19, "--referral-pct", 15, "--ad-pct", 10, "--cost-fixed", 12, "--margin-pct", 15)
        self.assertEqual((r["net_revenue"], r["referral_fee"], r["ad_cost"], r["unit_profit"]), ("25.20", "4.50", "3.00", "5.70"))
        self.assertEqual((r["break_even_price"], r["target_price"]), ("20.33", "25.85"))
        self.assertEqual((r["break_even_acos_pct"][:4], r["target_acos_pct"][:4]), ("29.0", "16.4"))

    def test_u2_without_vat(self):
        r = self.unit("--price", 29.99, "--vat-pct", 0, "--referral-pct", 15, "--ad-pct", 10, "--cost-fixed", 12, "--margin-pct", 15)
        self.assertEqual((r["break_even_price"], r["target_price"]), ("16.00", "20.00"))

    def test_u3_u4_referral_includes_shipping_and_dst_with_amazon_rounding(self):
        it = run(CALC, "referral", "--price", 63.55, "--ship", 10, "--referral-pct", 15, "--dst-pct", 3).stdout.strip()
        uk = run(CALC, "referral", "--price", 27.99, "--ship", 6.99, "--referral-pct", 15, "--dst-pct", 2).stdout.strip()
        self.assertEqual((it, uk), ("11.36", "5.36"))
        r = self.unit("--price", 63.55, "--ship", 10, "--vat-pct", 22, "--referral-pct", 15, "--dst-pct", 3, "--cost-fixed", 20)
        self.assertEqual(r["net_revenue"], "60.29")

    def test_ads_percentage_points_vs_percent(self):  # A1 / A2
        a = json.loads(run(CALC, "ads-whatif", "--acos", 30, "--sales", 10000, "--delta-pp", -3).stdout)
        b = json.loads(run(CALC, "ads-whatif", "--acos", 30, "--sales", 10000, "--delta-pct", -3).stdout)
        self.assertEqual((a["spend_after"], a["spend_saving"]), ("2700.00", "300.00"))
        self.assertEqual((b["spend_after"], b["spend_saving"]), ("2910.00", "90.00"))
        self.assertTrue(a["scenario"])
        m = json.loads(run(CALC, "ads-whatif", "--acos", 30, "--sales", 10000, "--delta-pp", -5, "--mode", "B").stdout)
        self.assertEqual(m["spend_before"], m["spend_after"])  # mode B: budget unchanged

    def test_unreachable_price_and_status(self):
        r = self.unit("--price", 20, "--vat-pct", 19, "--referral-pct", 15, "--ad-pct", 80, "--cost-fixed", 5)
        self.assertIsNone(r["break_even_price"])
        self.assertTrue(r["notes"])
        loss = self.unit("--price", 10, "--vat-pct", 19, "--referral-pct", 15, "--cost-fixed", 12)
        self.assertEqual(loss["status"], "Loss")
        ads = self.unit("--price", 29.99, "--vat-pct", 19, "--referral-pct", 15, "--ad-pct", 40, "--cost-fixed", 12)
        self.assertEqual(ads["status"], "Ads Over Limit")

    def test_minimum_referral_fee(self):
        r = self.unit("--price", 2, "--vat-pct", 0, "--referral-pct", 8, "--min-referral", 0.30, "--cost-fixed", 1)
        self.assertEqual(r["referral_fee"], "0.30")
        self.assertEqual(r["break_even_price"], "1.30")  # P = F + min

    def test_bad_input(self):
        run(CALC, "ads-whatif", "--acos", 30, "--sales", 100, ok=(2,))
        run(CALC, "ads-whatif", "--acos", 30, "--sales", 100, "--delta-pp", -40, ok=(2,))


class ReportDetect(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.d.cleanup()

    def write(self, name, rows, delim=","):
        p = os.path.join(self.d.name, name)
        with open(p, "w", newline="", encoding="utf-8-sig") as fh:
            csv.writer(fh, delimiter=delim).writerows(rows)
        return p

    def detect(self, *paths, ok=(0,)):
        return json.loads(run(DETECT, *paths, "--json", ok=ok).stdout)

    def test_german_date_range_report_with_disclaimer_rows(self):
        rows = [["Alle Beträge in EUR, sofern nicht anders angegeben"]] * 7 + [
            ["Datum/Uhrzeit", "Abrechnungsnummer", "Typ", "Bestellnummer", "SKU", "Menge", "Marketplace", "Umsätze", "Verkaufsgebühren",
             "Gebühren zu Versand durch Amazon", "Andere Transaktionsgebühren", "Andere", "Gesamt"],
            ["01.09.2026", "1", "Bestellung", "302-1", "A", "1", "amazon.de", "10,00", "-1,50", "-3,00", "0,00", "0,00", "5,50"]]
        r = self.detect(self.write("DE_date_range.csv", rows))[0]
        self.assertEqual((r["type"], r["status"], r["header_row"], r["marketplace"]), ("Date Range / Transaction Report", "recognized", 8, "DE"))
        self.assertTrue(r["decimal_format"].startswith("european"))
        self.assertEqual(r["marketplace_source"], "by file name")

    def test_payments_transactions_view_and_currency_from_header(self):
        rows = [["Date", "Transaction status", "Transaction type", "Order ID", "Product Details", "Total product charges",
                 "Total promotional rebates", "Amazon fees", "Other", "Total (GBP)"], ["01/09/2026", "Released", "Order Payment", "1", "x", "27.99", "0", "-5.36", "6.99", "29.62"]]
        r = self.detect(self.write("UK_transactions.csv", rows))[0]
        self.assertEqual((r["type"], r["currency"], r["currency_source"]), ("Payments Transactions view", "GBP", "header"))

    def test_business_report_by_asin_without_traffic_and_header_only_file(self):
        hdr = ["(Child) ASIN", "Units ordered", "Ordered Product Sales", "Total order items", "Units refunded", "Refund Rate",
               "Shipped product sales", "Units shipped", "Orders shipped"]
        r = self.detect(self.write("IT_business_1 sen-19 okt.csv", [hdr]))[0]
        self.assertEqual(r["type"], "Business Report (Sales and Orders by ASIN)")
        self.assertEqual(r["rows"], 0)
        self.assertIn("no data", r["note"])
        self.assertEqual(r["marketplace"], "IT")

    def test_unknown_report_and_duplicate_file(self):
        p = self.write("x.csv", [["foo", "bar", "baz"], ["1", "2", "3"]])
        r = self.detect(p, ok=(1,))[0]
        self.assertEqual(r["status"], "unknown")
        hdr = [["sku", "currency", "purchase_cost"], ["A", "EUR", "5"]]
        a, b = self.write("a.csv", hdr), self.write("b.csv", hdr)
        res = self.detect(a, b)
        self.assertEqual(res[0]["type"], "Cost Master (user)")
        self.assertEqual(res[1]["duplicate_of"], "a.csv")

    def test_ads_report_day_window_variants(self):
        hdr = ["Start Date", "Campaign Name", "Ad Group Name", "Advertised SKU", "Advertised ASIN", "Impressions", "Clicks", "Spend",
               "7 Day Total Sales ", "7 Day Total Orders (#)", "7 Day Total Units (#)"]
        r = self.detect(self.write("sp.csv", [hdr]))[0]
        self.assertEqual(r["type"], "Sponsored Products Advertised Product")


if __name__ == "__main__":
    unittest.main()
