"""Каждое правило R0–R5 и каждое ограничение срабатывает на своём негативном тесте (§25.4)."""
import pytest

from mia.config import Config
from mia.decision import DecisionInputs, decide

CFG = Config()


def inputs(**kw):
    d = dict(business_model="private_label", missing_critical=[], compliance_overall="PASS",
             compliance_hard_block=False, compliance_open_items=[], best_base_post_ad_contribution=3.0,
             score=85, confidence="HIGH", cogs_assumed=False, conservative_loss=1000,
             capital_at_risk=3000, max_test_loss=8000, required_capital_base=10000, budget=25000,
             fba_capacity_ok=True)
    d.update(kw)
    return DecisionInputs(**d)


@pytest.mark.parametrize("kw,status,rule", [
    (dict(), "GO", "R5a"),
    (dict(missing_critical=["costs.cogs"]), "INSUFFICIENT DATA", "R0"),
    (dict(score=None), "INSUFFICIENT DATA", "R0"),
    (dict(compliance_hard_block=True, compliance_overall="BLOCKED"), "NO-GO", "R1"),
    (dict(best_base_post_ad_contribution=-0.5), "NO-GO", "R2"),
    (dict(best_base_post_ad_contribution=0.0), "NO-GO", "R2"),
    (dict(resale_hard_stops=["Amazon Retail"]), "NO-GO", "R2"),
    (dict(compliance_overall="REVIEW REQUIRED"), "HOLD", "R3"),
    (dict(compliance_overall="BLOCKED"), "HOLD", "R3"),           # устранимый BLOCKED
    (dict(resale_reviews=["нет авторизации"]), "HOLD", "R3"),
    (dict(required_capital_base=30000), "HOLD", "R4"),
    (dict(fba_capacity_ok=False), "HOLD", "R4"),
    (dict(score=70), "TEST", "R5b"),
    (dict(score=70, capital_at_risk=9000), "HOLD", "R5c"),
    (dict(score=55), "HOLD", "R5c"),
    (dict(score=40), "NO-GO", "R5d"),
])
def test_rules(kw, status, rule):
    d = decide(inputs(**kw), CFG)
    assert (d.status, d.rule) == (status, rule)
    assert d.trace and d.trace[-1]["rule"] in (rule, "caps")


def test_rule_order_r0_before_r1():
    d = decide(inputs(missing_critical=["x"], compliance_hard_block=True), CFG)
    assert d.rule == "R0"


def test_high_score_low_confidence_is_test_not_go():
    d = decide(inputs(confidence="LOW"), CFG)
    assert d.status == "TEST" and d.rule == "R5b"


def test_assumed_cogs_caps_at_test():
    d = decide(inputs(cogs_assumed=True), CFG)
    assert d.status == "TEST"


def test_conservative_loss_over_limit_blocks_go():
    d = decide(inputs(conservative_loss=9000, capital_at_risk=7000), CFG)
    assert d.status == "TEST"


def test_seasonal_anomaly_downgrades_go():
    d = decide(inputs(seasonal_anomaly=True), CFG)
    assert d.status == "TEST" and d.caps_applied


def test_resale_caps_hold():
    d = decide(inputs(business_model="resale", resale_caps=["IP-жалобы"]), CFG)
    assert d.status == "HOLD" and d.caps_applied


def test_conditional_after_fix_reported():
    d = decide(inputs(compliance_overall="REVIEW REQUIRED"), CFG)
    assert d.conditional_after_fix == "GO (R5a)"
    d = decide(inputs(fba_capacity_ok=False, score=70), CFG)
    assert d.conditional_after_fix == "TEST (R5b)"


def test_hold_is_defined_for_score_50_64():
    for s in (50, 57, 64.9):
        assert decide(inputs(score=s), CFG).status == "HOLD"
