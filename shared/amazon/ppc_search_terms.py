#!/usr/bin/env python3
"""Search term report -> campaign summary, bid recommendations, negative candidates, harvest candidates.

Input: Amazon Ads search term report (CSV or XLSX, any marketplace; English headers, currency symbols and
thousands separators are normalized). Output: text summary, --json, and --out recommendations.xlsx.

Rules (all thresholds are options; defaults are in references/03 and 04):
  harvest   orders >= --min-orders and ACOS <= target and clicks >= --min-clicks (auto / broad / phrase sources)
  negative  clicks >= --neg-clicks and orders == 0 and spend >= --neg-spend-x * target CPA (CPA = target ACOS * AOV)
  bid       value based: suggested = RPC * target ACOS (RPC = sales / clicks), capped by --max-cpc, floored by --min-bid,
            one step at most +-30 %; targets under --min-clicks go to Watch
Usage:
  ppc_search_terms.py report.xlsx --target-acos 30 [--break-even-acos 45] [--max-cpc 1.2] [--brand "acme,acme pro"] [--out rec.xlsx] [--json]
Exit 0 = analysis done, 2 = usage / input error.
"""
import argparse
import csv
import json
import re
import sys
from collections import OrderedDict

ALIASES = {
    "campaign": ["campaign name", "campaign"],
    "ad_group": ["ad group name", "ad group"],
    "targeting": ["targeting", "keyword", "customer targeting", "target"],
    "match_type": ["match type"],
    "term": ["customer search term", "search term"],
    "impressions": ["impressions"],
    "clicks": ["clicks"],
    "spend": ["spend", "cost"],
    "sales": ["7 day total sales", "14 day total sales", "total sales", "sales", "7 day total sales (#)",
              "7 day total sales ($)", "7 day total sales (£)", "7 day total sales (€)"],
    "orders": ["7 day total orders (#)", "14 day total orders (#)", "7 day total orders", "total orders", "orders",
               "purchases"],
}


def norm_header(h):
    h = re.sub(r"\s+", " ", str(h or "").strip().lower())
    return re.sub(r"\s*\((?:[$£€¥]|[a-z]{3})\)$", "", h) if "sales" in h else h


def num(v):
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d,.\-]", "", str(v))
    if not s or s in "-.,":
        return 0.0
    if "," in s and "." in s:
        s = s.replace(",", "") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", ".")
    elif "," in s:
        head, tail = s.rsplit(",", 1)
        s = head.replace(",", "") + "." + tail if len(tail) <= 2 else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def load_rows(path):
    if path.lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        rows = []
        for ws in wb.worksheets:
            vals = list(ws.iter_rows(values_only=True))
            for i, r in enumerate(vals[:15]):
                if r and any(norm_header(c) in ("customer search term", "search term") for c in r):
                    hdr = [norm_header(c) for c in r]
                    rows += [dict(zip(hdr, rr)) for rr in vals[i + 1:] if rr and any(c is not None for c in rr)]
                    break
        return rows
    with open(path, encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t") if sample else csv.excel
        rd = csv.reader(fh, dialect)
        hdr = [norm_header(c) for c in next(rd, [])]
        return [dict(zip(hdr, r)) for r in rd if r]


def pick(row, field):
    for a in ALIASES[field]:
        if a in row and row[a] not in (None, ""):
            return row[a]
    for k, v in row.items():
        if field in ("sales", "orders") and k.startswith(("7 day total " + field, "14 day total " + field)):
            return v
    return None


def sd(a, b):
    return a / b if b else None


def analyze(rows, a):
    recs = []
    for r in rows:
        rec = {f: pick(r, f) for f in ALIASES}
        if not rec["term"]:
            continue
        for f in ("impressions", "clicks", "spend", "sales", "orders"):
            rec[f] = num(rec[f])
        for f in ("campaign", "ad_group", "targeting", "match_type", "term"):
            rec[f] = str(rec[f] or "").strip()
        recs.append(rec)
    if not recs:
        raise SystemExit("no rows with a 'Customer Search Term' column found")
    target = a.target_acos / 100.0
    tot_spend = sum(x["spend"] for x in recs)
    tot_orders = sum(x["orders"] for x in recs)
    tot_sales = sum(x["sales"] for x in recs)
    aov = a.aov or (sd(tot_sales, tot_orders) or 0)
    target_cpa = target * aov
    brands = [b.strip().lower() for b in (a.brand or "").split(",") if b.strip()]

    camp = OrderedDict()
    for x in recs:
        c = camp.setdefault(x["campaign"], dict(campaign=x["campaign"], impressions=0, clicks=0, spend=0.0, sales=0.0, orders=0))
        for f in ("impressions", "clicks", "spend", "sales", "orders"):
            c[f] += x[f]
    summary = []
    for c in camp.values():
        c.update(acos=sd(c["spend"], c["sales"]), roas=sd(c["sales"], c["spend"]), ctr=sd(c["clicks"], c["impressions"]),
                 cvr=sd(c["orders"], c["clicks"]), cpc=sd(c["spend"], c["clicks"]))
        summary.append(c)

    exact_terms = {x["targeting"].lower() for x in recs if x["match_type"].lower() == "exact"}
    # per search term across campaigns, to avoid promoting the same term twice
    terms = OrderedDict()
    for x in recs:
        t = terms.setdefault(x["term"].lower(), dict(term=x["term"], clicks=0, orders=0, spend=0.0, sales=0.0, campaigns=set()))
        for f in ("clicks", "orders", "spend", "sales"):
            t[f] += x[f]
        t["campaigns"].add(x["campaign"])

    def is_brand(term):
        return any(b in term.lower() for b in brands)

    harvest, negatives, watch = [], [], []
    for x in recs:
        acos = sd(x["spend"], x["sales"])
        is_asin = bool(re.fullmatch(r"b0[a-z0-9]{8}", x["term"].lower()))
        if (x["match_type"].lower() != "exact" and x["orders"] >= a.min_orders and x["clicks"] >= a.min_clicks
                and acos is not None and acos <= target and x["term"].lower() not in exact_terms):
            cpc = sd(x["spend"], x["clicks"]) or 0
            bid = round(min(cpc * 1.1, a.max_cpc) if a.max_cpc else cpc * 1.1, 2)
            harvest.append(dict(campaign=x["campaign"], ad_group=x["ad_group"], term=x["term"], clicks=x["clicks"], orders=x["orders"],
                                spend=round(x["spend"], 2), sales=round(x["sales"], 2), acos=round(acos, 4), start_bid=bid,
                                route="product targeting (ASIN)" if is_asin else "Manual Exact",
                                action="add as exact; add negative exact in source campaign"))
        elif x["orders"] == 0 and x["clicks"] >= a.neg_clicks and x["spend"] >= a.neg_spend_x * target_cpa:
            if is_brand(x["term"]):
                watch.append(dict(campaign=x["campaign"], term=x["term"], clicks=x["clicks"], spend=round(x["spend"], 2),
                                  reason="matches --brand: not negated automatically"))
                continue
            other = terms[x["term"].lower()]
            if other["orders"] > 0:
                watch.append(dict(campaign=x["campaign"], term=x["term"], clicks=x["clicks"], spend=round(x["spend"], 2),
                                  reason="term converts in another campaign: fix routing instead of negating"))
                continue
            negatives.append(dict(campaign=x["campaign"], ad_group=x["ad_group"], term=x["term"], clicks=x["clicks"], spend=round(x["spend"], 2),
                                  match="negative exact", reason=f"{int(x['clicks'])} clicks, 0 orders, spend {x['spend']:.2f}"))
        elif 0 < x["clicks"] < a.min_clicks and x["orders"] >= 1:
            watch.append(dict(campaign=x["campaign"], term=x["term"], clicks=x["clicks"], spend=round(x["spend"], 2),
                              reason="converting but too few clicks: re-check in 7 days"))

    tg = OrderedDict()
    for x in recs:
        k = (x["campaign"], x["ad_group"], x["targeting"], x["match_type"])
        t = tg.setdefault(k, dict(campaign=k[0], ad_group=k[1], targeting=k[2], match_type=k[3], clicks=0, orders=0, spend=0.0, sales=0.0))
        for f in ("clicks", "orders", "spend", "sales"):
            t[f] += x[f]
    bids = []
    for t in tg.values():
        acos, cpc, rpc = sd(t["spend"], t["sales"]), sd(t["spend"], t["clicks"]), sd(t["sales"], t["clicks"])
        row = dict(t, spend=round(t["spend"], 2), sales=round(t["sales"], 2), acos=None if acos is None else round(acos, 4),
                   avg_cpc=None if cpc is None else round(cpc, 2))
        if t["clicks"] < a.min_clicks and not (t["orders"] == 0 and t["clicks"] >= 10):
            row.update(action="watch", suggested_bid=None, reason=f"{int(t['clicks'])} clicks < {a.min_clicks}: not enough data")
        elif t["orders"] == 0:
            new = round(max(a.min_bid, cpc * 0.7), 2)
            row.update(action="decrease", suggested_bid=new, reason="no orders on 10+ clicks: cut about 30 %, check relevance")
        else:
            sug = rpc * target
            lo, hi = cpc * 0.7, cpc * 1.3
            new = max(a.min_bid, min(max(sug, lo), hi))
            if a.max_cpc:
                new = min(new, a.max_cpc)
            new = round(new, 2)
            if abs(new - cpc) / cpc < 0.05:
                row.update(action="keep", suggested_bid=round(cpc, 2), reason="within 5 % of the value-based bid")
            else:
                row.update(action="increase" if new > cpc else "decrease", suggested_bid=new,
                           reason=f"RPC {rpc:.2f} x target ACOS {a.target_acos:.0f} % = {sug:.2f}; step limited to +-30 % of avg CPC")
        bids.append(row)
    return dict(
        meta=dict(rows=len(recs), spend=round(tot_spend, 2), sales=round(tot_sales, 2), orders=int(tot_orders),
                  acos=sd(tot_spend, tot_sales), target_acos=target, break_even_acos=(a.break_even_acos / 100 if a.break_even_acos else None),
                  aov=round(aov, 2), target_cpa=round(target_cpa, 2)),
        campaign_summary=summary, bid_recommendations=bids, negative_keywords=negatives, keyword_harvest=harvest, watch=watch)


def write_xlsx(res, path):
    from openpyxl import Workbook
    wb = Workbook()
    wb.remove(wb.active)
    for name, key in (("Campaign Summary", "campaign_summary"), ("Bid Recommendations", "bid_recommendations"),
                      ("Negative Keywords", "negative_keywords"), ("Keyword Harvest", "keyword_harvest"), ("Watch", "watch")):
        ws = wb.create_sheet(name)
        rows = res[key]
        if not rows:
            ws.append(["(none)"])
            continue
        cols = list(rows[0].keys())
        ws.append(cols)
        for r in rows:
            ws.append([("" if r.get(c) is None else r.get(c)) for c in cols])
    wb.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--target-acos", type=float, required=True, help="percent, e.g. 30")
    ap.add_argument("--break-even-acos", type=float, help="percent, shown in the summary")
    ap.add_argument("--aov", type=float, help="average order value; default from the report")
    ap.add_argument("--max-cpc", type=float, default=0.0)
    ap.add_argument("--min-bid", type=float, default=0.02)
    ap.add_argument("--min-clicks", type=int, default=20)
    ap.add_argument("--min-orders", type=int, default=2)
    ap.add_argument("--neg-clicks", type=int, default=12)
    ap.add_argument("--neg-spend-x", type=float, default=1.5)
    ap.add_argument("--brand", help="comma separated own brand terms (never negated automatically)")
    ap.add_argument("--out", help="write recommendations.xlsx")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.target_acos <= 0:
        print("--target-acos must be > 0", file=sys.stderr)
        return 2
    try:
        res = analyze(load_rows(a.report), a)
    except (OSError, SystemExit) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if a.out:
        write_xlsx(res, a.out)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    else:
        m = res["meta"]
        acos = "N/A" if m["acos"] is None else f"{m['acos']:.1%}"
        print(f"rows {m['rows']}  spend {m['spend']}  sales {m['sales']}  orders {m['orders']}  ACOS {acos}  target {m['target_acos']:.0%}")
        print(f"bids: {sum(1 for b in res['bid_recommendations'] if b['action'] in ('increase', 'decrease'))} to change, "
              f"{sum(1 for b in res['bid_recommendations'] if b['action'] == 'watch')} watch | negatives {len(res['negative_keywords'])} | "
              f"harvest {len(res['keyword_harvest'])} | watch {len(res['watch'])}")
        for h in res["keyword_harvest"][:10]:
            print(f"  HARVEST  {h['term']}  ({h['orders']:.0f} orders, ACOS {h['acos']:.0%}) -> bid {h['start_bid']}")
        for n in res["negative_keywords"][:10]:
            print(f"  NEGATIVE {n['term']}  ({n['reason']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
