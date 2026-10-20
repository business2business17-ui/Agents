#!/usr/bin/env python3
"""Deterministic Amazon finance formulas (references/formulas.md section 7-8; TZ v1.2 sections 20, 22).

  finance_calc.py unit --price 29.99 --vat-pct 19 --referral-pct 15 --ad-pct 10 --cost-fixed 12 --margin-pct 15 [--json]
      Unit Economics of one SKU / Marketplace. P = price with VAT, S = shipping + gift wrap paid by the buyer (with VAT),
      v = VAT rate, r = referral rate, d = DST surcharge on Amazon fees (UK 2, IT/FR/ES 3, else 0), a = ad cost share of P,
      m = target margin of net revenue, F = cost per unit. F is --cost-fixed, or the sum of --landed + --fba-fee x (1+d)
      + --fbm-shipping + --fbm-packaging + --storage + --return-cost + --other.
        Referral = max(r (P+S), --min-referral) x (1+d), rounded like Amazon (referral to the cent first, then DST, to the cent)
        k = 1/(1+v) - r (1+d)        Unit Profit = (P+S)/(1+v) - Referral - a P - F
        Break-even Price = (F - S k) / (k - a)            Target Price = (F - S (k - m/(1+v))) / (k - a - m/(1+v))
        Break-even ACoS = ((P+S) k - F) / P               Target ACoS  = ((P+S)(k - m/(1+v)) - F) / P
      With --min-referral above r (P+S) the fixed minimum is used and the prices are solved with it.
      Status: Loss | Ads Over Limit | Below Target | On Target.   Unreachable price (denominator <= 0) -> null + note.
  finance_calc.py referral --price 63.55 --ship 10 --referral-pct 15 --dst-pct 3 [--min-referral X]
  finance_calc.py ads-whatif --acos 30 --sales 10000 (--delta-pp -3 | --delta-pct -3) [--mode A|B]
      A: attributed sales unchanged, spend = ACoS' x sales.  B: spend unchanged, sales' = spend / ACoS'.
      -3 percentage points is NOT -3 %: --delta-pct multiplies the ACoS (30 -> 29.1).
Exit 0 = ok, 2 = usage / impossible input. Amounts are in the currency of the input; nothing is converted.
"""
import argparse
import json
import sys
from decimal import ROUND_HALF_UP, Decimal

D = Decimal
CENT = D("0.01")


def d(x, default="0"):
    return D(str(x if x is not None else default))


def q2(x):
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def referral_fee(price_plus_ship, rate, dst, minimum):
    """Amazon order: referral to the cent first, then the DST surcharge, to the cent again."""
    base = q2(max(rate * price_plus_ship, minimum))
    return q2(base * (1 + dst))


def pct(x):
    return None if x is None else float(x)


def unit(a):
    P, S = d(a.price), d(a.ship)
    v, r, dst = d(a.vat_pct) / 100, d(a.referral_pct) / 100, d(a.dst_pct) / 100
    ad, m = d(a.ad_pct) / 100, d(a.margin_pct) / 100
    minref = d(a.min_referral)
    if a.cost_fixed is not None:
        F = d(a.cost_fixed)
    else:
        F = (d(a.landed) + d(a.fba_fee) * (1 + dst) + d(a.fbm_shipping) + d(a.fbm_packaging) + d(a.storage)
             + d(a.return_cost) + d(a.other))
    if P <= 0 or v < 0 or r < 0 or r >= 1:
        print("invalid price / VAT / referral rate", file=sys.stderr)
        return 2
    gross = P + S
    net = gross / (1 + v)
    k = 1 / (1 + v) - r * (1 + dst)
    ref = referral_fee(gross, r, dst, minref)
    profit = net - ref - ad * P - F
    margin = profit / net if net else None
    notes = []

    def solve(margin_target):
        mt = margin_target
        den = k - ad - mt / (1 + v)
        if den <= 0:
            return None
        price = (F - S * (k - mt / (1 + v))) / den
        if minref and r * (price + S) < minref:  # the minimum referral applies: fixed fee model
            den2 = (1 - mt) / (1 + v) - ad
            if den2 <= 0:
                return None
            price = (F + minref * (1 + dst) - S * (1 - mt) / (1 + v)) / den2
        return price if price > 0 else None

    be_price, tg_price = solve(D(0)), solve(m)
    if be_price is None:
        notes.append("break-even price unreachable in this model (denominator <= 0)")
    if tg_price is None:
        notes.append("target price unreachable in this model (denominator <= 0)")
    pre_ad = ((gross * k - F) / P)
    tg_acos = ((gross * (k - m / (1 + v)) - F) / P)
    if minref and r * gross < minref:
        pre_ad = (net - minref * (1 + dst) - F) / P
        tg_acos = (net * (1 - m) - minref * (1 + dst) - F) / P
        notes.append("minimum referral fee applies: ACoS limits use the fixed fee")
    if profit < 0:
        status = "Ads Over Limit" if pre_ad >= 0 else "Loss"
    elif margin is not None and margin < m:
        status = "Below Target"
    else:
        status = "On Target"
    roi = (profit / d(a.landed) * 100) if a.landed else None
    out = dict(
        net_revenue=q2(net), referral_fee=ref, ad_cost=q2(ad * P), cost_per_unit=q2(F), unit_profit=q2(profit),
        unit_margin_pct=None if margin is None else q2(margin * 100), roi_pct=None if roi is None else q2(roi),
        break_even_price=None if be_price is None else q2(be_price), target_price=None if tg_price is None else q2(tg_price),
        break_even_acos_pct=q2(pre_ad * 100), target_acos_pct=q2(tg_acos * 100),
        actual_ad_share_pct=q2(ad * 100), status=status, notes=notes,
        assumptions=dict(price_incl_vat=str(P), shipping_incl_vat=str(S), vat_pct=str(v * 100), referral_pct=str(r * 100),
                         dst_pct=str(dst * 100), min_referral=str(minref), target_margin_pct=str(m * 100)))
    return out


def run_unit(a):
    out = unit(a)
    if isinstance(out, int):
        return out
    if a.json:
        print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
    else:
        for k_, v_ in out.items():
            if k_ not in ("assumptions", "notes"):
                print(f"{k_:22} {v_}")
        for n in out["notes"]:
            print("NOTE:", n)
    return 0


def run_referral(a):
    fee = referral_fee(d(a.price) + d(a.ship), d(a.referral_pct) / 100, d(a.dst_pct) / 100, d(a.min_referral))
    print(json.dumps({"referral_fee": str(fee)}) if a.json else fee)
    return 0


def run_ads(a):
    acos, sales = d(a.acos), d(a.sales)
    if acos <= 0 or sales <= 0:
        print("--acos and --sales must be > 0", file=sys.stderr)
        return 2
    if (a.delta_pp is None) == (a.delta_pct is None):
        print("give exactly one of --delta-pp / --delta-pct", file=sys.stderr)
        return 2
    new = acos + d(a.delta_pp) if a.delta_pp is not None else acos * (1 + d(a.delta_pct) / 100)
    if new <= 0:
        print("new ACoS must be > 0", file=sys.stderr)
        return 2
    spend0 = acos / 100 * sales
    if a.mode == "A":
        spend1, sales1 = new / 100 * sales, sales
    else:
        spend1, sales1 = spend0, spend0 / (new / 100)
    out = dict(mode=a.mode, acos_before_pct=str(acos), acos_after_pct=str(new.normalize()), spend_before=q2(spend0), spend_after=q2(spend1),
               spend_saving=q2(spend0 - spend1), attributed_sales_before=q2(sales), attributed_sales_after=q2(sales1),
               scenario=True, note="Scenario, not fact. Organic effect only by the user's assumption; attributed sales are not added to total revenue.")
    print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    u = sp.add_parser("unit")
    for n in ("price", "ship", "vat_pct", "referral_pct", "dst_pct", "ad_pct", "margin_pct", "min_referral", "cost_fixed",
              "landed", "fba_fee", "fbm_shipping", "fbm_packaging", "storage", "return_cost", "other"):
        u.add_argument("--" + n.replace("_", "-"), dest=n, type=float, default=None if n in ("cost_fixed", "landed") else 0.0,
                       required=n in ("price", "referral_pct"))
    u.add_argument("--json", action="store_true")
    r_ = sp.add_parser("referral")
    for n in ("price", "ship", "referral_pct", "dst_pct", "min_referral"):
        r_.add_argument("--" + n.replace("_", "-"), dest=n, type=float, default=0.0)
    r_.add_argument("--json", action="store_true")
    w = sp.add_parser("ads-whatif")
    w.add_argument("--acos", type=float, required=True)
    w.add_argument("--sales", type=float, required=True)
    w.add_argument("--delta-pp", type=float)
    w.add_argument("--delta-pct", type=float)
    w.add_argument("--mode", choices=["A", "B"], default="A")
    a = ap.parse_args()
    return {"unit": run_unit, "referral": run_referral, "ads-whatif": run_ads}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
