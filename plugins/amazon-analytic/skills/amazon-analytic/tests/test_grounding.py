import pytest

from mia.grounding import MetricRegistry, grounded_generate, validate


@pytest.fixture
def reg():
    r = MetricRegistry()
    r.add("price", 19.99, "EUR", "assumed")
    r.add("margin", 0.242, "pct", "derived")
    r.add("units", {"low": 14, "base": 65, "high": 142}, "units", "estimated")
    r.add("capital", 5910.4, "EUR", "derived", decimals=0)
    return r


def test_render(reg):
    out = reg.render("Цена {{metric:price}}, маржа {{metric:margin}}, капитал {{metric:capital}}.")
    assert out == "Цена €19,99, маржа 24,2 %, капитал €5 910."
    assert reg.render("{{metric:units}}") == "14 шт. – 142 шт. (base 65 шт.)"


def test_ungrounded_number_detected(reg):
    v = validate("Маржа около 25 % при цене {{metric:price}}.", reg)
    assert [x.token for x in v] == ["25"]


def test_unknown_metric_detected(reg):
    v = validate("Прибыль {{metric:profit}}.", reg)
    assert v[0].kind == "unknown_metric"


@pytest.mark.parametrize("text", [
    "Лидеры TOP 10 и CR10 выше, чем TOP 3/5/10.",
    "Правило R5b, контрольная точка D30, ASIN B0EXAMPL01, см. §11.2, Agent №1.",
    "1. Первый пункт\n2. Второй пункт",
])
def test_identifiers_allowed(reg, text):
    assert validate(text, reg) == []


def test_duplicate_metric_rejected(reg):
    with pytest.raises(ValueError):
        reg.add("price", 1, "EUR", "derived")


def test_grounded_generate_retries_then_succeeds(reg):
    calls = []

    def llm(prompt):
        calls.append(prompt)
        return "Цена 20 евро." if len(calls) == 1 else "Цена {{metric:price}}."

    res = grounded_generate(llm, "опиши", reg)
    assert res.attempts == 2 and res.text == "Цена €19,99."
    assert "ОТКЛОНЕНО" in calls[1]


def test_grounded_generate_drops_bad_sentences_after_retries(reg):
    res = grounded_generate(lambda p: "Цена {{metric:price}}. Продажи вырастут на 300 %.", "x", reg,
                            max_retries=1)
    assert res.attempts == 2
    assert res.text == "Цена €19,99."
    assert res.dropped_sentences == ["Продажи вырастут на 300 %."]
