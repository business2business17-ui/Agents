"""Regression tests for the Design agent (amazon-creative-studio) scripts.

Run:  python3 -m unittest discover -s tests -v      (needs openpyxl, Pillow)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

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

    def test_creative_specs_and_zip(self):
        from PIL import Image
        Image.new("RGB", (362, 453), "blue").save(self.p("card.png"), dpi=(72, 72))
        run(os.path.join(CS, "validate_asset.py"), self.p("card.png"), "--placement", "brand-story-card")
        Image.new("RGB", (400, 453), "blue").save(self.p("card_bad.png"), dpi=(72, 72))
        run(os.path.join(CS, "validate_asset.py"), self.p("card_bad.png"), "--placement", "brand-story-card", ok=(1,))
        Image.new("RGB", (1500, 1500), "blue").save(self.p("sec.jpg"), dpi=(72, 72))
        p = run(os.path.join(CS, "validate_asset.py"), self.p("sec.jpg"), "--placement", "pdp-secondary", ok=(2,))
        self.assertIn("recommended_resolution", p.stdout)
        Image.new("RGB", (4000, 4000), "blue").save(self.p("sec4k.jpg"), dpi=(72, 72))
        run(os.path.join(CS, "validate_asset.py"), self.p("sec4k.jpg"), "--placement", "pdp-secondary")
        out = self.p("zipout")
        run(os.path.join(CS, "pack_upload_zip.py"), "--asin", "B000123456", "--main", self.p("sec4k.jpg"),
            "--pt", self.p("sec.jpg"), self.p("sec.jpg"), "--out", out)
        with zipfile.ZipFile(os.path.join(out, "B000123456.zip")) as z:
            self.assertEqual(z.namelist(), ["B000123456.MAIN.jpg", "B000123456.PT01.jpg", "B000123456.PT02.jpg"])
        run(os.path.join(CS, "pack_upload_zip.py"), "--asin", "4006381333931", "--main", self.p("sec.jpg"),
            "--out", out, ok=(1,))

    def test_image_probe_reads_facts(self):
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (1200, 1200), "white")
        ImageDraw.Draw(im).rectangle((300, 200, 900, 1000), fill=(200, 30, 30))
        im.save(self.p("probe.png"))
        out = self.p("tiles")
        p = run(os.path.join(CS, "image_probe.py"), self.p("probe.png"), "--tiles", out, "--json")
        r = json.loads(p.stdout)[0]
        self.assertEqual(r["pixels"], "1200x1200")
        self.assertEqual(r["background"]["kind"], "pure_white")
        self.assertFalse(r["touches_edge"])
        self.assertEqual(r["palette"][0]["hex"], "#FFFFFF")
        self.assertTrue(os.path.exists(os.path.join(out, "probe_tile_TL.jpg")))
        Image.new("RGB", (500, 500), (10, 10, 10)).save(self.p("clip.png"))
        run(os.path.join(CS, "image_probe.py"), self.p("clip.png"))
        run(os.path.join(CS, "image_probe.py"), self.p("nope.png"), ok=(2,))
        run(os.path.join(CS, "image_probe.py"), "--sheet", self.p("sheet.jpg"), self.p("probe.png"), self.p("clip.png"))

    def test_link_tools_and_marketplaces(self):
        p = run(os.path.join(CS, "amazon_link.py"), "parse", "https://www.amazon.de/dp/B0C1234567?tag=x&ref=y")
        self.assertIn("B0C1234567", p.stdout)
        run(os.path.join(CS, "amazon_link.py"), "parse", "https://www.amazon.de.evil.com/dp/B0C1234567", ok=(1,))
        run(os.path.join(CS, "amazon_link.py"), "parse", "https://www.amazon.com/gp/cart/view.html", ok=(1,))
        p = run(os.path.join(CS, "marketplaces.py"), "CA")
        self.assertIn("fr", p.stdout)
        run(os.path.join(CS, "google_link.py"), "info", "https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-abcd/edit#gid=0")

    def test_knowledge_files_present(self):
        refs = os.path.join(CS, "..", "references")
        for f in ("amazon-categories.md", "live-research.md", "image-reading.md"):
            self.assertTrue(os.path.getsize(os.path.join(refs, f)) > 1000, f)


if __name__ == "__main__":
    unittest.main()


class DesignBranch(unittest.TestCase):
    """design_branch.py keeps design output on AMZ-DESIGN (local bare remote, no network)."""

    def setUp(self):
        import shutil
        import subprocess as sp
        import tempfile
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bare = os.path.join(self.tmp, "remote.git")
        self.work = os.path.join(self.tmp, "work")
        sp.run(["git", "init", "-q", "--bare", "-b", "main", self.bare], check=True)
        sp.run(["git", "clone", "-q", self.bare, self.work], check=True, capture_output=True)
        self.g("config", "user.email", "t@example.com")
        self.g("config", "user.name", "t")
        with open(os.path.join(self.work, "README.md"), "w") as fh:
            fh.write("x\n")
        self.g("add", ".")
        self.g("commit", "-q", "-m", "init")
        self.g("branch", "-M", "main")
        self.g("push", "-q", "-u", "origin", "main")
        self.g("checkout", "-q", "-b", "claude/some-session-branch")
        self.script = os.path.join(CS, "design_branch.py")

    def g(self, *a):
        import subprocess as sp
        return sp.run(["git", *a], cwd=self.work, capture_output=True, text=True, check=True).stdout.strip()

    def run_script(self, *a, ok=(0,)):
        import subprocess as sp
        p = sp.run([sys.executable, self.script, *a], cwd=self.work, capture_output=True, text=True)
        self.assertIn(p.returncode, ok, p.stdout + p.stderr)
        return p

    def test_creates_branch_from_main_and_commits_only_design_paths(self):
        out = os.path.join(self.work, "creative-studio", "p1", "output")
        os.makedirs(out)
        with open(os.path.join(out, "01_MAIN.jpg"), "wb") as fh:
            fh.write(b"jpg")
        with open(os.path.join(self.work, "notes.txt"), "w") as fh:
            fh.write("unrelated\n")
        self.run_script("commit", "-m", "Add render")
        self.assertEqual(self.g("branch", "--show-current"), "AMZ-DESIGN")
        self.assertEqual(self.g("show", "--name-only", "--format=", "HEAD"), "creative-studio/p1/output/01_MAIN.jpg")
        self.assertIn("notes.txt", self.g("status", "--short"))  # unrelated file stays untouched
        self.assertIn("nothing to commit", self.run_script("commit", "-m", "again").stdout)

    def test_push_and_reuse_existing_remote_branch(self):
        self.run_script("ensure")
        self.run_script("push")
        self.assertIn("AMZ-DESIGN", self.g("ls-remote", "--heads", "origin"))
        self.g("checkout", "-q", "main")
        self.g("branch", "-D", "AMZ-DESIGN")
        self.g("checkout", "-q", "-b", "claude/other")
        self.assertIn("created from remote", self.run_script("ensure").stdout)
        self.assertIn("already on", self.run_script("ensure").stdout)

    def test_not_a_repo(self):
        import subprocess as sp
        p = sp.run([sys.executable, self.script, "ensure"], cwd=self.tmp, capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
