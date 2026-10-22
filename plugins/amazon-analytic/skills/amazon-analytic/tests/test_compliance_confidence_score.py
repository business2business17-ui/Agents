from mia.compliance import BLOCKED, PASS, REVIEW, run_compliance
from mia.config import Config
from mia.confidence import assess_confidence
from mia.score import niche_score

CFG = Config()


def ids(res):
    return {i.check_id for i in res.items}


def test_de_cosmetics_requires_epr_cpnp_gpsr():
    r = run_compliance("DE", "skincare", "private_label")
    assert {"epr_packaging", "cosmetics_rp_cpnp", "gpsr", "vat_registration", "cosmetics_labeling"} <= ids(r)
    assert "mocra" not in ids(r)
    assert r.overall == REVIEW            # ничего не подтверждено → REVIEW, а не PASS


def test_us_cosmetics_requires_mocra_not_eu_rules():
    r = run_compliance("US", "skincare", "private_label")
    assert "mocra" in ids(r)
    assert not {"epr_packaging", "gpsr", "cosmetics_rp_cpnp"} & ids(r)


def test_uk_uses_scpn_not_cpnp_or_gpsr():
    r = run_compliance("UK", "skincare", "private_label")
    assert "cosmetics_scpn" in ids(r)
    assert not {"cosmetics_rp_cpnp", "gpsr"} & ids(r)


def test_hazmat_by_category_or_flag():
    assert "dangerous_goods" in ids(run_compliance("DE", "fragrance", "resale"))
    assert "dangerous_goods" in ids(run_compliance("DE", "home", "resale", flags={"hazmat": True}))
    assert "dangerous_goods" not in ids(run_compliance("DE", "home", "resale"))


def test_resale_vs_private_label_rules():
    assert "resale_authorization" in ids(run_compliance("DE", "home", "resale"))
    assert "brand_rights" not in ids(run_compliance("DE", "home", "resale"))


def test_pass_requires_evidence_and_hard_block():
    statuses = {"brand_rights": {"status": PASS}}
    r = run_compliance("US", "home", "private_label", statuses=statuses)
    item = next(i for i in r.items if i.check_id == "brand_rights")
    assert item.status == REVIEW
    r = run_compliance("US", "home", "private_label",
                       statuses={"brand_rights": {"status": BLOCKED, "removable": False}})
    assert r.overall == BLOCKED and r.hard_block


def test_confidence_weakest_link():
    c = assess_confidence(CFG, coverage=0.9, source_divergence=0.1, calibrated=False, data_age_days=5,
                          cogs_status="supplier_quote", seasonality="history", peak_period=False)
    assert c.level == "HIGH"
    c = assess_confidence(CFG, coverage=0.9, source_divergence=0.7, calibrated=False, data_age_days=5,
                          cogs_status="supplier_quote", seasonality="history", peak_period=False)
    assert c.level == "LOW" and c.weakest() == ["sources"]
    c = assess_confidence(CFG, coverage=0.9, source_divergence=None, calibrated=False, data_age_days=5,
                          cogs_status="supplier_quote", seasonality="history", peak_period=False)
    assert c.level == "MEDIUM"
    c = assess_confidence(CFG, coverage=0.9, source_divergence=0.1, calibrated=False, data_age_days=5,
                          cogs_status="supplier_quote", seasonality="none", peak_period=True)
    assert c.level == "LOW"


FULL = {"niche_revenue_month": 240_000, "nonbranded_share": 0.6, "monthly_cv": 0.25, "trend_12m": 0.1,
        "contestable_revenue_base": 12_000, "nesr": 0.3, "contribution_margin": 0.25,
        "capital_roi_12m": 1.0, "review_median_top10": 500, "hhi_brand": 1800,
        "amazon_retail_share": 0.2, "cpc": 0.5, "cvr_ads": 0.1, "pre_ad_contribution": 10.0,
        "addressable_pain_points": 2}


def test_score_deterministic_and_bounded():
    s = niche_score(CFG, "private_label", FULL)
    assert 0 <= s.score <= 100
    assert s.score == niche_score(CFG, "private_label", dict(FULL)).score
    assert not s.missing


def test_score_negative_margin_zeroes_economics():
    s = niche_score(CFG, "private_label", {**FULL, "contribution_margin": -0.05})
    assert s.components["economics"] == 0.0


def test_score_not_computed_when_too_much_missing():
    partial = {k: v for k, v in FULL.items() if k not in ("contribution_margin", "capital_roi_12m",
                                                          "contestable_revenue_base", "nesr")}
    s = niche_score(CFG, "private_label", partial)
    assert s.score is None and {"economics", "contestable"} <= set(s.missing)


def test_score_no_data_quality_component():
    assert "data_quality" not in CFG.score_weights
    assert abs(sum(CFG.score_weights.values()) - 1) < 1e-9
