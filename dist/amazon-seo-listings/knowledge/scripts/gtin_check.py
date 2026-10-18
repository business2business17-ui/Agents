#!/usr/bin/env python3
"""GTIN / EAN / UPC check-digit validation and duplicate detection (no network, no guessing).

Usage:
  gtin_check.py 4006381333931 036000291452          # one or more codes
  gtin_check.py --batch products.csv [--out ids.json]
      columns (any case, flexible): sku, ean, upc, gtin, asin, gtin_exempt, product_name
Statuses per record: GTIN_VALID | GTIN_INVALID | GTIN_EXEMPT | GTIN_MISSING | IDENTIFIER_DUPLICATE | IDENTIFIER_CONFLICT
Never repairs, pads or invents a code. A code that lost leading zeros (e.g. 11-digit UPC, 12-digit EAN-13 body)
is reported as GTIN_INVALID with a hint; the user decides.
Exit code 0 = no invalid/conflict, 1 = something to review.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict


def check_digit(body: str) -> int:
    total = 0
    for i, ch in enumerate(reversed(body)):
        total += int(ch) * (3 if i % 2 == 0 else 1)
    return (10 - total % 10) % 10


def classify(code):
    raw = "" if code is None else str(code).strip()
    if raw == "":
        return dict(code=None, status="GTIN_MISSING", type=None, hint=None)
    if raw.endswith(".0") and raw[:-2].isdigit():
        return dict(code=raw, status="GTIN_INVALID", type=None,
                    hint="looks like a number exported from Excel (trailing .0); re-export identifiers as text")
    if "e" in raw.lower() and any(ch.isdigit() for ch in raw) and not raw.isdigit():
        return dict(code=raw, status="GTIN_INVALID", type=None, hint="scientific notation: identifier corrupted by Excel")
    if not raw.isdigit():
        return dict(code=raw, status="GTIN_INVALID", type=None, hint="contains non-digits")
    n = len(raw)
    types = {8: "GTIN-8", 12: "UPC-A", 13: "EAN-13", 14: "GTIN-14"}
    if n not in types:
        hint = None
        if n == 11:
            hint = "11 digits: a UPC-A may have lost a leading zero; confirm with the source, do not pad automatically"
        return dict(code=raw, status="GTIN_INVALID", type=None, hint=hint or f"{n} digits; expected 8, 12, 13 or 14")
    ok = check_digit(raw[:-1]) == int(raw[-1])
    return dict(code=raw, status="GTIN_VALID" if ok else "GTIN_INVALID", type=types[n],
                hint=None if ok else f"check digit should be {check_digit(raw[:-1])}")


def truthy(v):
    return str(v).strip().lower() in ("1", "true", "yes", "y", "да", "ja", "oui", "si", "sí")


def lowkeys(row):
    return {str(k).strip().lower().replace(" ", "_"): v for k, v in row.items() if k is not None}


def batch(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [lowkeys(r) for r in csv.DictReader(f)]
    out, by_code = [], defaultdict(list)
    for i, r in enumerate(rows, start=2):
        sku = r.get("sku") or r.get("seller_sku") or r.get("item_sku") or f"row{i}"
        ids = {k: (r.get(k) or "").strip() for k in ("ean", "upc", "gtin") if (r.get(k) or "").strip()}
        exempt = truthy(r.get("gtin_exempt", ""))
        rec = dict(sku=sku, row=i, identifiers={}, gtin_exempt=exempt, asin=(r.get("asin") or "").strip() or None,
                   product_name=r.get("product_name") or r.get("title") or None)
        if exempt:
            rec["status"] = "GTIN_EXEMPT" if not ids else "IDENTIFIER_CONFLICT"
            if ids:
                rec["hint"] = "gtin_exempt=true but identifiers also present: confirm which applies"
        elif not ids:
            rec["status"] = "GTIN_MISSING"
        else:
            sts = []
            for k, v in ids.items():
                c = classify(v)
                rec["identifiers"][k] = c
                sts.append(c["status"])
                if c["status"] == "GTIN_VALID":
                    by_code[c["code"].lstrip("0")].append(sku)
            valid = {c["code"].lstrip("0") for c in rec["identifiers"].values() if c["status"] == "GTIN_VALID"}
            rec["status"] = "GTIN_INVALID" if "GTIN_INVALID" in sts else "GTIN_VALID"
            if len(valid) > 1:
                rec["status"] = "IDENTIFIER_CONFLICT"
                rec["hint"] = "EAN/UPC/GTIN columns hold different codes for the same SKU"
        out.append(rec)
    dups = {code: skus for code, skus in by_code.items() if len(set(skus)) > 1}
    for rec in out:
        for c in rec["identifiers"].values():
            if c["status"] == "GTIN_VALID" and c["code"].lstrip("0") in dups:
                rec["status"] = "IDENTIFIER_DUPLICATE"
                rec["hint"] = f"same code on SKUs {sorted(set(dups[c['code'].lstrip('0')]))}"
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("codes", nargs="*")
    ap.add_argument("--batch")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.batch:
        res = batch(a.batch)
        summary = defaultdict(int)
        for r in res:
            summary[r["status"]] += 1
        text = json.dumps(dict(summary=dict(summary), records=res), ensure_ascii=False, indent=2)
        bad = any(r["status"] not in ("GTIN_VALID", "GTIN_EXEMPT") for r in res)
    elif a.codes:
        res = [classify(c) for c in a.codes]
        text = json.dumps(res, ensure_ascii=False, indent=2)
        bad = any(r["status"] != "GTIN_VALID" for r in res)
    else:
        ap.error("give codes or --batch")
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")
        print(f"wrote {a.out}")
    else:
        print(text)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
