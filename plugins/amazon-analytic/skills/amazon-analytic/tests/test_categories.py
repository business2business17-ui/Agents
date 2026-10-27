import pytest

from mia.categories import default_referral, detect_category, normalize_category
from mia.claims import NEEDS_EVIDENCE, PROHIBITED, check_claims
from mia.compliance import BLOCKED, PASS, run_compliance
from mia.importers.helium10 import _dims, _weight_kg


def ids(res):
    return {i.check_id for i in res.items}


@pytest.mark.parametrize("name,key", [
    ("Beauty", "cosmetics"), ("Kosmetik", "cosmetics"), ("Health & Personal Care", "personal_care"),
    ("Pet Supplies", "pet_supplies"), ("Haustierbedarf", "pet_supplies"), ("Toys & Games", "toys"),
    ("Küche, Haushalt & Wohnen", "kitchen"), ("Elektronik & Foto", "electronics"), ("", "other"),
    ("Something Unknown", "other"),
])
def test_normalize_category(name, key):
    assert normalize_category(name) == key


def test_detect_category_mode_and_share():
    key, share, allc = detect_category(["Beauty"] * 8 + ["Health & Personal Care"] * 2 + ["", None])
    assert key == "cosmetics" and share == 0.8 and allc == {"cosmetics": 8, "personal_care": 2}
    assert detect_category(["", None]) == ("other", 0.0, {})


def test_default_referral():
    assert default_referral("cosmetics", "DE")["tiers"] == [[10, 0.08], [None, 0.15]]
    assert default_referral("electronics", "US")["tiers"] == [[None, 0.08]]
    assert default_referral("grocery", "US")["tiers"][0] == [15, 0.08]
    assert default_referral("apparel", "DE") is None          # только из fee schedule
    assert default_referral("other", "DE") is None


# ---------- compliance по категориям

@pytest.mark.parametrize("mp,cat,expected,absent", [
    ("DE", "toys", {"toy_safety", "gpsr"}, {"cpsia_children", "toy_safety_uk"}),
    ("UK", "toys", {"toy_safety_uk"}, {"toy_safety"}),
    ("US", "baby", {"cpsia_children"}, {"toy_safety"}),
    ("DE", "electronics", {"electronics_ce", "epr_weee"}, {"electronics_fcc"}),
    ("US", "electronics", {"electronics_fcc"}, {"electronics_ce"}),
    ("DE", "kitchen", {"food_contact"}, set()),
    ("DE", "food", {"food_business_registration", "food_labelling", "food_claims"},
     {"food_supplement_notification", "fda_food"}),
    ("US", "food", {"fda_food"}, {"food_labelling"}),
    ("DE", "apparel", {"textile_labelling"}, set()),
])
def test_category_rules(mp, cat, expected, absent):
    r = ids(run_compliance(mp, cat, "private_label"))
    assert expected <= r and not (absent & r)


def test_food_contact_by_flag_in_any_category():
    assert "food_contact" in ids(run_compliance("DE", "home", "private_label", flags={"food_contact": True}))
    assert "food_contact" not in ids(run_compliance("DE", "home", "private_label"))


def test_food_supplement_flag():
    assert "food_supplement_notification" in ids(
        run_compliance("DE", "food", "private_label", flags={"food_supplement": True}))


# ---------- стоп-листы claims по группам

@pytest.mark.parametrize("claim,rule,sev", [
    ("Heals eczema in 3 days", "treats_cures", PROHIBITED),
    ("Anti-inflammatory night cream", "anti_inflammatory", PROHIBITED),
    ("For eczema-prone skin", "skin_disease", NEEDS_EVIDENCE),
    ("Hair regrowth serum", "hair_regrowth", NEEDS_EVIDENCE),
    ("Tea Tree Antifungal Soap Bar", "antimicrobial", NEEDS_EVIDENCE),
    ("Sun lotion SPF 50", "spf_claim", NEEDS_EVIDENCE),
    ("Dermatologically tested", "dermatologist", NEEDS_EVIDENCE),
])
def test_cosmetic_claims(claim, rule, sev):
    found = check_claims([claim], "cosmetics")
    assert any(f.rule_id == rule and f.severity == sev for f in found)


@pytest.mark.parametrize("claim", ["Intensive hair treatment mask", "Moisturising body lotion for dry skin"])
def test_cosmetic_safe_claims(claim):
    assert check_claims([claim], "cosmetics") == []         # «treatment» в косметике — формат, не лечение


def test_food_claims():
    found = {f.rule_id: f.severity for f in check_claims(["Prevents cancer", "Boosts immunity"], "food")}
    assert found == {"prevents_disease": PROHIBITED, "unauthorised_health": NEEDS_EVIDENCE}


def test_categories_without_stoplist():
    assert check_claims(["cures everything"], "toys") == []


def test_cosmetic_claim_blocks_cosmetic_claims_item():
    r = run_compliance("DE", "cosmetics", "private_label",
                       statuses={"cosmetic_claims": {"status": PASS, "evidence_ref": "matrix"}},
                       claims=["Cures acne overnight"])
    item = next(i for i in r.items if i.check_id == "cosmetic_claims")
    assert item.status == BLOCKED and item.removable


# ---------- единицы измерения

def test_units_eu_and_us():
    assert _dims("16,30 x 2,90 x 6,30 cm", ",", "UK") == [16.3, 2.9, 6.3]
    assert _dims("6.4 x 1.1 x 2.5 inches", ".", "US") == [16.26, 2.79, 6.35]
    assert _dims("6.4 x 1.1 x 2.5", ".", "US") == [16.26, 2.79, 6.35]       # US без единицы — дюймы
    assert _weight_kg("0,22", "Weight", ",", "DE") == 0.22
    assert _weight_kg("0.5", "Weight", ".", "US") == pytest.approx(0.2268, abs=1e-4)
    assert _weight_kg("8 oz", "Weight", ".", "US") == pytest.approx(0.2268, abs=1e-4)
    assert _weight_kg("N/A", "Weight", ",", "DE") is None
