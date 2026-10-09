"""Regression tests for the Design agent (amazon-creative-studio) scripts.

Run:  python3 -m unittest discover -s tests -v      (needs openpyxl, Pillow)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CS = os.path.join(ROOT, "plugins", "amazon-creative-studio", "skills", "amazon-creative-studio", "scripts")


def run(script, *args, ok=(0,)):
    p = subprocess.run([sys.executable, script, *map(str, args)], capture_output=True, text=True)
    assert p.returncode in ok, f"{os.path.basename(script)} {args} -> {p.returncode}\n{p.stdout}\n{p.stderr}"
    return p


class DesignTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()

    def p(self, name):
        return os.path.join(self.d, name)

    def test_creative_validator_main_image(self):
        from PIL import Image, ImageDraw
        good = Image.new("RGB", (1200, 1200), "white")
        ImageDraw.Draw(good).rectangle((60, 40, 1140, 1150), fill=(20, 80, 160))
        good.save(self.p("main.jpg"))
        run(os.path.join(CS, "validate_asset.py"), self.p("main.jpg"), "--placement", "pdp-main", ok=(0, 2))
        Image.new("RGB", (800, 800), (230, 230, 230)).save(self.p("grey.png"))
        run(os.path.join(CS, "validate_asset.py"), self.p("grey.png"), "--placement", "pdp-main", ok=(1,))

    def test_creative_gtin_match(self):
        from PIL import Image
        imgs = self.p("imgs")
        os.makedirs(imgs)
        for name in ("4006381333931.jpg", "4006381333931_2.png", "36000291452.jpg", "5901234123457.jpg", "bad name.jpg"):
            Image.new("RGB", (40, 40), "white").save(os.path.join(imgs, name))
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Name", "Штрихкод", "ТТХ", "Преимущества", "Категория", "Тип товара", "Описание"])
        ws.append(["A", 4006381333931, "Capacity 500 ml", "Keeps drinks cold\nBPA free", "Home", "Bottle", "Nice bottle"])
        ws.append(["B", "036000291452", "Weight 120 g", None, None, None, None])
        ws.append(["C", "9999999999999", "x", "y", None, None, None])
        wb.save(self.p("p.xlsx"))
        out = self.p("match.json")
        run(os.path.join(CS, "match_inputs.py"), "--images", imgs, "--xlsx", self.p("p.xlsx"), "--out", out, ok=(1,))
        r = json.load(open(out, encoding="utf-8"))
        by = {m["key"]: m for m in r["matched"]}
        a = by["04006381333931"]
        self.assertEqual(len(a["images"]), 2)
        self.assertEqual(a["row"]["benefits"], ["Keeps drinks cold", "BPA free"])
        b = by["00036000291452"]  # UPC lost its leading zero in the file name: matched via check digit, flagged
        self.assertIn("ZERO_PADDED", b["flags"])
        self.assertEqual(b["row"]["benefits_status"], "MISSING_DRAFT_FROM_TTX")
        self.assertEqual(a["row"]["category"], "Home")
        self.assertEqual(a["row"]["product_type"], "Bottle")
        self.assertEqual(a["row"]["classification_status"], "FROM_FILE_CONFIRM_AT_C1")
        self.assertEqual(a["row"]["existing_description"], {"Описание": "Nice bottle"})
        self.assertEqual(b["row"]["classification_status"], "MISSING_ASK")
        self.assertEqual(r["summary"]["classification_to_ask"], 1)
        self.assertNotIn("Категория", a["row"]["facts"])
        kinds = {i["issue"] for i in r["issues"]}
        self.assertTrue({"IMAGE_WITHOUT_ROW", "ROW_WITHOUT_IMAGE", "FILENAME_NOT_A_GTIN"} <= kinds)


if __name__ == "__main__":
    unittest.main()
