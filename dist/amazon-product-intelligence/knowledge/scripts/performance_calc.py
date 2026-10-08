#!/usr/bin/env python3
"""GMV, net profit, ACOS, TACOS, ROAS and ad-spend limits for a period or a plan (user-supplied numbers only).

Uses the same per-unit model as margin_calc.py (units, not orders; referral on gross price unless --referral-base net;
margin = net profit / net revenue ex VAT). Ad spend is entered as the cost to the business (net of recoverable VAT).

Definitions
  GMV (gross)   = sum(price * units), prices incl. VAT         GMV (net) = GMV gross / (1 + VAT)
  net profit before ads = sum(units * unit profit)             net profit = profit before ads - ad spend
  net margin    = net profit / net revenue (ex VAT)
  ACOS  = ad spend / ad-attributed sales          ROAS = ad sales / ad spend
  TACOS = ad spend / total sales (organic + ad)   ad cost per unit = ad spend / units
  break-even ACOS/TACOS = net profit before ads / sales (ACOS/TACOS at which net profit is zero)
  target ACOS/TACOS     = (net profit before ads - target margin * net revenue) / sales   (needs --target-margin)
  "sales" in ACOS/TACOS must match the report the numbers come from (VAT included or not). There is NO default:
    * --sales-basis gross|net states it explicitly, or
    * with --total-sales the script DETECTS it by comparing the report figure with GMV gross and GMV net of the
      units x price lines (within 3%); if both fit or neither fits it stops and asks.
  With VAT 0 gross = net and no choice is needed.

Usage:
  performance_calc.py --cost 9 --referral-pct 15 --fba-fee 3.2 --channel fba --vat-pct 19 \\
      --lines "24.99:300,22.49:120" --ad-spend 650 --ad-sales 2100 [--total-sales 10500] --target-margin 15
  Plan mode (no ads yet): omit --ad-spend -> prints the ad budget that still meets the target margin.
Other options: --referral-min --referral-base --other-pct --other-fixed (returns reserve, prep; NOT ads) --json
Exit 0 = margin after ads meets the target (or no target), 1 = below target / ads above break-even, 2 = usage error.
"""
import argparse
import json
import sys
from decimal import ROUND_HALF_UP, Decimal

from margin_calc import Econ, d, pct, q2

D = Decimal


def ratio(a, b):
    return (a / b) if b else None


def fp(x):
    return pct(x) if x is not None else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cost", required=True)
    ap.add_argument("--referral-pct", required=True)
    ap.add_argument("--referral-min")
    ap.add_argument("--referral-base", choices=["gross", "net"], default="gross")
    ap.add_argument("--fba-fee")
    ap.add_argument("--mfn-fee")
    ap.add_argument("--channel", choices=["fba", "mfn"], required=True)
    ap.add_argument("--vat-pct")
    ap.add_argument("--other-pct")
    ap.add_argument("--other-fixed")
    ap.add_argument("--lines", required=True, help='"price:units,price:units" (prices incl. VAT; mix of tiers is fine)')
    ap.add_argument("--ad-spend")
    ap.add_argument("--ad-sales", help="ad-attributed sales (same basis as --sales-basis)")
    ap.add_argument("--total-sales", help="total sales incl. organic (defaults to GMV on the chosen basis)")
    ap.add_argument("--sales-basis", choices=["gross", "net"], default=None)
    ap.add_argument("--target-margin")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    e = Econ(a, a.channel)
    vat = e.vat
    lines = []
    for chunk in a.lines.split(","):
        p, u = chunk.split(":")
        lines.append((D(p.replace(",", ".")), D(u)))
    units = sum(u for _, u in lines)
    gmv_gross = sum(p * u for p, u in lines)
    gmv_net = gmv_gross / (1 + vat)
    profit_before = sum(e.at(p)["profit"] * u for p, u in lines)
    basis, basis_note = a.sales_basis, "stated by the user"
    if vat == 0:
        basis, basis_note = basis or "gross", "VAT 0: gross = net"
    elif basis is None and a.total_sales:
        ts = d(a.total_sales, "total_sales")
        near_g = abs(ts - gmv_gross) <= gmv_gross * D("0.03")
        near_n = abs(ts - gmv_net) <= gmv_net * D("0.03")
        if near_g != near_n:
            basis = "gross" if near_g else "net"
            basis_note = f"DETECTED: total sales {q2(ts)} is within 3% of GMV {basis} ({q2(gmv_gross if near_g else gmv_net)}); confirm with the user"
        else:
            sys.exit(f"sales basis cannot be detected (total sales {q2(ts)} vs GMV gross {q2(gmv_gross)} / net {q2(gmv_net)}): "
                     "ask the user whether the report shows sales incl. VAT or excl. VAT and pass --sales-basis gross|net")
    if basis is None and (a.ad_spend is not None):
        sys.exit("sales basis unknown: ask the user whether the report (Business Report / Ads console) shows sales incl. VAT or excl. VAT, "
                 "or pass --total-sales so it can be detected; then pass --sales-basis gross|net")
    basis = basis or "gross"
    a.sales_basis = basis
    basis_total = gmv_gross if basis == "gross" else gmv_net
    target = d(a.target_margin, "target_margin") / 100 if a.target_margin else None
    out = dict(assumptions=dict(unit_model="fees and discounts per unit", referral_base=a.referral_base,
                                margin="net profit / net revenue ex VAT", sales_basis=f"{basis} ({basis_note})",
                                ad_spend="cost to the business, net of recoverable VAT"),
               units=str(units), gmv_gross=str(q2(gmv_gross)), gmv_net=str(q2(gmv_net)),
               net_profit_before_ads=str(q2(profit_before)),
               net_margin_before_ads=fp(ratio(profit_before, gmv_net)),
               break_even_acos_tacos=fp(ratio(profit_before, basis_total)))
    if target is not None:
        allowed = profit_before - target * gmv_net
        out["target_margin"] = fp(target)
        out["max_ad_spend_for_target_margin"] = str(q2(allowed)) if allowed > 0 else "none: margin target not reachable before any ad spend"
        out["target_acos_tacos"] = fp(ratio(allowed, basis_total)) if allowed > 0 else None
        out["target_ad_cost_per_unit"] = str(q2(allowed / units)) if allowed > 0 and units else None
    bad = False
    if a.ad_spend is not None:
        spend = d(a.ad_spend, "ad_spend")
        total_sales = d(a.total_sales, "total_sales") if a.total_sales else basis_total
        ad_sales = d(a.ad_sales, "ad_sales") if a.ad_sales else None
        profit = profit_before - spend
        margin = ratio(profit, gmv_net)
        acos = ratio(spend, ad_sales) if ad_sales else None
        tacos = ratio(spend, total_sales)
        be = ratio(profit_before, basis_total)
        out.update(ad_spend=str(q2(spend)), net_profit=str(q2(profit)), net_margin=fp(margin),
                   net_margin_vs_gmv_gross=fp(ratio(profit, gmv_gross)),
                   acos=fp(acos), roas=(str((ad_sales / spend).quantize(D("0.01"), rounding=ROUND_HALF_UP)) if ad_sales and spend else None),
                   tacos=fp(tacos), ad_cost_per_unit=str(q2(spend / units)) if units else None,
                   ad_share_of_sales=fp(ratio(ad_sales, total_sales)) if ad_sales else None,
                   organic_sales=str(q2(total_sales - ad_sales)) if ad_sales else None)
        flags = []
        if a.total_sales and abs(total_sales - basis_total) > basis_total * D("0.02"):
            flags.append(f"total_sales {q2(total_sales)} differs from GMV on {a.sales_basis} basis {q2(basis_total)} by more than 2%: lines may be incomplete")
        if acos is not None and be is not None and acos > be:
            flags.append("ACOS above break-even: ad-attributed sales lose money before overheads")
            bad = True
        if target is not None and margin is not None and margin < target:
            flags.append(f"net margin after ads {fp(margin)} below target {fp(target)}")
            bad = True
        out["flags"] = flags
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for k, v in out.items():
            if k != "assumptions":
                print(f"{k:34} {v}")
        print("assumptions:", "; ".join(f"{k}={v}" for k, v in out["assumptions"].items()))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
