#!/usr/bin/env python3
"""Read market and performance reports the seller exports: Helium 10 Xray (category / top-100), Amazon Brand Analytics
(Search Catalog Performance, Search Query Performance brand view, Brand Share), Voice of the Customer / CX Health.

Usage:
  analytics_import.py FILE [FILE ...] [--marketplace UK] [--brand NAME] [--out analytics.json]
                      [--emit-seo-csv seo_from_sqp.csv] [--emit-competitors competitors.csv]
  analytics_import.py FILE --detect             only identify the report type

What it does
  * identifies each file by its header signature (not by file name) and says so; unknown headers -> UNKNOWN_REPORT, the agent asks;
  * reads metadata (brand, range, year, quarter in the first line of Brand Analytics CSVs; Reporting Date; marketplace from the file
    name GB_/DE_/..., from Xray product URLs or the price column currency) and reports every inference as such;
  * locale-aware numbers (DE/FR/IT/ES... "16,99", "13 666", "N/A") - the decimal convention follows the marketplace;
  * produces facts and clearly labelled relative signals. Thresholds are configuration of THIS tool (quartiles inside the file),
    not Amazon rules; nothing here proves a product fact, and competitor rows are REFERENCE_ONLY.
Report kinds
  XRAY               market snapshot of a category: price, sales and revenue spread, concentration of top brands, review barrier, title
                     length vs the 75-character rule, Item Highlight not visible here, FBA share, new entrants, candidate competitor ASINs.
  BA_CATALOG         per-ASIN search funnel (impressions -> clicks -> basket adds -> purchases): CTR / basket / conversion, price median;
                     diagnosis per ASIN against the median of the same file.
  BA_SQP_BRAND       per-query funnel of the brand: demand (search query volume), impression / click / purchase share. Opportunity queries
                     (high volume, low impression share), clicks without purchases. --emit-seo-csv writes a keyword file seo_import.py accepts.
  BA_BRAND_SHARE     brand share over quarters (impressions, clicks, purchases) with changes between quarters.
  VOC_CX             Voice of the Customer: negative-experience rate, star rating, returns, health per ASIN/SKU; LOW_SAMPLE when orders < 10.
Period handling: every file gets a period; files of the same analysis with different periods raise PERIOD_MISMATCH.
Exit code 0 = ok, 1 = unknown report / needs a human decision (flags), 2 = usage error.
"""
import argparse
import csv
import io
import json
import os
import re
import statistics
import sys
from collections import Counter
from datetime import date, datetime

try:
    from marketplaces import norm as mp_norm, info as mp_info
except ImportError:  # pragma: no cover
    mp_norm = lambda c: (c or "").upper()
    mp_info = lambda c: None

COMMA_DECIMAL = {"DE", "FR", "IT", "ES", "NL", "SE", "PL", "BE", "TR", "BR", "MX_"}
HOST_MP = {"amazon.de": "DE", "amazon.co.uk": "UK", "amazon.com": "US", "amazon.fr": "FR", "amazon.it": "IT", "amazon.es": "ES",
           "amazon.nl": "NL", "amazon.se": "SE", "amazon.pl": "PL", "amazon.ca": "CA", "amazon.com.mx": "MX", "amazon.com.br": "BR",
           "amazon.co.jp": "JP", "amazon.in": "IN", "amazon.ae": "AE", "amazon.sa": "SA", "amazon.com.au": "AU", "amazon.com.tr": "TR",
           "amazon.ie": "IE", "amazon.sg": "SG", "amazon.eg": "EG", "amazon.co.za": "ZA", "amazon.com.be": "BE"}
CUR_MP = {"€": None, "£": "UK", "$": "US"}

SOURCE_LABEL = {
    "XRAY": "Helium 10 Xray - ESTIMATES (not Amazon data)",
    "BA_CATALOG": "Amazon Brand Analytics - Amazon data for the brand and period",
    "BA_SQP_BRAND": "Amazon Brand Analytics - Amazon data for the brand and period",
    "BA_BRAND_SHARE": "Brand share table (derived from Amazon market and brand totals; ask who produced it)",
    "VOC_CX": "Amazon Voice of the Customer / CX Health - Amazon data per ASIN",
}
SIGNATURES = {
    "XRAY": {"asin", "asin sales", "asin revenue", "bsr", "review count"},
    "BA_CATALOG": {"asin title", "asin", "impressions: impressions", "clicks: clicks"},
    "BA_SQP_BRAND": {"search query", "search query volume", "impressions: brand share %"},
    "BA_BRAND_SHARE": {"impression share %", "click share %", "purchase share %"},
    "VOC_CX": {"ncx rate", "customer experience (cx) health"},
}


def num(v, comma_decimal=False):
    """Locale-aware number; None for blanks, N/A, '--', 'Not available'."""
    if v is None:
        return None
    s = str(v).replace("\xa0", "").replace(" ", "").replace("%", "").replace("€", "").replace("£", "").replace("$", "").strip()
    if s == "" or s.lower() in {"n/a", "na", "--", "-", "notavailable", "none", "nan"}:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if (comma_decimal or re.search(r",\d{1,2}$", s)) else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def read_table(path):
    """Returns (meta_line, header, rows). Brand Analytics CSVs carry a 'Key=["value"],...' metadata line before the header."""
    low = path.lower()
    if low.endswith((".xlsx", ".xlsm")):
        import openpyxl
        ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        header = [str(c).strip() if c is not None else "" for c in rows[0]]
        return "", header, [dict(zip(header, r)) for r in rows[1:] if any(c not in (None, "") for c in r)]
    text = open(path, "rb").read().decode("utf-8-sig", errors="replace")
    lines = list(csv.reader(io.StringIO(text)))
    meta = ""
    if lines and len(lines[0]) >= 1 and re.search(r'\w+=\[', ",".join(lines[0])):
        meta = ",".join(lines[0])
        lines = lines[1:]
    header = [c.strip() for c in lines[0]]
    return meta, header, [dict(zip(header, r)) for r in lines[1:] if any(c.strip() for c in r)]


def parse_meta(meta):
    return {k.strip().lower().replace(" ", "_"): v for k, v in re.findall(r'([A-Za-z ]+)=\["([^"]*)"\]', meta)}


def detect_kind(header):
    h = {c.lower() for c in header}
    best, score = None, 0
    for kind, sig in SIGNATURES.items():
        n = len(sig & h)
        if n == len(sig) or (n >= len(sig) - 1 and n > score and len(sig) > 3):
            if n > score:
                best, score = kind, n
    return best


def quart(vals):
    v = sorted(x for x in vals if x is not None)
    if len(v) < 4:
        return (v[0], statistics.median(v), v[-1]) if v else (None, None, None)
    q = statistics.quantiles(v, n=4)
    return q[0], q[1], q[2]


def pct(a, b):
    return round(100 * a / b, 2) if a is not None and b else None


# ---------------------------------------------------------------- report kinds
def do_xray(rows, mp_hint, flags):
    host = Counter()
    for r in rows:
        m = re.search(r"https?://(?:www\.)?([\w.]+)/", str(r.get("URL") or ""))
        if m:
            host[m.group(1)] += 1
    mp = HOST_MP.get(host.most_common(1)[0][0]) if host else None
    mp = mp or mp_hint
    cd = mp in COMMA_DECIMAL
    price_col = next((c for c in rows[0] if str(c).lower().startswith("price")), None)
    cur = re.search(r"([€£$])", price_col or "")
    items = []
    for r in rows:
        items.append(dict(asin=r.get("ASIN"), brand=r.get("Brand"), title=r.get("Product Details"),
                          price=num(r.get(price_col), cd), units=num(r.get("ASIN Sales"), cd), revenue=num(r.get("ASIN Revenue"), cd),
                          bsr=num(r.get("BSR"), cd), rating=num(r.get("Ratings"), cd), reviews=num(r.get("Review Count"), cd),
                          images=num(r.get("Images"), cd), title_len=num(r.get("Title Char. Count"), cd), fulfillment=r.get("Fulfillment"),
                          created=str(r.get("Creation Date") or ""), sponsored=bool(str(r.get("Sponsored") or "").strip()),
                          seller=r.get("Seller"), url=r.get("URL")))
    n = len(items)
    rev = [i["revenue"] for i in items if i["revenue"]]
    tot_rev = sum(rev) or None
    by_brand = Counter()
    for i in items:
        by_brand[i["brand"] or "?"] += i["revenue"] or 0
    top_brands = [dict(brand=b, revenue=round(v, 2), share_pct=pct(v, tot_rev)) for b, v in by_brand.most_common(8)]
    p25, p50, p75 = quart([i["price"] for i in items])
    r25, r50, r75 = quart([i["reviews"] for i in items])
    recent = []
    for i in items:
        try:
            d = datetime.strptime(i["created"], "%b %d, %Y").date()
            if (date.today() - d).days <= 365 and (i["units"] or 0) > 0:
                recent.append(dict(asin=i["asin"], brand=i["brand"], created=i["created"], units=i["units"], reviews=i["reviews"]))
        except ValueError:
            pass
    out = dict(kind="XRAY", marketplace=mp, marketplace_basis="product URLs" if host else "file name / argument", currency=cur.group(1) if cur else None,
               products=n,
               price=dict(p25=p25, median=p50, p75=p75, min=min((i["price"] for i in items if i["price"]), default=None),
                          max=max((i["price"] for i in items if i["price"]), default=None)),
               monthly_units_total=sum(i["units"] or 0 for i in items), monthly_revenue_total=round(tot_rev, 2) if tot_rev else None,
               top_brands=top_brands,
               top3_brand_share_pct=round(sum(b["share_pct"] or 0 for b in top_brands[:3]), 2) if tot_rev else None,
               review_barrier=dict(p25=r25, median=r50, p75=r75),
               rating_median=quart([i["rating"] for i in items])[1],
               images_median=quart([i["images"] for i in items])[1],
               title_over_75=sum(1 for i in items if (i["title_len"] or 0) > 75),
               fba_share_pct=pct(sum(1 for i in items if str(i["fulfillment"]).upper() == "FBA"), n),
               sponsored_share_pct=pct(sum(i["sponsored"] for i in items), n),
               new_entrants_last_12_months=recent[:10], new_entrants_count=len(recent),
               notes=["Revenue and unit figures are Helium 10 estimates, not Amazon data.",
                      "Competitor rows are REFERENCE_ONLY: never copy their titles, bullets, images or claims.",
                      "Category of this export: ask the user / read from the Category column; a file with a blank Category column does not identify the category."],
               items=items)
    if n < 20:
        flags.append(dict(code="SMALL_SAMPLE", detail=f"only {n} products: shares and quartiles are indicative"))
    return out


def funnel_diag(rows, key_fields, cd):
    """Return per-row funnel numbers and diagnosis vs the median of the same file."""
    out = []
    for r in rows:
        imp, clk, bas, pur = (num(r.get(k), cd) for k in key_fields)
        out.append(dict(imp=imp, clk=clk, bas=bas, pur=pur, ctr=pct(clk, imp), basket_rate=pct(bas, clk), cvr=pct(pur, clk)))
    return out


def do_catalog(rows, meta, flags, mp):
    cd = mp in COMMA_DECIMAL
    f = funnel_diag(rows, ("Impressions: Impressions", "Clicks: Clicks", "Basket Adds: Basket Adds", "Purchases: Purchases"), cd)
    ctr_med = statistics.median([x["ctr"] for x in f if x["ctr"] is not None] or [0])
    cvr_med = statistics.median([x["cvr"] for x in f if x["cvr"] is not None and (x["clk"] or 0) >= 5] or [0])
    items = []
    for r, x in zip(rows, f):
        diag = []
        if (x["imp"] or 0) >= 100 and x["ctr"] is not None and x["ctr"] < 0.5 * ctr_med:
            diag.append("LOW_CTR: seen but not clicked - check main image, title start, price and rating against the set")
        if (x["clk"] or 0) >= 5 and x["cvr"] is not None and x["cvr"] < 0.5 * cvr_med:
            diag.append("LOW_CONVERSION: clicked but not bought - check price, content, reviews, delivery")
        if (x["clk"] or 0) >= 5 and not x["pur"]:
            diag.append("CLICKS_NO_PURCHASE")
        if (x["imp"] or 0) < 50:
            diag.append("LOW_VISIBILITY: few impressions - check indexing, keywords, availability")
        if (x["clk"] or 0) < 5:
            diag.append("LOW_SAMPLE")
        items.append(dict(asin=r.get("ASIN"), title=r.get("ASIN title"), impressions=x["imp"], clicks=x["clk"], basket_adds=x["bas"],
                          purchases=x["pur"], ctr_pct=x["ctr"], basket_rate_pct=x["basket_rate"], conversion_pct=x["cvr"],
                          price_median=num(r.get("Impressions: Price (Median)"), cd), sales=num(r.get("Purchases: Search Traffic Sales"), cd),
                          diagnosis=diag))
    return dict(kind="BA_CATALOG", meta=meta, asins=len(items), median_ctr_pct=ctr_med, median_conversion_pct=cvr_med,
                notes=["Signals compare ASINs with the median of this file (configuration of the tool, not Amazon rules); small numbers are noisy."],
                items=items)


def do_sqp(rows, meta, flags, mp, seo_csv):
    cd = mp in COMMA_DECIMAL
    items = []
    for r in rows:
        vol = num(r.get("Search query volume"), cd)
        imp_t, imp_b = num(r.get("Impressions: Total Count"), cd), num(r.get("Impressions: Brand Count"), cd)
        clk_t, clk_b = num(r.get("Clicks: Total Count"), cd), num(r.get("Clicks: Brand Count"), cd)
        pur_t, pur_b = num(r.get("Purchases: Total Count"), cd), num(r.get("Purchases: Brand Count"), cd)
        items.append(dict(query=r.get("Search query"), score=num(r.get("Search query score"), cd), volume=vol, impressions_total=imp_t,
                          impressions_brand=imp_b, impression_share_pct=num(r.get("Impressions: Brand Share %"), cd), clicks_total=clk_t,
                          clicks_brand=clk_b, click_share_pct=num(r.get("Clicks: Brand Share %"), cd), purchases_total=pur_t, purchases_brand=pur_b,
                          purchase_share_pct=num(r.get("Purchases: Brand Share %"), cd), click_rate_pct=num(r.get("Clicks: Click Rate %"), cd),
                          purchase_rate_pct=num(r.get("Purchases: Purchase Rate %"), cd)))
    vols = [i["volume"] for i in items if i["volume"]]
    vmed = statistics.median(vols) if vols else 0
    opp = sorted([i for i in items if (i["volume"] or 0) >= vmed and (i["impression_share_pct"] or 0) < 5], key=lambda i: -(i["volume"] or 0))[:15]
    cnp = sorted([i for i in items if (i["clicks_brand"] or 0) >= 3 and not i["purchases_brand"]], key=lambda i: -(i["clicks_brand"] or 0))[:15]
    top = sorted(items, key=lambda i: -(i["volume"] or 0))[:15]
    if seo_csv:
        with open(seo_csv, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["Keyword Phrase", "Search Volume", "Brand Impression Share %", "Brand Click Share %", "Brand Purchase Share %"])
            for i in sorted(items, key=lambda i: -(i["volume"] or 0)):
                w.writerow([i["query"], i["volume"], i["impression_share_pct"], i["click_share_pct"], i["purchase_share_pct"]])
    return dict(kind="BA_SQP_BRAND", meta=meta, queries=len(items), top_queries_by_volume=top, opportunity_queries_high_volume_low_share=opp,
                clicks_without_purchase=cnp, seo_csv=seo_csv,
                notes=["Search Query Performance shows the queries behind the brand's own impressions: it is demand verified for this brand and "
                       "marketplace, not a full market keyword list (use Cerebro / Magnet for that).",
                       "Query volume is an Amazon-reported count for the period; a small count means the share figures are noisy."], )


def do_share(rows, meta, flags):
    items = []
    for r in rows:
        items.append({k.lower().replace(" ", "_").replace("%", "pct"): (num(v) if k != "Quarter" else v) for k, v in r.items()})

    def qkey(x):
        m = re.match(r"Q(\d) (\d{4})", str(x.get("quarter")))
        return (int(m.group(2)), int(m.group(1))) if m else (0, 0)
    items.sort(key=qkey)
    changes = []
    for a, b in zip(items, items[1:]):
        changes.append(dict(from_quarter=a["quarter"], to_quarter=b["quarter"],
                            impression_share_pp=round((b.get("impression_share_pct") or 0) - (a.get("impression_share_pct") or 0), 2),
                            click_share_pp=round((b.get("click_share_pct") or 0) - (a.get("click_share_pct") or 0), 2),
                            purchase_share_pp=round((b.get("purchase_share_pct") or 0) - (a.get("purchase_share_pct") or 0), 2)))
    gaps = [i["quarter"] for i in items if not i.get("brand_purchases")]
    return dict(kind="BA_BRAND_SHARE", quarters=items, quarter_changes=changes, quarters_without_brand_purchases=gaps,
                notes=["Shares are tiny when the market is large: look at the trend and at the conversion of clicks into purchases, not at the absolute share.",
                       "If quarters are missing (here no Q3/Q4 continuity check was made) say so; do not interpolate."])


def do_voc(rows, flags):
    items, cnt = [], Counter()
    for r in rows:
        orders = num(r.get("Total orders"))
        health = r.get("Customer Experience (CX) Health")
        cnt[str(health)] += 1
        diag = []
        if str(health).strip().lower() not in {"excellent", "good"}:
            diag.append("CX_HEALTH_NOT_EXCELLENT")
        if (num(r.get("NCX rate")) or 0) > 0:
            diag.append("NEGATIVE_EXPERIENCE: top reason " + str(r.get("Top NCX reason")))
        if orders is not None and orders < 10:
            diag.append("LOW_SAMPLE: fewer than 10 orders, the health status is not meaningful yet")
        items.append(dict(asin=r.get("ASIN"), sku=r.get("SKU"), product=r.get("Product name"), fulfilled_by=r.get("Fulfilled by"), orders=orders,
                          ncx_rate_pct=num(r.get("NCX rate")), ncx_orders=num(r.get("Negative Customer Experience (NCX) orders")),
                          star_rating=num(r.get("Star rating")), return_rate=r.get("Return rate"), health=health, last_updated=r.get("Last updated"),
                          diagnosis=diag))
    return dict(kind="VOC_CX", asins=len(items), health_distribution=dict(cnt), items=items,
                notes=["With very few orders per ASIN, 'Excellent' only means no complaints yet."])


def period_of(kind, meta, rows):
    if kind in ("BA_CATALOG", "BA_SQP_BRAND"):
        d = (rows[0].get("Reporting Date") if rows else None) or ""
        return dict(range=meta.get("reporting_range"), year=meta.get("select_year"), quarter=meta.get("select_quarter"), reporting_date=d)
    return {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--marketplace", default="")
    ap.add_argument("--brand", default="")
    ap.add_argument("--category", default="", help="leaf (final) category path of an Xray export, e.g. 'Pet Supplies > Dogs > Vitamins'")
    ap.add_argument("--detect", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--emit-seo-csv")
    ap.add_argument("--emit-competitors")
    a = ap.parse_args()
    results, flags = [], []
    for f in a.files:
        try:
            metaline, header, rows = read_table(f)
        except (OSError, IndexError, csv.Error) as e:
            print(f"{f}: cannot read ({e})", file=sys.stderr)
            return 2
        kind = detect_kind(header)
        meta = parse_meta(metaline)
        base = os.path.basename(f)
        codes = {mp_norm(t) for t in re.split(r"[^A-Za-z]+", base) if t.isupper() and 2 <= len(t) <= 3 and mp_info(t)}
        mp = mp_norm(a.marketplace) if a.marketplace else (codes.pop() if len(codes) == 1 else "")
        if a.detect:
            print(f"{base}: {kind or 'UNKNOWN_REPORT'}  rows={len(rows)}  meta={meta}  marketplace_hint={mp or '-'}")
            continue
        if not kind:
            flags.append(dict(code="UNKNOWN_REPORT", detail=f"{base}: headers {header[:8]} match no known report; ask the user what it is"))
            continue
        if not rows:
            flags.append(dict(code="EMPTY_REPORT", detail=base))
            continue
        fl = []
        if kind == "XRAY":
            res = do_xray(rows, mp, fl)
        elif kind == "BA_CATALOG":
            res = do_catalog(rows, meta, fl, mp)
        elif kind == "BA_SQP_BRAND":
            res = do_sqp(rows, meta, fl, mp, a.emit_seo_csv)
        elif kind == "BA_BRAND_SHARE":
            res = do_share(rows, meta, fl)
        else:
            res = do_voc(rows, fl)
        res.update(file=base, rows=len(rows), brand=meta.get("brand") or a.brand or None, period=period_of(kind, meta, rows),
                   source=SOURCE_LABEL[kind])
        if kind == "XRAY":
            col = Counter(str(r.get("Category") or "").strip() for r in rows if str(r.get("Category") or "").strip())
            cat = a.category or (col.most_common(1)[0][0] if col else "")
            res["category"] = cat or None
            res["category_scope"] = "LEAF (final) category: this product set is the market for entry benchmarks" if cat else "UNKNOWN"
            if not cat:
                fl.append(dict(code="CATEGORY_UNKNOWN", detail=f"{base}: the Xray file does not name its category; ask for the leaf (final) category path "
                                                               "(or pass --category) and record it in PROJECT.md"))
        if kind != "XRAY":
            res.setdefault("marketplace", mp or None)
            res["marketplace_basis"] = "file name / argument" if mp else "UNKNOWN - ask the user"
            if not mp:
                fl.append(dict(code="MARKETPLACE_UNKNOWN", detail=f"{base}: no marketplace in the file; ask which marketplace this report is from"))
        res["flags"] = fl
        flags.extend(fl)
        results.append(res)
    if a.detect:
        return 0
    # period consistency between Brand Analytics files
    per = {(r["kind"], json.dumps(r["period"], sort_keys=True)) for r in results if r["kind"] in ("BA_CATALOG", "BA_SQP_BRAND")}
    qs = {(p[1]) for p in per}
    if len({(json.loads(p).get("year"), json.loads(p).get("quarter")) for p in qs}) > 1:
        flags.append(dict(code="PERIOD_MISMATCH", detail="Brand Analytics files cover different periods: " + "; ".join(sorted(qs)) + " - compare only same-period files"))
    mps = {r.get("marketplace") for r in results if r.get("marketplace")}
    if len(mps) > 1:
        flags.append(dict(code="MARKETPLACE_MISMATCH", detail=f"files come from different marketplaces: {sorted(mps)}"))
    if a.emit_competitors:
        with open(a.emit_competitors, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["ASIN", "Brand", "Title", "Price", "Monthly units", "Monthly revenue", "Reviews", "Rating", "Use"])
            for r in results:
                if r["kind"] == "XRAY":
                    for i in r["items"]:
                        w.writerow([i["asin"], i["brand"], i["title"], i["price"], i["units"], i["revenue"], i["reviews"], i["rating"], "REFERENCE_ONLY"])
    payload = dict(generated=date.today().isoformat(), reports=results, flags=flags)
    if a.out:
        json.dump(payload, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for r in results:
        head = {k: v for k, v in r.items() if k not in ("items", "quarters", "top_queries_by_volume", "opportunity_queries_high_volume_low_share",
                                                        "clicks_without_purchase", "new_entrants_last_12_months", "notes")}
        print(f"== {r['kind']} {r['file']}  [{r['source']}]")
        print(json.dumps(head, ensure_ascii=False, indent=1)[:1800])
    for fl in flags:
        print(f"FLAG {fl['code']}: {fl['detail']}")
    return 1 if flags else 0


if __name__ == "__main__":
    sys.exit(main())
