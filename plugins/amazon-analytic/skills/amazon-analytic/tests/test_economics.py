"""Golden-тесты формул §11.2 (эталон посчитан вручную)."""
import pytest

from mia.economics import (FeeSchedule, ReferralRule, TaxContext, UnitCosts, break_even_units,
                           min_viable_price, plan_initial_inventory, LeadTime, unit_economics,
                           reorder_point)

DE = TaxContext("DE", 0.19, True)
US = TaxContext("US", 0.0, False)
WHOLE = ReferralRule.from_dict({"kind": "whole", "tiers": [[10, 0.08], [None, 0.15]], "min_fee": 0.30})
FEES = FeeSchedule(WHOLE, fulfillment_fee=3.40, storage_per_unit=0.12, other_amazon_fees=0.05)
COSTS = UnitCosts(cogs=3.20, inbound_freight=0.60, prep=0.15, duties=0.10, other_variable=0.10,
                  return_rate=0.03, unsellable_share=0.5)


def test_golden_de_unit_economics():
    ue = unit_economics(19.99, DE, FEES, COSTS, tacos_net=0.11)
    net = 19.99 / 1.19
    referral = 19.99 * 0.15                       # от цены С НДС
    fees = referral + 3.40 + 0.12 + 0.05
    landed = 4.05
    returns = 0.03 * (0 + 0.5 * landed + 3.40)    # lost fees по умолчанию = fulfillment fee
    pre = net - landed - fees - returns - 0.10
    assert ue.net_revenue == pytest.approx(net)
    assert ue.referral_fee == pytest.approx(referral)
    assert ue.pre_ad_contribution == pytest.approx(pre)
    assert ue.post_ad_contribution == pytest.approx(pre - 0.11 * net)
    assert ue.be_acos_net == pytest.approx(pre / net)
    assert ue.be_acos_console == pytest.approx(pre / 19.99)
    # В EU BE ACoS для консоли (от gross) всегда ниже, чем в net-базе — ровно в (1+VAT) раз.
    assert ue.be_acos_net / ue.be_acos_console == pytest.approx(1.19)


def test_us_price_is_net():
    ue = unit_economics(19.99, US, FEES, COSTS)
    assert ue.net_revenue == pytest.approx(19.99)
    assert ue.be_acos_net == pytest.approx(ue.be_acos_console)


def test_referral_whole_vs_marginal_and_min_fee():
    assert WHOLE.fee(10.00) == pytest.approx(0.80)
    assert WHOLE.fee(10.01) == pytest.approx(1.5015)     # вся цена по 15 %
    assert WHOLE.fee(2.00) == pytest.approx(0.30)        # минимальная комиссия
    marg = ReferralRule.from_dict({"kind": "marginal", "tiers": [[250, 0.20], [None, 0.05]]})
    assert marg.fee(300) == pytest.approx(250 * 0.20 + 50 * 0.05)
    assert marg.fee(100) == pytest.approx(20.0)


def test_referral_rule_validation():
    with pytest.raises(ValueError):
        ReferralRule.from_dict({"kind": "whole", "tiers": [[10, 0.08]]})
    with pytest.raises(ValueError):
        ReferralRule.from_dict({"kind": "flat", "tiers": [[None, 0.1]]})


def test_coupon_reduces_net_revenue_net_of_vat():
    c = UnitCosts(cogs=3.2, coupon_gross=1.19)
    ue = unit_economics(19.99, DE, FEES, c)
    assert ue.net_revenue == pytest.approx(19.99 / 1.19 - 1.0)


def test_break_even_units_none_when_not_profitable():
    assert break_even_units(2500, 4.0) == 625
    assert break_even_units(2500, 0.0) is None
    assert break_even_units(2500, -1.0) is None


def test_min_viable_price_handles_tier_jump():
    price = min_viable_price(DE, FEES, COSTS, tacos_net=0.11, search_max=60)
    assert unit_economics(price, DE, FEES, COSTS, 0.11).post_ad_contribution >= 0
    assert unit_economics(price - 0.01, DE, FEES, COSTS, 0.11).post_ad_contribution < 0


def test_min_viable_price_none_if_never_profitable():
    huge = UnitCosts(cogs=1000)
    assert min_viable_price(DE, FEES, huge, 0.1, search_max=50) is None


def test_unknown_cost_field_rejected():
    with pytest.raises(ValueError):
        UnitCosts.from_dict({"cogs": 1, "cogz": 2})


def test_inventory_plan_moq_and_capacity():
    lt = LeadTime(30, 35, 5, 10)   # 80 дней
    plan = plan_initial_inventory([30] * 12, lt, 60, moq=500, fba_capacity_units=300, z=1.65)
    assert plan.initial_units == 500                 # спрос за 140 дн. = 140 < MOQ
    assert not plan.capacity_ok                      # → R4
    assert plan.sd_assumed


def test_reorder_point_periodic_review():
    # 2 шт./день, LT 80, R 30 → 220 + z·σ·√110
    assert reorder_point(2, 0, 80, 1.65) == pytest.approx(220)
    assert reorder_point(2, 1, 80, 1.65) == pytest.approx(220 + 1.65 * 110 ** 0.5)
