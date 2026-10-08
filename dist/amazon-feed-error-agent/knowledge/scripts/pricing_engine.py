#!/usr/bin/env python3
"""Deterministic Amazon pricing engine - shared policy 2026-10-08-v3.

Policy (see references/shared-pricing-and-updates.md):
  S = user Sale Price (preserved unchanged)
  P = Standard / Your Price = ROUND_HALF_UP(S / (1 - d))           d = 0.10
  B = Business Price       = ROUND_HALF_UP(P * (1 - b))            b = 0.10, from the ROUNDED P
  List Price / MSRP / MAP / min-max / quantity tiers are never invented.

Usage:
  pricing_engine.py --sale 24.99 --marketplace DE
  pricing_engine.py --sale 24.99 --currency EUR --no-b2b
  pricing_engine.py --batch prices.csv --out pricing.json     (columns: sku,marketplace,sale_price[,currency,...])
  pricing_engine.py --self-test

Exact Decimal arithmetic only. Exit code 0 = all PRICE_VALID, 1 = conflicts/data required, 2 = usage error.
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

POLICY_VERSION = "2026-10-08-v3"
DISCOUNT_STANDARD = Decimal("0.10")
DISCOUNT_BUSINESS = Decimal("0.10")

# Internal convenience map; the workbook / Data Definitions always win.
MARKETPLACE_CURRENCY = {
    "US": "USD", "CA": "CAD", "MX": "MXN", "BR": "BRL", "UK": "GBP", "GB": "GBP",
    "DE": "EUR", "FR": "EUR", "IT": "EUR", "ES": "EUR", "NL": "EUR", "BE": "EUR", "IE": "EUR",
    "SE": "SEK", "PL": "PLN", "TR": "TRY", "JP": "JPY", "AU": "AUD", "AE": "AED", "SA": "SAR",
    "EG": "EGP", "SG": "SGD", "IN": "INR",
}
ZERO_DECIMAL = {"JPY", "KRW", "VND", "CLP", "ISK"}


def dec(value, name="value"):
    if value is None or str(value).strip() == "":
        return None
    try:
        s = str(value).strip().replace(" ", "").replace(" ", "")
        if "," in s and "." not in s:
            s = s.replace(",", ".")  # 24,99 -> 24.99
        elif "," in s and "." in s:
            s = s.replace(",", "")  # 1,234.50
        d = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"{name}: not a number: {value!r}")
    if not d.is_finite():
        raise ValueError(f"{name}: not finite: {value!r}")
    return d


def quant(precision):
    return Decimal(1).scaleb(-precision)


def rnd(x, precision):
    return x.quantize(quant(precision), rounding=ROUND_HALF_UP)


def compute(sale, marketplace=None, currency=None, precision=None, b2b_applicable=True,
            explicit_standard=None, explicit_business=None, list_price=None, map_price=None,
            min_price=None, max_price=None, tiers=None, sale_start=None, sale_end=None,
            d=DISCOUNT_STANDARD, b=DISCOUNT_BUSINESS, now=None, source="USER_INPUT"):
    """Return the pricing block for the Agent 1 handoff plus an audit record."""
    issues, status = [], "PRICE_VALID"
    S = dec(sale, "sale_price")
    if S is None or S <= 0:
        return dict(price_input_type="sale_price", sale_price=None, standard_price=None, business_price=None,
                    business_price_status="NOT_CALCULATED", pricing_policy_version=POLICY_VERSION,
                    pricing_basis="STANDARD_PRICE", status="PRICE_DATA_REQUIRED",
                    issues=["sale_price missing or not > 0"], pricing_calculations=[])
    mp = (marketplace or "").upper() or None
    expected_cur = MARKETPLACE_CURRENCY.get(mp) if mp else None
    cur = (currency or expected_cur or "").upper() or None
    if cur is None:
        status = "PRICE_DATA_REQUIRED"
        issues.append("currency unknown: give marketplace or currency")
    elif expected_cur and cur != expected_cur:
        status = "CURRENCY_CONFLICT"
        issues.append(f"currency {cur} does not match marketplace {mp} ({expected_cur}); confirm against template")
    if precision is None:
        precision = 0 if cur in ZERO_DECIMAL else 2
    if not (Decimal(0) <= d < 1 and Decimal(0) <= b < 1):
        raise ValueError("discount rates must satisfy 0 <= rate < 1")

    P_raw = S / (1 - d)
    P = rnd(P_raw, precision)
    calcs = [dict(field="standard_price", input="sale_price", input_value=str(S), formula="S / (1 - d)",
                  d=str(d), unrounded=str(P_raw), rounded=str(P), rounding="ROUND_HALF_UP",
                  precision=precision, currency=cur)]
    B = None
    b2b_status = "NOT_APPLICABLE"
    if b2b_applicable:
        B_raw = P * (1 - b)  # from the ROUNDED standard price, never from S
        B = rnd(B_raw, precision)
        b2b_status = "CALCULATED"
        calcs.append(dict(field="business_price", input="standard_price", input_value=str(P),
                          formula="P * (1 - b)", b=str(b), unrounded=str(B_raw), rounded=str(B),
                          rounding="ROUND_HALF_UP", precision=precision, currency=cur))
        if not B < P:
            status = "PRICE_POLICY_CONFLICT"
            issues.append("business_price is not below standard_price")
    if not S < P:
        status = "PRICE_POLICY_CONFLICT"
        issues.append("sale_price is not below standard_price (amount too small for 2-decimal rounding)")

    # Explicit user values beat calculated ones but must be surfaced, never silently overwritten.
    for name, explicit, calc in (("standard_price", dec(explicit_standard, "explicit_standard"), P),
                                 ("business_price", dec(explicit_business, "explicit_business"), B)):
        if explicit is not None and calc is not None and explicit != calc:
            status = "PRICE_POLICY_CONFLICT"
            issues.append(f"explicit {name} {explicit} differs from policy value {calc}; user review required")

    lo, hi = dec(min_price, "min_price"), dec(max_price, "max_price")
    if lo is not None and hi is not None and lo > hi:
        status = "PRICE_CONFLICT"
        issues.append("minimum_seller_allowed_price > maximum_seller_allowed_price")
    for label, val in (("sale_price", S), ("standard_price", P)):
        if lo is not None and val < lo:
            status = "PRICE_CONFLICT"
            issues.append(f"{label} {val} below minimum allowed {lo}")
        if hi is not None and val > hi:
            status = "PRICE_CONFLICT"
            issues.append(f"{label} {val} above maximum allowed {hi}")
    if tiers:
        last_q = 0
        for q, _ in tiers:
            if int(q) != q or q <= last_q:
                status = "PRICE_CONFLICT"
                issues.append("quantity tiers must be integers in strictly ascending order")
                break
            last_q = int(q)
    if sale_start and sale_end and str(sale_start) > str(sale_end):
        status = "PRICE_CONFLICT"
        issues.append("sale_start_date after sale_end_date")

    ts = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return dict(
        price_input_type="sale_price", sale_price=S, standard_price=P, business_price=B,
        business_price_status=b2b_status, pricing_policy_version=POLICY_VERSION,
        pricing_basis="STANDARD_PRICE", currency=cur, marketplace=mp, status=status, issues=issues,
        list_price=dec(list_price), map_price=dec(map_price),
        pricing_calculations=calcs, calculated_at=ts, source=source,
    )


def jsonable(o):
    if isinstance(o, Decimal):
        return float(o) if o == o.to_integral_value() or len(str(o).split(".")[-1]) <= 8 else str(o)
    raise TypeError(type(o))


def self_test():
    r = compute("24.99", marketplace="DE")
    assert (r["standard_price"], r["business_price"]) == (Decimal("27.77"), Decimal("24.99")), r
    assert r["status"] == "PRICE_VALID" and r["sale_price"] == Decimal("24.99")
    r = compute("24,99", currency="EUR")
    assert r["standard_price"] == Decimal("27.77")
    r = compute("100", marketplace="US")
    assert (r["standard_price"], r["business_price"]) == (Decimal("111.11"), Decimal("100.00")), r
    r = compute("2000", marketplace="JP")
    assert r["standard_price"] == Decimal("2222") and r["business_price"] == Decimal("2000"), r
    r = compute("0.01", marketplace="US")
    assert r["status"] == "PRICE_POLICY_CONFLICT"
    r = compute("24.99", marketplace="DE", currency="USD")
    assert r["status"] == "CURRENCY_CONFLICT"
    r = compute("24.99", marketplace="DE", explicit_standard="29.99")
    assert r["status"] == "PRICE_POLICY_CONFLICT"
    r = compute("24.99", marketplace="DE", b2b_applicable=False)
    assert r["business_price"] is None and r["business_price_status"] == "NOT_APPLICABLE"
    r = compute("", marketplace="DE")
    assert r["status"] == "PRICE_DATA_REQUIRED"
    r = compute("10", marketplace="US", tiers=[(5, 9), (3, 8)])
    assert r["status"] == "PRICE_CONFLICT"
    print("self-test OK (8 cases)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sale")
    ap.add_argument("--marketplace")
    ap.add_argument("--currency")
    ap.add_argument("--precision", type=int)
    ap.add_argument("--no-b2b", action="store_true", help="B2B price not supported by this template/operation")
    ap.add_argument("--explicit-standard")
    ap.add_argument("--explicit-business")
    ap.add_argument("--batch")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test()
        return 0
    rows = []
    if a.batch:
        with open(a.batch, encoding="utf-8-sig", newline="") as f:
            if a.batch.lower().endswith(".json"):
                rows = json.load(f)
            else:
                rows = list(csv.DictReader(f))
    elif a.sale:
        rows = [dict(sale_price=a.sale, marketplace=a.marketplace, currency=a.currency,
                     explicit_standard=a.explicit_standard, explicit_business=a.explicit_business)]
    else:
        ap.error("give --sale or --batch")
    out, bad = [], 0
    for r in rows:
        try:
            res = compute(r.get("sale_price") or r.get("sale"), r.get("marketplace") or a.marketplace,
                          r.get("currency") or a.currency, a.precision, not a.no_b2b,
                          r.get("explicit_standard") or r.get("standard_price"),
                          r.get("explicit_business") or r.get("business_price"),
                          r.get("list_price"), r.get("map_price"), r.get("min_price"), r.get("max_price"),
                          sale_start=r.get("sale_start_date"), sale_end=r.get("sale_end_date"))
        except ValueError as e:
            res = dict(status="PRICE_DATA_REQUIRED", issues=[str(e)])
        if r.get("sku"):
            res["sku"] = r["sku"]
        bad += res["status"] != "PRICE_VALID"
        out.append(res)
    text = json.dumps(out if a.batch else out[0], ensure_ascii=False, indent=2, default=jsonable)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"wrote {a.out}: {len(out)} records, {bad} not PRICE_VALID")
    else:
        print(text)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
