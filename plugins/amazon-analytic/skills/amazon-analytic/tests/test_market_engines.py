import pytest

from mia.buybox import Offer, buybox_analysis
from mia.config import Config
from mia.contestable import KeywordCluster, ScenarioValues, cohort_stats, contestable_market

CFG = Config()
SV = ScenarioValues


def cluster(cid, kws, sv=10000, cs=(0.01, 0.02, 0.03), cvr=(0.1, 0.1, 0.1)):
    return KeywordCluster(cid, tuple(kws), sv, SV(*cs), SV(*cvr))


# ---------------------------------------------------------------- contestable

def test_contestable_is_min_of_constraints_with_binding():
    cl = [cluster("a", ["x"])]                     # спрос base = 10000·0.02·0.1 = 20
    r = contestable_market(cl, ppc_budget_month=1000, cpc=SV(1, 1, 1), cvr_ads=SV(0.1, 0.1, 0.1),
                           organic_multiplier=SV(0, 0, 0), price=SV(10, 10, 10),
                           supply_units_month=None, cohort=None)
    # бюджет base = 1000/1·0.1 = 100 → связывает спрос
    assert r.units.base == pytest.approx(20)
    assert r.binding_constraint["base"] == "demand"
    assert r.revenue.base == pytest.approx(200)
    assert r.empirical_status == "NOT_MEASURABLE"


def test_budget_binding():
    cl = [cluster("a", ["x"], sv=1_000_000)]
    r = contestable_market(cl, 300, SV(1.5, 1, 0.8), SV(0.1, 0.1, 0.1), SV(0.5, 0.5, 0.5),
                           SV(10, 10, 10), None, None)
    assert r.binding_constraint["base"] == "budget"
    assert r.units.base == pytest.approx(300 / 1 * 0.1 * 1.5)


def test_duplicate_keyword_across_clusters_rejected():
    with pytest.raises(ValueError):
        contestable_market([cluster("a", ["x", "y"]), cluster("b", ["y"])], 100, SV(1, 1, 1),
                           SV(.1, .1, .1), SV(0, 0, 0), SV(1, 1, 1), None, None)


def test_cohort_thresholds():
    assert cohort_stats([10] * 5, CFG).status == "NOT_MEASURABLE"
    assert cohort_stats([10] * 12, CFG).status == "LOW"
    r = cohort_stats(list(range(0, 250, 10)), CFG, exited_count=5)    # 25 + 5 выбывших
    assert r.status == "OK" and r.cohort_size == 30
    assert r.share_reaching[100] == pytest.approx(15 / 30)
    assert r.units.low <= r.units.base <= r.units.high


def test_empirical_cohort_participates():
    cl = [cluster("a", ["x"], sv=1_000_000)]
    coh = cohort_stats([5] * 25, CFG)
    r = contestable_market(cl, 10_000, SV(1, 1, 1), SV(.1, .1, .1), SV(0, 0, 0), SV(1, 1, 1), None, coh)
    assert r.binding_constraint["base"] == "empirical"
    assert r.units.base == pytest.approx(5)


# ---------------------------------------------------------------- buy box

OFFERS = [Offer("S1", 24.90, is_fba=True), Offer("S2", 25.30, is_fba=True),
          Offer("S3", 24.95, is_fba=True), Offer("S4", 27.50), Offer("ME", 24.90, is_fba=True)]


def test_buybox_competitive_count_and_shares():
    r = buybox_analysis("B0EXAMPL01", OFFERS, 24.90, SV(900, 1200, 1500), CFG, our_seller_id="ME",
                        new_sellers_90d=2, amazon_bb_share=0.0, has_resale_authorization=True)
    # S1, S3 в пределах +2 %, S2 = +1.6 % тоже; S4 FBM без Prime — нет
    assert r.n_competitive == 3
    assert r.bb_share.base == pytest.approx(1 / 4)
    assert r.bb_share.low == pytest.approx(1 / 6)
    assert r.units.base == pytest.approx(300)
    assert not r.hard_stops and not r.reviews


def test_amazon_dominance_is_hard_stop():
    offers = OFFERS + [Offer("AMZ", 24.90, is_amazon=True)]
    r = buybox_analysis("B0EXAMPL01", offers, 24.90, SV(1, 1, 1), CFG, amazon_bb_share=0.7,
                        has_resale_authorization=True)
    assert r.hard_stops


def test_missing_authorization_and_ip_flags():
    r = buybox_analysis("B0EXAMPL01", OFFERS, 24.90, SV(1, 1, 1), CFG, brand_ip_complaints=True)
    assert r.reviews and r.caps
