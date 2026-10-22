import copy
import json
from pathlib import Path

import pytest

from mia.grounding import MetricRegistry, validate
from mia.pipeline import analyze

EX = Path(__file__).resolve().parent.parent / "examples"


def load(name):
    return json.loads((EX / name).read_text(encoding="utf-8"))


@pytest.fixture
def pl():
    return load("de_private_label_skincare.json")


@pytest.fixture
def rs():
    return load("de_resale_fragrance.json")


def test_reproducible(pl):
    a = json.dumps(analyze(copy.deepcopy(pl)), sort_keys=True, default=str)
    b = json.dumps(analyze(copy.deepcopy(pl)), sort_keys=True, default=str)
    assert a == b


def test_package_contract(pl):
    p = analyze(pl)
    for key in ("schema_version", "decision", "compliance", "market", "launch_plan", "economics",
                "test_plan", "metrics", "approval", "versions"):
        assert key in p
    assert p["approval"]["status"] == "pending"
    assert p["launch_plan"]["recommended_price"]["tax_basis"] == "gross_incl_vat"
    assert p["decision"]["status"] in ("GO", "TEST", "HOLD", "NO-GO", "INSUFFICIENT DATA")
    assert p["decision"]["rule_fired"].startswith("R")


def test_narrative_is_grounded(pl, rs):
    for inp in (pl, rs):
        p = analyze(inp)
        reg = MetricRegistry()
        for m in p["metrics"]:
            reg.add(m["metric_id"], m["value"], m["unit"], m["data_type"])
        assert validate(p["narrative_template"], reg) == []


def test_missing_cogs_gives_insufficient_data_with_hint(pl):
    del pl["costs"]["cogs"]
    p = analyze(pl)
    assert p["decision"]["status"] == "INSUFFICIENT DATA"
    assert "costs.cogs" in p["decision"]["how_to_get"]


def test_missing_budget_and_loss_is_critical(pl):
    pl.pop("budget"); pl.pop("max_test_loss")
    assert analyze(pl)["decision"]["status"] == "INSUFFICIENT DATA"


def test_resale_requires_buybox(rs):
    del rs["buybox"]
    p = analyze(rs)
    assert "buybox.offers" in p["decision"]["how_to_get"]


def test_resale_hazmat_open_gives_hold_r3(rs):
    p = analyze(rs)
    assert (p["decision"]["status"], p["decision"]["rule_fired"]) == ("HOLD", "R3")
    assert p["decision"]["conditional_after_fix"]


def test_amazon_dominance_is_no_go(rs):
    rs["buybox"]["amazon_bb_share"] = 0.8
    rs["buybox"]["offers"].append({"seller_id": "AMZ", "price": 24.9, "is_amazon": True})
    assert analyze(rs)["decision"]["status"] == "NO-GO"


def test_negative_economics_is_no_go(pl):
    pl["costs"]["cogs"] = 40.0
    p = analyze(pl)
    assert (p["decision"]["status"], p["decision"]["rule_fired"]) == ("NO-GO", "R2")


def test_blocked_category_high_demand(pl):
    pl["compliance"]["statuses"]["category_ungating"] = {"status": "BLOCKED", "removable": False}
    assert analyze(pl)["decision"]["rule_fired"] == "R1"


def test_capacity_below_initial_stock_is_hold(pl):
    pl["launch"]["fba_capacity_units"] = 100
    p = analyze(pl)
    assert p["decision"]["rule_fired"] in ("R4",)


def test_stale_fee_schedule_warns(pl):
    pl["fees"]["checked_at"] = "2026-01-01"
    assert any("Fee schedule" in w for w in analyze(pl)["warnings"])


def test_peak_snapshot_without_index_lowers_confidence(pl):
    pl["market"]["seasonality_source"] = "none"
    pl["market"]["peak_period"] = True
    assert analyze(pl)["decision"]["confidence"] == "LOW"


def test_better_niche_reaches_go(pl):
    """Сильная ниша с дешёвым трафиком должна получить GO — движок не «вечный HOLD»."""
    pl["ppc"]["cpc"] = {"low": 0.35, "base": 0.25, "high": 0.20}
    pl["ppc"]["budget_month"] = 3000
    pl["cohort"]["units_at_month"] = [300 + 10 * i for i in range(25)]
    for c in pl["keywords"]["clusters"]:
        c["click_share"] = {"low": 0.05, "base": 0.08, "high": 0.10}
    pl["addressable_pain_points"] = 3
    pl["market"].update(review_median_top10=300, hhi_brand=1200, trend_12m=0.25)
    p = analyze(pl)
    assert p["decision"]["status"] == "GO", p["decision"]
    assert p["decision"]["score"] >= 80


def test_same_niche_with_assumed_cogs_is_capped(pl):
    pl["costs"]["cogs_status"] = "assumed"
    p = analyze(pl)
    assert p["decision"]["confidence"] == "LOW"
    assert p["decision"]["status"] in ("TEST", "HOLD", "NO-GO")
