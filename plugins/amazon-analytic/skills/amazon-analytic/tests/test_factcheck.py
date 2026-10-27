"""Регрессия на ошибки отчёта «Хондропротекторы, Amazon.ES» (срез 24.08.2026).

Данные — строки таблицы конкурентов из самого отчёта; каждая проверка ловит
конкретную фразу, которая противоречила этой таблице.
"""
import pytest

from mia.config import Config
from mia.factcheck import (HYPOTHESIS, FactTable, check_product_card, compare_phrase)
from mia.grounding import MetricRegistry, grounded_generate, validate

ALIASES = {"green_mussel": ["мидии", "мидия", "mussel"], "devils_claw": ["devil's claw", "harpago"]}

ROWS = [
    {"id": "veddelholzer", "brand": "Veddelholzer", "values": {"units": 3345, "reviews": 9286, "price": 22.45},
     "ingredients": {"green_mussel": "label", "devils_claw": "label", "glucosamine": "label"},
     "tags": {"devils_claw", "made_in_germany"}},
    {"id": "acevit", "brand": "Acevit Nutrition", "values": {"units": 1864, "reviews": 498, "price": 19.99},
     "ingredients": {"glucosamine": "label", "msm": "label"}, "tags": {"mass_market"}},
    {"id": "faucare", "brand": "Faucare", "values": {"units": 1146, "reviews": 180, "price": 28.95},
     "ingredients": {"glucosamine": "label", "green_mussel": "label"}, "tags": {"mass_market"}},
    {"id": "petsuplus", "brand": "PETSUPLUS", "values": {"units": 787, "reviews": 1060, "price": 23.99},
     "ingredients": {"glucosamine": "label", "green_mussel": "label"}, "tags": {"mass_market"}},
    {"id": "ivvi", "brand": "ivvi", "values": {"units": 456, "reviews": 1546, "price": 29.90},
     "ingredients": {"green_mussel": "label", "msm": "label"}, "tags": {"mass_market", "treat"}},
    {"id": "natureflow", "brand": "Natureflow", "values": {"units": 234, "reviews": 6658, "price": 21.79},
     "ingredients": {"green_mussel": "label", "devils_claw": "label"}, "tags": {"devils_claw", "senior"}},
    {"id": "hifarmax20", "brand": "Hifarmax", "values": {"units": 212, "reviews": 218, "price": 46.98},
     "ingredients": {"glucosamine": "photo"}, "tags": {"senior"}},
    {"id": "jointsure", "brand": "JOINTSURE", "values": {"units": 204, "reviews": 7568, "price": 25.86},
     "ingredients": {"green_mussel": "label", "glucosamine": "label"}, "tags": {"mass_market"}},
    {"id": "hifarmax_pro", "brand": "Hifarmax", "values": {"units": 169, "reviews": 118, "price": 53.80},
     "ingredients": {"turmeric": "photo"}, "tags": {"senior"}},
    {"id": "canivet", "brand": "CANIVET", "values": {"units": 123, "reviews": 315, "price": 18.99},
     "ingredients": {"green_mussel": "label"}, "tags": {"mass_market"}},
    {"id": "vetplus", "brand": "VetPlus", "values": {"units": 122, "reviews": 64, "price": 25.90},
     "ingredients": None, "tags": {"small_medium"}},
    {"id": "dognity_senior", "brand": "Dognity", "values": {"units": 76, "reviews": 44, "price": 21.99},
     "ingredients": {"glucosamine": "label"}, "tags": {"senior", "large_breed"}},
    {"id": "clinix", "name": "09 Clinix Formula", "kind": HYPOTHESIS, "tags": {"vet_trust"}},
    {"id": "p01", "name": "01 Base Chews", "kind": HYPOTHESIS, "tags": {"mass_market"}},
    {"id": "p02", "name": "02 Value Pack", "kind": HYPOTHESIS, "tags": {"mass_market"}},
    {"id": "p03", "name": "03 Treat Snacks", "kind": HYPOTHESIS, "tags": {"mass_market"}},
    {"id": "p04", "name": "04 Mussel Formula", "kind": HYPOTHESIS, "tags": {"mass_market"}},
    {"id": "p05", "name": "05 TrustCare", "kind": HYPOTHESIS, "tags": {"mass_market"}},
]


@pytest.fixture
def facts():
    f = FactTable(ingredient_aliases=ALIASES)
    for r in ROWS:
        f.add_row(r)
    return f


@pytest.fixture
def reg(facts):
    r = MetricRegistry()
    facts.to_registry(r, source="helium10-like 2026-08-24")
    return r


def kinds(violations):
    return [v.kind for v in violations]


# ---------- ошибки из отчёта

def test_report_error_jointsure_vs_ivvi(facts, reg):
    # Отчёт: «JOINTSURE… почти вдвое больше, чем ivvi». По таблице 204 против 456.
    assert "ungrounded_comparison" in kinds(validate("JOINTSURE продаёт почти вдвое больше, чем ivvi.", reg, facts))
    fixed = "JOINTSURE продаёт {{cmp:jointsure.units|ivvi.units}}, чем ivvi."
    assert validate(fixed, reg, facts) == []
    assert facts.render(fixed) == "JOINTSURE продаёт в 2,2 раза меньше, чем ivvi."


def test_report_error_leaders_without_mussel(facts, reg):
    # Отчёт: «Veddelholzer и Natureflow… оба без мидии». По таблице мидия есть у обоих.
    v = validate("Оба лидера Devil's Claw-сегмента без мидии.", reg, facts)
    assert "ungrounded_ingredient_claim" in kinds(v)
    assert facts.render("Мидия у Veddelholzer: {{ing:veddelholzer:green_mussel}}.") == \
        "Мидия у Veddelholzer: есть (этикетка)."
    ok, why = facts.check_assertion({"type": "lacks", "entity": "natureflow", "ingredient": "green_mussel"})
    assert ok is False


def test_report_error_faucare_twice_next(facts):
    # Отчёт: «Faucare почти в 2 раза больше следующего конкурента» (следующий — PETSUPLUS 787).
    assert compare_phrase(facts.value("faucare.units"), facts.value("petsuplus.units")) == "на 46 % больше"
    # И Faucare не лидер: выше Veddelholzer и Acevit.
    assert facts.render("{{rank:faucare.units}}") == "#3 из 12"


def test_report_error_first_of_three(facts, reg):
    # Отчёт: «первый из трёх масс-маркет продуктов», а их пять.
    assert "ungrounded_comparison" in kinds(validate("Первый из трёх масс-маркет продуктов.", reg, facts))
    assert facts.render("Масс-маркет продуктов: {{count:hypothesis/mass_market}}.") == "Масс-маркет продуктов: 5."


def test_uniqueness_requires_count(facts, reg):
    assert "ungrounded_uniqueness" in kinds(
        validate("Hifarmax — единственный бренд с Senior в заголовке.", reg, facts))


def test_unknown_composition_is_no_data_not_absence(facts):
    assert facts.render("{{ing:vetplus:green_mussel}}") == "нет данных"
    ok, _ = facts.check_assertion({"type": "lacks", "entity": "vetplus", "ingredient": "green_mussel"})
    assert ok is None


def test_competitor_values_grounded_through_registry(facts, reg):
    assert reg.render("{{metric:comp.ivvi.units}}") == "456 шт."
    assert kinds(validate("ivvi продаёт 456 штук.", reg, facts)) == ["ungrounded_number"]


def test_unknown_fact_reference(facts, reg):
    assert kinds(validate("{{cmp:nobody.units|ivvi.units}}", reg, facts)) == ["unknown_fact"]


# ---------- карточки продуктов

MIN = Config().model_min_units


def test_card_senior_model_out_of_segment(facts):
    # Продукт 07: CANIVET (не senior) засчитан третьей моделью сеньор-сегмента.
    c = check_product_card({"product_id": "07", "segment_tags": ["senior"], "models_count": 3,
                            "models": ["hifarmax20", "hifarmax_pro", "canivet"]}, facts, MIN)
    assert c.valid_models == ["hifarmax20", "hifarmax_pro"]
    assert c.brands == 1                       # обе модели — один бренд
    assert kinds(c.violations) == ["model_out_of_segment", "models_count_mismatch"]


def test_card_circular_evidence(facts):
    # Продукт 05 обосновывает спрос нашим же продуктом 09.
    c = check_product_card({"product_id": "05", "segment_tags": [], "models": ["clinix"]}, facts, MIN)
    assert kinds(c.violations) == ["circular_evidence"] and c.valid_models == []


def test_card_below_threshold(facts):
    # Продукт 13: Dognity 76 продаж < 100.
    c = check_product_card({"product_id": "13", "segment_tags": ["senior", "large_breed"],
                            "models": ["dognity_senior"]}, facts, MIN)
    assert kinds(c.violations) == ["model_below_threshold"]


def test_card_valid(facts):
    c = check_product_card({"product_id": "01", "segment_tags": ["mass_market"],
                            "models": ["faucare", "petsuplus"], "models_count": 2}, facts, MIN)
    assert c.violations == [] and c.brands == 2


# ---------- сравнение и генерация

@pytest.mark.parametrize("a,b,phrase", [
    (100, 100, "примерно столько же"), (150, 100, "на 50 % больше"), (300, 100, "в 3,0 раза больше"),
    (60, 100, "на 40 % меньше"), (25, 100, "в 4,0 раза меньше"),
])
def test_compare_phrase(a, b, phrase):
    assert compare_phrase(a, b) == phrase


def test_grounded_generate_with_facts(facts, reg):
    calls = []

    def llm(prompt):
        calls.append(prompt)
        return ("JOINTSURE продаёт вдвое больше, чем ivvi." if len(calls) == 1
                else "JOINTSURE продаёт {{cmp:jointsure.units|ivvi.units}}, чем ivvi "
                     "({{metric:comp.jointsure.units}}).")

    res = grounded_generate(llm, "сравни", reg, facts=facts)
    assert res.attempts == 2
    assert res.text == "JOINTSURE продаёт в 2,2 раза меньше, чем ivvi (204 шт.)."
    assert "{{cmp:" in calls[1]


def test_plain_text_without_comparisons_passes(facts, reg):
    assert validate("Состав лидеров сходится на глюкозамине и мидии.", reg, facts) == []
