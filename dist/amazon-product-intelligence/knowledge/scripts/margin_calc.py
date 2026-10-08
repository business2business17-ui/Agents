#!/usr/bin/env python3
"""Unit-economics helper: margin at each price level, break-even / minimum price, and a PROPOSED tier ladder.

Everything numeric comes from the USER (cost, fees, target margin, quantities); nothing is defaulted except
arithmetic. Output is a proposal for the user to approve - it does not write prices anywhere.

Per-unit model (one unit sold at price p, p includes VAT if --vat-pct is given):
  net      = p / (1 + vat)
  referral = max(referral_pct * base, referral_min)      base = p (gross, default) or net (--referral-base net)
  fulfil   = fba_fee (channel fba)  |  mfn_fee (channel mfn)       per unit
  other    = other_pct * base + other_fixed                         ads / returns reserve / prep, only if the user gives them
  profit   = net - referral - fulfil - other - cost
  margin   = profit / net          roi = profit / cost

Usage:
  margin_calc.py --cost 7.50 --referral-pct 15 --fba-fee 3.20 --channel fba --target-margin 20 --price 24.99
  margin_calc.py ... --basis-price 24.99 --quantities 2,4          # propose tier percents so the deepest tier keeps the target margin
  margin_calc.py ... --from-pricing pricing.json                    # evaluate sale/standard/business/tier/B2B-min prices from pricing_engine output
  margin_calc.py ... --channel both --mfn-fee 4.10 --fba-fee 3.20   # compare channels
Optional: --vat-pct, --referral-min, --referral-base gross|net, --other-pct, --other-fixed, --buffer-pp (safety, percentage points).
Exit 0 = all evaluated levels meet the target margin (or no target given), 1 = some level below target, 2 = usage error.
"""
import argparse
import json
import sys
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

D = Decimal
CENT = D("0.01")


def d(v, name):
    if v is None:
        return None
    try:
        return D(str(v).replace(",", "."))
    except Exception:  # noqa: BLE001
        sys.exit(f"{name}: not a number: {v!r}")


class Econ:
    def __init__(self, a, channel):
        self.cost = d(a.cost, "cost")
        self.ref_pct = d(a.referral_pct, "referral_pct") / 100
        self.ref_min = d(a.referral_min or 0, "referral_min")
        self.base = a.referral_base
        self.vat = d(a.vat_pct or 0, "vat_pct") / 100
        self.other_pct = d(a.other_pct or 0, "other_pct") / 100
        self.other_fixed = d(a.other_fixed or 0, "other_fixed")
        self.channel = channel
        fee = a.fba_fee if channel == "fba" else a.mfn_fee
        if fee is None:
            sys.exit(f"--{channel}-fee is required for channel {channel}")
        self.fulfil = d(fee, f"{channel}_fee")

    def at(self, p):
        p = D(p)
        net = p / (1 + self.vat)
        base = p if self.base == "gross" else net
        ref = max(self.ref_pct * base, self.ref_min)
        other = self.other_pct * base + self.other_fixed
        profit = net - ref - self.fulfil - other - self.cost
        return dict(price=p, net=net, referral=ref, fulfilment=self.fulfil, other=other, cost=self.cost, profit=profit,
                    margin=(profit / net if net else D(0)), roi=(profit / self.cost if self.cost else None))

    def price_for_margin(self, m):
        """Smallest gross price with margin >= m (profit / net)."""
        k = (1 + self.vat) if self.base == "gross" else D(1)
        fixed = self.cost + self.fulfil + self.other_fixed
        denom = 1 - (self.ref_pct + self.other_pct) * k - m
        if denom <= 0:
            return None
        net_a = fixed / denom
        p_a = net_a * (1 + self.vat)
        base_a = p_a if self.base == "gross" else net_a
        if self.ref_pct * base_a >= self.ref_min:
            return p_a
        denom_b = 1 - self.other_pct * k - m
        if denom_b <= 0:
            return None
        return (fixed + self.ref_min) / denom_b * (1 + self.vat)


def q2(x):
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def pct(x):
    return f"{(x * 100).quantize(D('0.1'), rounding=ROUND_HALF_UP)}%"


def levels_from_pricing(path):
    j = json.load(open(path, encoding="utf-8"))
    j = j[0] if isinstance(j, list) else j
    out = []
    for key, label in (("sale_price", "Sale Price"), ("standard_price", "Standard Price"), ("business_price", "Business Price"),
                       ("business_min_price", "B2B minimum (deepest tier)")):
        if j.get(key) is not None:
            out.append((label, D(str(j[key]))))
    for t in j.get("quantity_tiers") or []:
        out.append((f"Tier from {t['quantity']} pcs (-{t['discount_percent']}%)", D(str(t["price"]))))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cost", required=True, help="landed unit cost (purchase + inbound + duties...), given by the user")
    ap.add_argument("--referral-pct", required=True, help="Amazon referral fee, percent of price")
    ap.add_argument("--referral-min")
    ap.add_argument("--referral-base", choices=["gross", "net"], default="gross",
                    help="price the referral % applies to (gross = incl. VAT). CONFIRM in your fee schedule")
    ap.add_argument("--fba-fee")
    ap.add_argument("--mfn-fee")
    ap.add_argument("--channel", choices=["fba", "mfn", "both"], required=True)
    ap.add_argument("--vat-pct")
    ap.add_argument("--other-pct")
    ap.add_argument("--other-fixed")
    ap.add_argument("--target-margin", help="minimum margin, percent of net revenue")
    ap.add_argument("--price", action="append", default=[], help="evaluate a price (repeatable)")
    ap.add_argument("--from-pricing")
    ap.add_argument("--basis-price", help="price the tier discounts apply to (Business Price recommended)")
    ap.add_argument("--quantities", help="tier quantities chosen by the user for THIS run, e.g. 2,4 or 2,4,6")
    ap.add_argument("--buffer-pp", default="0", help="percentage points subtracted from the maximum safe discount")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    target = d(a.target_margin, "target_margin") / 100 if a.target_margin else None
    channels = ["fba", "mfn"] if a.channel == "both" else [a.channel]
    levels = [(f"price {p}", D(p.replace(",", "."))) for p in a.price]
    if a.from_pricing:
        levels += levels_from_pricing(a.from_pricing)
    result, below = {}, False
    for ch in channels:
        e = Econ(a, ch)
        rows = []
        for label, p in levels:
            r = e.at(p)
            ok = None if target is None else r["margin"] >= target
            below |= ok is False
            rows.append(dict(level=label, price=str(q2(p)), referral=str(q2(r["referral"])), fulfilment=str(q2(r["fulfilment"])),
                             other=str(q2(r["other"])), cost=str(q2(r["cost"])), profit=str(q2(r["profit"])),
                             margin=pct(r["margin"]), roi=pct(r["roi"]) if r["roi"] is not None else None, meets_target=ok))
        be = e.price_for_margin(D(0))
        pmin = e.price_for_margin(target) if target is not None else None
        entry = dict(channel=ch, break_even_price=str(q2(be)) if be else None,
                     min_price_for_target_margin=str(q2(pmin)) if pmin else None, levels=rows)
        if a.basis_price and pmin:
            basis = D(a.basis_price.replace(",", "."))
            dmax = 1 - pmin / basis
            buf = d(a.buffer_pp, "buffer_pp") / 100
            usable = dmax - buf
            entry["basis_price"] = str(q2(basis))
            entry["max_discount_from_basis"] = pct(dmax) if dmax > 0 else "none: basis is already at/below the minimum price"
            if usable > 0 and a.quantities:
                qs = sorted({int(x) for x in a.quantities.split(",") if x.strip()})
                deepest = (usable * 100 * 2).to_integral_value(rounding=ROUND_DOWN) / 2
                ladder = []
                for i, qn in enumerate(qs, 1):
                    pc = (deepest * i / len(qs))
                    pc = (pc * 2).to_integral_value(rounding=ROUND_DOWN) / 2 if i < len(qs) else deepest
                    price = q2(basis * (1 - pc / 100))
                    ladder.append(dict(quantity=qn, discount_percent=str(pc), price=str(price),
                                       margin=pct(e.at(price)["margin"])))
                entry["proposed_ladder"] = dict(
                    note="PROPOSAL for the user to approve or change; deepest tier keeps the target margin; B2B minimum would be the deepest tier price",
                    tiers=ladder, cli_tiers=",".join(f"{t['quantity']}:{t['discount_percent']}" for t in ladder))
            elif a.quantities:
                entry["proposed_ladder"] = None
        result[ch] = entry
    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for ch, ent in result.items():
            print(f"== channel {ch.upper()} | break-even price {ent['break_even_price']} | min price for target margin {ent['min_price_for_target_margin']}")
            for r in ent["levels"]:
                flag = "" if r["meets_target"] is None else ("  OK" if r["meets_target"] else "  BELOW TARGET")
                print(f"  {r['level']:34} price {r['price']:>8}  referral {r['referral']:>6}  fulfil {r['fulfilment']:>6}  cost {r['cost']:>6}  "
                      f"profit {r['profit']:>7}  margin {r['margin']:>7}  roi {r['roi']}{flag}")
            if "max_discount_from_basis" in ent:
                print(f"  basis {ent['basis_price']}: max discount keeping the target margin = {ent['max_discount_from_basis']}")
            lad = ent.get("proposed_ladder")
            if lad:
                print("  proposed ladder (to approve):", "; ".join(f"{t['quantity']} pcs -{t['discount_percent']}% = {t['price']} (margin {t['margin']})" for t in lad["tiers"]))
                print("  -> pricing_engine --tiers", f"\"{lad['cli_tiers']}\"", "--tier-basis business --b2b-min deepest-tier")
    return 1 if below else 0


if __name__ == "__main__":
    sys.exit(main())
