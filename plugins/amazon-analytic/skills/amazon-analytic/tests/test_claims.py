import pytest

from mia.claims import NEEDS_EVIDENCE, PROHIBITED, check_claims
from mia.compliance import BLOCKED, PASS, REVIEW, run_compliance


def ids(res):
    return {i.check_id for i in res.items}


def item(res, cid):
    return next(i for i in res.items if i.check_id == cid)


@pytest.mark.parametrize("claim,rule", [
    ("Противовоспалительный эффект благодаря MSM", "anti_inflammatory"),
    ("Natural Anti-Inflammatory joint support", "anti_inflammatory"),
    ("Suplemento antiinflamatorio para perros", "anti_inflammatory"),
    ("Entzündungshemmend für Hunde", "anti_inflammatory"),
    ("Обезболивает и снимает боль в суставах", "pain_relief"),
    ("Para perros con artrosis", "disease_name"),
    ("Помогает при артрите", "disease_name"),
])
def test_prohibited_feed_claims(claim, rule):
    found = check_claims([claim], "pet_supplements")
    assert any(f.rule_id == rule and f.severity == PROHIBITED for f in found)


@pytest.mark.parametrize("claim", [
    "Created by Specialist Veterinarians",
    "Clinically proven formula",
])
def test_claims_needing_evidence(claim):
    found = check_claims([claim], "pet_supplements")
    assert found and all(f.severity == NEEDS_EVIDENCE for f in found)


@pytest.mark.parametrize("claim", [
    "Supports joint mobility and flexibility",
    "Joint Treats for dogs with green lip mussel",     # treats = лакомства
    "Soporte articular con glucosamina y condroitina",
])
def test_safe_claims_pass(claim):
    assert check_claims([claim], "pet_supplements") == []


def test_dietetic_feed_wording_allowed_only_with_flag():
    claim = "Support of joint metabolism in the case of osteoarthritis"
    assert check_claims([claim], "pet_supplements")                       # без флага — болезнь
    assert check_claims([claim], "pet_supplements", dietetic_feed=True) == []


def test_other_categories_have_no_stoplist():
    assert check_claims(["anti-inflammatory"], "home") == []


def test_es_pet_feed_rules():
    r = run_compliance("ES", "pet_supplements", "private_label")
    assert {"feed_business_registration", "feed_ingredients", "feed_labelling", "feed_claims",
            "epr_packaging", "vat_registration"} <= ids(r)
    assert "gpsr" not in ids(r)                    # GPSR не распространяется на корма
    assert "feed_dietetic" not in ids(r)
    assert "feed_dietetic" in ids(run_compliance("ES", "pet_supplements", "private_label",
                                                 flags={"dietetic_feed": True}))


def test_prohibited_claim_overrides_pass_and_is_removable():
    r = run_compliance("ES", "pet_supplements", "private_label",
                       statuses={"feed_claims": {"status": PASS, "evidence_ref": "claims matrix v1"}},
                       claims=["Joint support, anti-inflammatory (MSM)"])
    it = item(r, "feed_claims")
    assert it.status == BLOCKED and it.removable and "anti-inflammatory" in it.note
    assert r.overall == BLOCKED and not r.hard_block     # R3 HOLD, а не R1 NO-GO
    assert r.as_dict()["claim_findings"][0]["rule_id"] == "anti_inflammatory"


def test_evidence_claim_downgrades_pass_to_review():
    r = run_compliance("ES", "pet_supplements", "private_label",
                       statuses={"feed_claims": {"status": PASS, "evidence_ref": "claims matrix v1"}},
                       claims=["Created by Specialist Veterinarians"])
    assert item(r, "feed_claims").status == REVIEW


def test_clean_claims_keep_user_status():
    r = run_compliance("ES", "pet_supplements", "private_label",
                       statuses={"feed_claims": {"status": PASS, "evidence_ref": "claims matrix v1"}},
                       claims=["Supports joint mobility"])
    assert item(r, "feed_claims").status == PASS
