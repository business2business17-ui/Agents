import csv
import zipfile
from datetime import date
from pathlib import Path

import pytest

from mia.importers import read_cerebro, read_xray
from mia.importers.helium10 import badge_bounds, detect_decimal, parse_date, parse_number
from mia.importers.xlsx import read_table
from mia.niche import (NicheDefinition, brand_tokens, build_clusters, build_input, clean_rows,
                       keyword_metrics, market_metrics)
from mia.pipeline import analyze

ROOT = Path(__file__).resolve().parent.parent
AS_OF = date(2026, 10, 20)

XRAY_HEADER = ["Display Order", "Image", "Product Details", "ASIN", "URL", "Image URL", "Brand", "Price  €",
               "Parent Level Sales", "ASIN Sales", "Recent Purchases", "Parent Level Revenue", "ASIN Revenue",
               "Title Char. Count", "BSR", "Seller Country/Region", "Fees  €", "Active Sellers", "Ratings",
               "Review Count", "Images", "Review velocity", "Buy Box", "Category", "Size Tier", "Fulfillment",
               "Dimensions", "Weight", "ABA Most Clicked", "Creation Date", "Sponsored", "Best Seller",
               "Seller Age (mo)", "Seller"]


def xrow(asin, title, brand, price, units, badge, fulfillment="FBA", created="Jan 5, 2026", reviews="120",
         fees="6,10", revenue=None):
    rev = revenue if revenue is not None else f"{float(price.replace(',', '.')) * units:.2f}".replace(".", ",")
    return {"Display Order": "1.", "Product Details": title, "ASIN": asin,
            "URL": f"https://www.amazon.de/dp/{asin}?psc=1", "Brand": brand, "Price  €": price,
            "Parent Level Sales": f"{units}", "ASIN Sales": f"{units:,}".replace(",", " "),
            "Recent Purchases": badge, "Parent Level Revenue": rev, "ASIN Revenue": rev, "BSR": "100",
            "Seller Country/Region": "AMZ" if fulfillment == "AMZ" else "DE", "Fees  €": fees,
            "Active Sellers": "1", "Ratings": "4,5", "Review Count": reviews, "Images": "7",
            "Review velocity": "N/A", "Buy Box": "Amazon" if fulfillment == "AMZ" else brand,
            "Category": "Beauty", "Size Tier": "Small Parcel", "Fulfillment": fulfillment,
            "Dimensions": "13,00 x 5,40 x 5,60 cm", "Weight": "0,30", "ABA Most Clicked": "N/A",
            "Creation Date": created, "Sponsored": "", "Best Seller": "No", "Seller Age (mo)": "40",
            "Seller": "Amazon" if fulfillment == "AMZ" else brand}


ROWS = [
    xrow("B0AAAAAAA1", "Bräunungsbeschleuniger Creme Solarium 200 ml", "SunCo", "18,48", 3000, "1 000"),
    xrow("B0AAAAAAA2", "Tanning Accelerator Oil for Sunbed", "SunCo", "16,00", 900, "900"),
    xrow("B0AAAAAAA3", "Dark Tanning Oil 200ml", "Hawaiian Tropic", "5,87", 1500, "800", fulfillment="AMZ"),
    xrow("B0AAAAAAA4", "Self Tanning Mousse 200 ml", "Bondi", "15,93", 400, "200"),
    xrow("B0AAAAAAA5", "Tanning Accelerator Cream Choco", "Cocos", "2 342,00", 100, "50",
         revenue="2 342,00"),                        # цена в центах (×100): выручка/шт. = 23,42
    xrow("B0AAAAAAA7", "Gift box body lotion", "Promo", "24,00", 50, "N/A",
         revenue="600,00", created="Jan 1, 2020"),        # цена ×2 к выручке/шт.: акция, не ошибка
    xrow("B0AAAAAAA6", "Tanning accelerator lotion new", "NewBrand", "14,00", 60, "N/A", created="Mar 1, 2026"),
]


def write_csv(path, rows, header=XRAY_HEADER):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


@pytest.fixture
def xray_csv(tmp_path):
    p = tmp_path / "xray.csv"
    write_csv(p, ROWS)
    return p


@pytest.fixture
def cerebro_csv(tmp_path):
    p = tmp_path / "cerebro.csv"
    header = ["Keyword Phrase", "ABA Total Click Share", "ABA Total Conv. Share", "Keyword Sales",
              "Search Volume", "Search Volume Trend", "Competing Products", "CPR", "Title Density", "B0AAAAAAA1"]
    rows = [
        {"Keyword Phrase": "bräunungsbeschleuniger", "ABA Total Click Share": "22.2", "Search Volume": "4000",
         "Search Volume Trend": "-20", "B0AAAAAAA1": "3"},
        {"Keyword Phrase": "solarium creme", "Search Volume": "1000", "Search Volume Trend": "10"},
        {"Keyword Phrase": "bräunungsöl", "Search Volume": "2000", "Search Volume Trend": "0"},
        {"Keyword Phrase": "hawaiian tropic öl", "Search Volume": "3000", "Search Volume Trend": "0"},
    ]
    write_csv(p, rows, header)
    return p


# ---------- разбор значений

@pytest.mark.parametrize("raw,dec,val", [
    ("13 138", ",", 13138), ("29 471,08", ",", 29471.08), ("2,45", ",", 2.45), ("N/A", ",", None),
    ("", ",", None), ("1,234.50", ".", 1234.5), (17, ",", 17.0), ("-30", ",", -30.0),
])
def test_parse_number(raw, dec, val):
    assert parse_number(raw, dec) == val


def test_detect_decimal():
    assert detect_decimal(["2,45", "13 138", "29 471,08"]) == ","
    assert detect_decimal(["2.45", "1,234.50"]) == "."


def test_parse_date_and_badge():
    assert parse_date("May 31, 2020") == date(2020, 5, 31)
    assert parse_date("N/A") is None
    assert badge_bounds(1000) == (1000, 2000) and badge_bounds(900) == (900, 1000)
    assert badge_bounds(None) is None


def test_xlsx_reader_shared_inline_sparse(tmp_path):
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    p = tmp_path / "t.xlsx"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook {ns}><sheets><sheet name="S" sheetId="1"/></sheets></workbook>')
        z.writestr("xl/sharedStrings.xml", f'<sst {ns}><si><t>ASIN</t></si><si><t>Brand</t></si>'
                                           f'<si><t>B0AAAAAAA1</t></si></sst>')
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<worksheet {ns}><sheetData>'
                   f'<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c>'
                   f'<c r="C1" t="inlineStr"><is><t>Sales</t></is></c></row>'
                   f'<row r="2"><c r="A2" t="s"><v>2</v></c><c r="C2"><v>17</v></c></row>'
                   f'</sheetData></worksheet>')
    assert read_table(str(p)) == [{"ASIN": "B0AAAAAAA1", "Brand": None, "Sales": "17"}]


# ---------- импорт и качество

def test_read_xray_csv(xray_csv):
    rows = read_xray(str(xray_csv))
    r = rows[0]
    assert (r.marketplace, r.currency, r.price, r.units, r.badge_floor) == ("DE", "EUR", 18.48, 3000, 1000)
    assert r.dimensions_cm == [13.0, 5.4, 5.6] and r.weight_kg == 0.3 and r.created == date(2026, 1, 5)
    assert rows[2].is_amazon_retail and not rows[0].is_amazon_retail


def test_price_anomaly_fixed(xray_csv):
    rows, q = clean_rows(read_xray(str(xray_csv)))
    assert q.price_fixed == 1 and q.price_gap == 1
    assert next(r for r in rows if r.asin == "B0AAAAAAA5").price == 23.42     # ×100 → /100
    assert next(r for r in rows if r.asin == "B0AAAAAAA7").price == 24.0      # расхождение — только пометка
    assert {i["issue"] for i in q.issues} == {"price_x100", "price_asp_gap"}


def test_read_cerebro_percent_shares(cerebro_csv):
    kw = read_cerebro(str(cerebro_csv))
    assert kw[0].aba_click_share == pytest.approx(0.222)
    assert kw[0].asin_ranks == {"B0AAAAAAA1": 3}


# ---------- определение ниши и метрики

DEF = NicheDefinition("t", include_any=["accelerat", "bräunungs", "tanning oil"], exclude_any=["self tan"])


def test_niche_definition_reasons(xray_csv):
    rows, _ = clean_rows(read_xray(str(xray_csv)))
    inc, exc, _ = DEF.apply(rows)
    assert {r.asin for r in inc} == {"B0AAAAAAA1", "B0AAAAAAA2", "B0AAAAAAA3", "B0AAAAAAA5", "B0AAAAAAA6"}
    assert exc == [{"asin": "B0AAAAAAA4", "title": "Self Tanning Mousse 200 ml",
                    "reason": "нет ни одного include-слова в title"},
                   {"asin": "B0AAAAAAA7", "title": "Gift box body lotion",
                    "reason": "нет ни одного include-слова в title"}]


def test_market_metrics_badge_and_concentration(xray_csv):
    rows, _ = clean_rows(read_xray(str(xray_csv)))
    inc, _, _ = DEF.apply(rows)
    mm = market_metrics(inc, AS_OF, rows_exported=len(rows))
    rv = mm["revenue_month"]
    # SunCo 3000 шт. при бейдже 1K+ (1000–1999): Helium выше интервала бейджа
    assert rv["base"] == pytest.approx(3000 * 18.48 + 900 * 16 + 1500 * 5.87 + 2342 + 60 * 14)
    assert rv["low"] < rv["base"]
    b = mm["badge_check"]
    assert b["helium_above_badge"] > 0.5
    assert b["divergence"] == pytest.approx((rv["base"] - b["revenue_badge_consistent"]) / b["revenue_badge_consistent"])
    assert b["revenue_badge_consistent"] == pytest.approx(
        1999 * 18.48 + 900 * 16 + 899 * 5.87 + 99 * 23.42 + 60 * 14)    # 1500 при 800+ → не выше 899
    assert mm["brands"] == 4 and mm["cr"][3] == pytest.approx(1 - 60 * 14 / rv["base"])   # без NewBrand
    assert mm["amazon_retail_share"] == pytest.approx(1500 * 5.87 / rv["base"])
    assert sorted(mm["cohort"]["units_at_month"]) == [60, 100, 900, 1500, 3000]   # все созданы 3–18 мес. назад


def test_keywords_nonbranded_and_clusters(xray_csv, cerebro_csv):
    rows, _ = clean_rows(read_xray(str(xray_csv)))
    kw = read_cerebro(str(cerebro_csv))
    brands = brand_tokens(rows)
    km = keyword_metrics(kw, brands)
    assert km["nonbranded_share"] == pytest.approx(7000 / 10000)       # «hawaiian tropic öl» — брендовый
    a = {"click_share": {"low": 0.01, "base": 0.02, "high": 0.04}, "cvr": {"low": 0.08, "base": 0.1, "high": 0.12}}
    clusters, rest = build_clusters(kw, brands, {"acc": ["beschleuniger", "solarium"], "oil": ["öl"]}, a)
    assert [(c["cluster_id"], c["search_volume_month"]) for c in clusters] == [("acc", 5000), ("oil", 2000)]
    assert rest == []


# ---------- сквозной прогон

def _user(**over):
    u = {
        "business_model": "private_label", "category": "cosmetics",
        "tax": {"vat_rate": 0.19, "price_includes_vat": True},
        "fees": {"referral": {"kind": "whole", "tiers": [[10, 0.08], [None, 0.15]], "min_fee": 0.30},
                 "fulfillment_fee": None, "checked_at": "2026-10-01"},
        "costs": {"cogs": 2.8, "cogs_status": "assumed"},
        "keyword_clusters": {"acc": ["beschleuniger", "solarium"], "oil": ["öl"]},
        "keyword_assumptions": {"click_share": {"low": 0.01, "base": 0.02, "high": 0.04},
                                "cvr": {"low": 0.08, "base": 0.1, "high": 0.12}},
        "ppc": {"budget_month": 1000, "cpc": {"low": 0.95, "base": 0.75, "high": 0.6},
                "cvr_ads": {"low": 0.08, "base": 0.1, "high": 0.12}},
        "scenarios": {"prices": {"conservative": 14.99, "base": 16.99, "optimistic": 18.99}},
        "launch": {"lead_time": {"production_days": 30, "transit_days": 35}, "deposit_pct": 0.3, "moq": 500,
                   "fixed_launch_costs": 2000},
        "budget": 15000,
    }
    u.update(over)
    return u


def test_build_input_and_analyze(xray_csv, cerebro_csv):
    rows = read_xray(str(xray_csv))
    kw = read_cerebro(str(cerebro_csv))
    inp = build_input(DEF, rows, _user(), keywords=kw, as_of=AS_OF)
    assert inp["marketplace"] == "DE" and inp["niche_definition_id"] == "t@v1"
    assert inp["market"]["source_divergence"] > 0.25                 # бейдж как второй источник → не HIGH
    assert inp["fees"]["fulfillment_fee"] > 0                         # FBA fee из Fees − referral
    assert [c["cluster_id"] for c in inp["keywords"]["clusters"]] == ["acc", "oil"]
    pkg = analyze(inp)
    assert pkg["decision"]["status"] in ("HOLD", "NO-GO", "TEST")
    assert pkg["decision"]["confidence"] == "LOW"                    # ASSUMED_COGS
    assert pkg["import"]["quality"]["price_fixed"] == 1
    assert any("бейджа Amazon" in w for w in pkg["warnings"])


def test_clusters_only_for_hypothesis(xray_csv, cerebro_csv):
    inp = build_input(DEF, read_xray(str(xray_csv)), _user(keyword_clusters_only=["oil"]),
                      keywords=read_cerebro(str(cerebro_csv)), as_of=AS_OF)
    assert [c["cluster_id"] for c in inp["keywords"]["clusters"]] == ["oil"]


def test_without_keyword_assumptions_is_insufficient_data(xray_csv, cerebro_csv):
    user = _user()
    del user["keyword_assumptions"]
    inp = build_input(DEF, read_xray(str(xray_csv)), user, keywords=read_cerebro(str(cerebro_csv)), as_of=AS_OF)
    pkg = analyze(inp)
    assert pkg["decision"]["status"] == "INSUFFICIENT DATA"
    assert "keywords.clusters" in pkg["decision"]["how_to_get"]


# ---------- реальные выгрузки (если папка XRAY на месте)

REAL = ROOT / "XRAY"


@pytest.mark.skipif(not REAL.exists(), reason="нет папки XRAY с реальными выгрузками")
def test_real_exports_parse():
    xr = sorted(REAL.glob("*xray*.xlsx"))
    cb = sorted(REAL.glob("*cerebro*.xlsx"))
    assert xr and cb
    for f in xr:
        rows = read_xray(str(f))
        assert rows and all(r.marketplace in ("DE", "UK") for r in rows)
        assert sum(r.units is not None for r in rows) / len(rows) > 0.9
    for f in cb:
        kw = read_cerebro(str(f))
        assert kw and all(k.phrase for k in kw)


@pytest.mark.skipif(not REAL.exists(), reason="нет папки XRAY с реальными выгрузками")
def test_real_example_config_runs():
    from mia.xray_run import run_file
    res = run_file(str(ROOT / "examples" / "de_tanning_xray.json"))
    assert [t["id"] for t in res["summary"]] == ["niche", "h1_accelerator_cream", "h2_budget_oil",
                                                 "h3_carrot_oil", "h4_tanning_stick"]
    assert all(t["status"] != "INSUFFICIENT DATA" for t in res["summary"])
    assert res["summary"][-1]["evidence"] == "white_space"            # формата нет в выдаче — не спрос
    assert res["portfolio"]["wave_1"] == []


# ---------- скрининг папки и автокатегория

def test_scan_folder_detects_duplicates(tmp_path):
    from mia.scan import scan_folder
    write_csv(tmp_path / "a xray.csv", ROWS)
    write_csv(tmp_path / "b xray.csv", ROWS)
    res = scan_folder(str(tmp_path), AS_OF, pattern="*xray*.csv")
    assert [r["duplicate_of"] for r in res] == [None, "a xray.csv"]
    assert res[0]["category"] == "cosmetics" and res[0]["marketplace"] == "DE"


def test_build_input_detects_category_and_default_referral(xray_csv, cerebro_csv):
    user = _user()
    del user["category"]
    del user["fees"]["referral"]
    inp = build_input(DEF, read_xray(str(xray_csv)), user, keywords=read_cerebro(str(cerebro_csv)), as_of=AS_OF)
    assert inp["category"] == "cosmetics"
    assert inp["fees"]["referral"]["tiers"] == [[10, 0.08], [None, 0.15]]
    assert any("стартовая ставка" in w for w in inp["_import"]["warnings"])
