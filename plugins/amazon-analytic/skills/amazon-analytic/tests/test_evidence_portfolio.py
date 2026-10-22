from dataclasses import replace
from datetime import date

import pytest

from mia.config import Config
from mia.evidence import HYPOTHESIS, VALIDATED, WEAK, WHITE_SPACE, assess, conservative_units
from mia.importers.helium10 import XrayRow
from mia.portfolio import Candidate, build_portfolio, overlap

CFG = Config()
AS_OF = date(2026, 10, 20)


def row(asin, brand, units, price, reviews=1000, created=date(2020, 1, 1), badge=None):
    return XrayRow(asin=asin, title=f"{brand} product", brand=brand, marketplace="DE", currency="EUR",
                   price=price, units=units, revenue=units * price, parent_units=units,
                   parent_revenue=units * price, badge_floor=badge, bsr=None, rating=4.5, reviews=reviews,
                   review_velocity=None, images=7, fees=5.0, active_sellers=1, fulfillment="FBA", buy_box=brand,
                   seller=brand, seller_country="DE", size_tier="Small Parcel", category="Beauty",
                   dimensions_cm=None, weight_kg=0.3, created=created, seller_age_months=40, url="")


SEGMENT = [
    row("B0A0000001", "Alpha", 400, 15.0),
    row("B0A0000002", "Beta", 300, 17.0, reviews=120, created=date(2025, 12, 1)),   # молодая модель
    row("B0A0000003", "Gamma", 250, 16.0),
    row("B0A0000004", "Delta", 40, 14.0),                                           # ниже порога
]


# ---------- доказательность

def test_validated_segment():
    ev = assess(SEGMENT, 16.99, AS_OF, CFG)
    assert ev.status == VALIDATED and ev.brands == 3 and ev.young_models == 1
    assert [m["asin"] for m in ev.models] == ["B0A0000001", "B0A0000002", "B0A0000003"]
    assert ev.price_corridor == [11.25, 21.25]


def test_single_brand_is_weak():
    rows = [row("B0A0000001", "Alpha", 400, 15.0, reviews=100), row("B0A0000002", "alpha", 300, 16.0)]
    ev = assess(rows, 15.99, AS_OF, CFG)
    assert ev.status == WEAK and "brands" in ev.failed


def test_only_old_incumbents_is_weak():
    rows = [row(f"B0A000000{i}", b, 300, 15.0, reviews=5000) for i, b in enumerate(["A", "B", "C"])]
    assert "young" in assess(rows, 15.0, AS_OF, CFG).failed


def test_price_outside_corridor_is_weak():
    assert "price" in assess(SEGMENT, 29.99, AS_OF, CFG).failed


def test_segment_resting_on_one_asin_is_weak():
    rows = SEGMENT + [row("B0A0000009", "Mega", 5000, 16.0)]
    ev = assess(rows, 16.0, AS_OF, CFG)
    assert "top1" in ev.failed and ev.top1_share > 0.5


def test_no_models_and_white_space():
    assert assess([row("B0A0000004", "Delta", 40, 14.0)], 14.0, AS_OF, CFG).status == HYPOTHESIS
    assert assess([], 14.0, AS_OF, CFG).status == WHITE_SPACE


def test_conservative_units_capped_by_badge():
    assert conservative_units(row("B0A0000001", "A", 9278, 18.0, badge=2000)) == 2999   # 2K+ = 2000–2999
    assert conservative_units(row("B0A0000001", "A", 150, 18.0, badge=100)) == 150
    assert conservative_units(row("B0A0000001", "A", 150, 18.0)) == 150
    # модель с 150 по Helium, но бейдж 50+ (50–99) → консервативно 99 < порога 100
    assert assess([row("B0A0000001", "A", 150, 18.0, badge=50)], 18.0, AS_OF, CFG).status == HYPOTHESIS


# ---------- портфель

def cand(cid, profit, capital, decision="TEST", evidence=VALIDATED, units=200, initial=600, moq=500,
         keywords=None, asins=None, cond=None, rule="R5b"):
    return Candidate(cid, cid, decision, rule, cond, evidence, [], profit, capital, capital * 0.5, initial,
                     units, moq, keywords or {}, asins or set())


def test_minimal_set_without_target_is_one_sku():
    pf = build_portfolio([cand("a", 3000, 10000), cand("b", 5000, 10000)], CFG, budget=50000)
    assert pf["wave_1"] == ["b"]                                       # лучшая эффективность капитала
    assert pf["wave_2"][0]["id"] == "a" and "минимальный набор" in pf["wave_2"][0]["reason"]


def test_target_profit_adds_skus_until_met():
    cs = [cand("a", 3000, 10000), cand("b", 5000, 10000), cand("c", 1000, 10000)]
    pf = build_portfolio(cs, CFG, budget=50000, target_profit_12m=7000)
    assert pf["wave_1"] == ["b", "a"] and pf["target_met"] is True
    assert pf["wave_2"] == [{"id": "c", "reason": "цель по прибыли уже достигнута — расширение по KPI волны 1"}]


def test_budget_and_fba_capacity():
    cs = [cand("a", 5000, 10000), cand("b", 4000, 9000, initial=600), cand("c", 1000, 2000, initial=3000)]
    pf = build_portfolio(cs, CFG, budget=15000, fba_capacity=1500, target_profit_12m=100000)
    assert pf["wave_1"] == ["a"]
    reasons = {x["id"]: x["reason"] for x in pf["wave_2"]}
    assert "бюджет" in reasons["b"] and "FBA capacity" in reasons["c"]
    assert pf["target_met"] is False


def test_cannibalization_keeps_pair_apart():
    a = cand("a", 5000, 10000, keywords={"tan oil": 1000, "sun oil": 500}, asins={"X", "Y"})
    b = cand("b", 4000, 10000, keywords={"tan oil": 1000, "carrot oil": 300}, asins={"Z"})
    assert overlap(a, b)["keywords"] == pytest.approx(1000 / 1300)
    pf = build_portfolio([a, b], CFG, budget=50000, target_profit_12m=100000)
    assert pf["wave_1"] == ["a"] and "каннибализация" in pf["wave_2"][0]["reason"]
    assert pf["cannibalization"][0]["a"] == "a"


def test_weak_evidence_goes_to_wave_2_and_holds_after_fix():
    cs = [cand("weak", 9000, 10000, evidence=WEAK),
          cand("hold", 6000, 10000, decision="HOLD", cond="TEST (R5b)", rule="R3"),
          cand("dead", 9000, 10000, decision="HOLD", cond="NO-GO (R5d)", rule="R3"),
          cand("no", 0, 10000, decision="NO-GO", rule="R2")]
    pf = build_portfolio(cs, CFG, budget=50000)
    assert pf["wave_1"] == []
    assert pf["wave_2"][0]["id"] == "weak" and "доказательность" in pf["wave_2"][0]["reason"]
    assert pf["after_fix"]["plan"] == ["hold"]
    assert {x["id"] for x in pf["rejected"]} == {"dead", "no"}


def test_moq_cover_risk():
    pf = build_portfolio([cand("a", 1000, 5000, units=50, moq=1000)], CFG)
    assert "20,0 мес." in pf["risks"]["a"][0]
