import pytest

from mia.cashflow import LaunchParams, ScenarioParams, analyze_scenarios, build_scenarios, simulate
from mia.config import Config
from mia.economics import FeeSchedule, LeadTime, ReferralRule, TaxContext, UnitCosts

CFG = Config()
US = TaxContext("US", 0.0, False)
FEES = FeeSchedule(ReferralRule("whole", ((None, 0.10),)), fulfillment_fee=2.0)
COSTS = UnitCosts(cogs=5.0)


def flat(units, price=20.0, tacos=0.0):
    return ScenarioParams("base", price, units, tacos, (1.0,), (1.0,))


def launch(**kw):
    d = dict(lead_time=LeadTime(0, 30), deposit_pct=0.5, moq=100, payout_delay_days=0)
    d.update(kw)
    return LaunchParams(**d)


def test_hand_computed_simple_case():
    # Цена 20, referral 2, FBA 2 → 16 на единицу в кэше; COGS 5; 100 шт./мес.; LT 30 дн. → продажи с месяца 1.
    r = simulate(flat(100), launch(), US, FEES, COSTS, initial_units=300, cfg=CFG)
    assert r.sales_start_month == 1
    m0 = r.rows[0]
    assert m0.cash_out == pytest.approx(0.5 * 300 * 5 + 0.5 * 300 * 5)  # депозит + остаток (production=0)
    assert r.rows[1].units_sold == 100
    assert r.rows[1].cash_in == pytest.approx(100 * 16)
    assert r.liquidity_gap == pytest.approx(1500)
    # Конец месяца 1: на складе 200 < ROP = 100/30·(30+30) + SS ≈ 221 → дозаказ max(MOQ, 300) = 300,
    # депозит 0.5·300·5 = 750 в месяце 1, остаток 750 при отгрузке (месяц 2).
    assert r.rows[1].cash_out == pytest.approx(750)
    assert r.rows[1].cum_cash == pytest.approx(-1500 + 1600 - 750)
    assert r.payback_month == 2                 # −650 + 1600 − 750 = 200 ≥ 0
    assert r.profit_12m > 0


def test_stockout_is_recorded_and_sales_capped():
    lp = launch(lead_time=LeadTime(0, 30), moq=10)
    r = simulate(flat(100), lp, US, FEES, COSTS, initial_units=50, cfg=CFG)
    assert r.rows[1].units_sold == 50
    assert 1 in r.stockout_months


def test_reorder_prevents_stockout_in_steady_state():
    lp = launch(lead_time=LeadTime(30, 35, 5, 10), moq=100)
    r = simulate(flat(65), lp, US, FEES, COSTS, initial_units=500, cfg=CFG)
    # после первой партии дозаказ должен приходить вовремя
    assert r.stockout_months == []


def test_payout_delay_shifts_cash():
    r = simulate(flat(100), launch(payout_delay_days=15), US, FEES, COSTS, 300, CFG)
    assert r.rows[1].cash_in == pytest.approx(100 * 16 * 0.5)
    assert r.rows[2].cash_in == pytest.approx(100 * 16 * 0.5 + 100 * 16 * 0.5)


def test_conservative_buys_same_stock_as_base_and_car():
    units = {"conservative": 20, "base": 100, "optimistic": 150}
    prices = {s: 20.0 for s in units}
    tacos = {s: 0.1 for s in units}
    sc = build_scenarios(units, prices, tacos, "private_label", CFG)
    sa = analyze_scenarios(sc, launch(lead_time=LeadTime(0, 30)), US, FEES, COSTS, CFG)
    assert sa.results["conservative"].initial_units == sa.results["base"].initial_units
    assert set(sa.stress) == {"price_-15%", "cpc_+30%", "cvr_-30%", "delay_+45d", "unsold_50%"}
    w = CFG.scenario_weights
    assert sa.expected_profit_12m == pytest.approx(sum(w[s] * sa.results[s].profit_12m for s in w))
    assert sa.capital_at_risk >= sa.results["conservative"].loss_at_horizon


def test_capacity_limit_caps_initial_order():
    units = {"conservative": 500, "base": 500, "optimistic": 500}
    sc = build_scenarios(units, {s: 20.0 for s in units}, {s: 0.1 for s in units}, "private_label", CFG)
    sa = analyze_scenarios(sc, launch(fba_capacity_units=200), US, FEES, COSTS, CFG)
    assert not sa.capacity_ok
    assert sa.initial_units == 200


def test_seasonality_normalised():
    lp = LaunchParams.from_dict({"lead_time": {"production_days": 0, "transit_days": 0},
                                 "deposit_pct": 1, "moq": 1, "seasonality": [2] * 12})
    assert lp.seasonality == tuple([1.0] * 12)
    with pytest.raises(ValueError):
        LaunchParams.from_dict({"lead_time": {"production_days": 0, "transit_days": 0},
                                "deposit_pct": 1, "moq": 1, "seasonality": [1] * 11})
