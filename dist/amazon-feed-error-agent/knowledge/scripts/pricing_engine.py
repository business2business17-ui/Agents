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
            d=DISCOUNT_STANDARD, b=DISCOUNT_BUSINESS, now=None, source="USER_INPUT",
            tier_basis=None, b2b_min_rule=None, b2b_max_pct=None, min_pct=None, max_pct=None):
    """Return the pricing block for the Agent 1 handoff plus an audit record.

    USER-DECIDED extras (NOT part of shared policy v3; nothing here has a default - the user supplies every number):
      tiers         [(qty, discount_pct), ...]  quantity-tier prices = basis * (1 - pct/100)
      tier_basis    'business' | 'standard'     which price the tier discounts apply to (must be stated)
      b2b_min_rule  'DEEPEST_TIER'              B2B minimum allowed price = price of the tier with the largest qty
      b2b_max_pct   percent above Business Price -> B2B maximum allowed price
      min_pct / max_pct  percent below / above Standard Price -> minimum / maximum seller allowed price (audience ALL)
    Everything produced from these arguments is tagged policy_status USER_DECISION.
    """
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
    _explicit_lo, _explicit_hi = lo, hi
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
    guard = {}
    tier_out = []
    if tiers:
        last_q, last_pct = 0, Decimal(0)
        for q, pct in tiers:
            pct = dec(pct, "tier discount percent")
            if int(q) != q or q <= last_q:
                status = "PRICE_CONFLICT"
                issues.append("quantity tiers must be integers in strictly ascending order")
                break
            if not (Decimal(0) < pct < 100) or pct <= last_pct:
                status = "PRICE_CONFLICT"
                issues.append("tier discount percents must be in (0,100) and strictly increase with quantity")
                break
            last_q, last_pct = int(q), pct
        else:
            if tier_basis not in ("business", "standard"):
                status = "PRICE_DATA_REQUIRED" if status == "PRICE_VALID" else status
                issues.append("tier_basis must be stated by the user: 'business' or 'standard' (no default)")
            else:
                basis_val = B if tier_basis == "business" else P
                if basis_val is None:
                    status = "PRICE_DATA_REQUIRED" if status == "PRICE_VALID" else status
                    issues.append("tier basis 'business' needs a Business Price (B2B not applicable here)")
                else:
                    for q, pct in tiers:
                        pct = dec(pct)
                        tp = rnd(basis_val * (1 - pct / 100), precision)
                        tier_out.append(dict(quantity=int(q), discount_percent=pct, price=tp))
                        calcs.append(dict(field=f"quantity_price_{int(q)}", input=f"{tier_basis}_price", input_value=str(basis_val),
                                          formula="basis * (1 - pct/100)", pct=str(pct), unrounded=str(basis_val * (1 - pct / 100)),
                                          rounded=str(tp), rounding="ROUND_HALF_UP", precision=precision, currency=cur,
                                          policy_status="USER_DECISION"))
                    prices = [t["price"] for t in tier_out]
                    if any(x >= y for x, y in zip(prices[1:], prices[:-1])):
                        status = "PRICE_CONFLICT"
                        issues.append("tier prices must strictly decrease with quantity (rounding collapsed two tiers?)")
                    guard["tier_basis"] = tier_basis
    b2b_min = b2b_max = None
    if b2b_min_rule:
        if b2b_min_rule != "DEEPEST_TIER":
            raise ValueError("b2b_min_rule must be 'DEEPEST_TIER'")
        if not tier_out:
            status = "PRICE_DATA_REQUIRED" if status == "PRICE_VALID" else status
            issues.append("b2b_min_rule DEEPEST_TIER needs quantity tiers")
        elif not b2b_applicable or B is None:
            issues.append("B2B minimum skipped: B2B price not applicable")
        else:
            b2b_min = max(tier_out, key=lambda t: t["quantity"])["price"]
            guard["business_min_rule"] = "DEEPEST_TIER (min = price of the largest-quantity tier)"
            if b2b_min > B:
                status = "PRICE_CONFLICT"
                issues.append("B2B minimum above Business Price")
    if b2b_max_pct is not None:
        if B is None:
            issues.append("B2B maximum skipped: B2B price not applicable")
        else:
            pct = dec(b2b_max_pct, "b2b_max_pct")
            b2b_max = rnd(B * (1 + pct / 100), precision)
            guard["business_max_percent_above_business_price"] = str(pct)
    if min_pct is not None or max_pct is not None:
        if min_pct is not None:
            lo = rnd(P * (1 - dec(min_pct, "min_pct") / 100), precision)
            guard["min_percent_below_standard_price"] = str(dec(min_pct))
        if max_pct is not None:
            hi = rnd(P * (1 + dec(max_pct, "max_pct") / 100), precision)
            guard["max_percent_above_standard_price"] = str(dec(max_pct))
        for label, val in (("sale_price", S), ("standard_price", P)):
            if lo is not None and val < lo:
                status = "PRICE_CONFLICT"
                issues.append(f"{label} {val} below minimum allowed {lo}")
            if hi is not None and val > hi:
                status = "PRICE_CONFLICT"
                issues.append(f"{label} {val} above maximum allowed {hi}")
    if guard:
        guard["policy_status"] = "USER_DECISION"
        guard["note"] = "B2B bounds / quantity tiers / allowed-price percents are the user's decision, not shared policy v3"
    if sale_start and sale_end and str(sale_start) > str(sale_end):
        status = "PRICE_CONFLICT"
        issues.append("sale_start_date after sale_end_date")

    ts = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return dict(
        price_input_type="sale_price", sale_price=S, standard_price=P, business_price=B,
        business_price_status=b2b_status, pricing_policy_version=POLICY_VERSION,
        pricing_basis="STANDARD_PRICE", currency=cur, marketplace=mp, status=status, issues=issues,
        list_price=dec(list_price), map_price=dec(map_price),
        minimum_seller_allowed_price=lo if (min_pct is not None or min_price is not None) else None,
        maximum_seller_allowed_price=hi if (max_pct is not None or max_price is not None) else None,
        business_min_price=b2b_min, business_max_price=b2b_max, quantity_tiers=tier_out or None,
        guardrails=guard or None,
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
    r = compute("10", marketplace="US", tiers=[(5, 5), (3, 10)], tier_basis="business")
    assert r["status"] == "PRICE_CONFLICT"
    # user-decided tiers: 2/4/6 pcs, B2B min = deepest tier
    r = compute("24.99", marketplace="DE", tiers=[(2, 5), (4, 10), (6, 15)], tier_basis="business", b2b_min_rule="DEEPEST_TIER",
                b2b_max_pct=20, min_pct=15, max_pct=30)
    assert r["status"] == "PRICE_VALID", r
    assert [t["price"] for t in r["quantity_tiers"]] == [Decimal("23.74"), Decimal("22.49"), Decimal("21.24")], r["quantity_tiers"]
    assert r["business_min_price"] == Decimal("21.24") == r["quantity_tiers"][-1]["price"]
    assert r["business_max_price"] == Decimal("29.99")
    assert r["minimum_seller_allowed_price"] == Decimal("23.60") and r["maximum_seller_allowed_price"] == Decimal("36.10")
    assert r["guardrails"]["policy_status"] == "USER_DECISION"
    r = compute("24.99", marketplace="DE", tiers=[(2, 5)])  # no basis stated -> no silent default
    assert r["status"] == "PRICE_DATA_REQUIRED" and not r["quantity_tiers"]
    r = compute("24.99", marketplace="DE", b2b_min_rule="DEEPEST_TIER")
    assert r["status"] == "PRICE_DATA_REQUIRED"
    print("self-test OK (12 cases)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sale")
    ap.add_argument("--marketplace")
    ap.add_argument("--currency")
    ap.add_argument("--precision", type=int)
    ap.add_argument("--no-b2b", action="store_true", help="B2B price not supported by this template/operation")
    ap.add_argument("--explicit-standard")
    ap.add_argument("--explicit-business")
    ap.add_argument("--tiers", help='USER-DECIDED quantity tiers "qty:discount_pct,..." e.g. "2:5,4:10,6:15"')
    ap.add_argument("--tier-basis", choices=["business", "standard"], help="price the tier discounts apply to (no default)")
    ap.add_argument("--b2b-min", choices=["deepest-tier"], help="B2B minimum = price of the largest-quantity tier")
    ap.add_argument("--b2b-max-pct", help="B2B maximum = Business Price + pct")
    ap.add_argument("--min-pct", help="minimum seller allowed price = Standard Price - pct")
    ap.add_argument("--max-pct", help="maximum seller allowed price = Standard Price + pct")
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
    def parse_tiers(t):
        if not t:
            return None
        return [(int(q), dec(p)) for q, p in (x.split(":") for x in str(t).split(",") if x.strip())]

    out, bad = [], 0
    for r in rows:
        try:
            res = compute(r.get("sale_price") or r.get("sale"), r.get("marketplace") or a.marketplace,
                          r.get("currency") or a.currency, a.precision, not a.no_b2b,
                          r.get("explicit_standard") or r.get("standard_price"),
                          r.get("explicit_business") or r.get("business_price"),
                          r.get("list_price"), r.get("map_price"), r.get("min_price"), r.get("max_price"),
                          sale_start=r.get("sale_start_date"), sale_end=r.get("sale_end_date"),
                          tiers=parse_tiers(r.get("tiers") or a.tiers), tier_basis=r.get("tier_basis") or a.tier_basis,
                          b2b_min_rule="DEEPEST_TIER" if (r.get("b2b_min") or a.b2b_min) else None,
                          b2b_max_pct=r.get("b2b_max_pct") or a.b2b_max_pct,
                          min_pct=r.get("min_pct") or a.min_pct, max_pct=r.get("max_pct") or a.max_pct)
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
