"""Числовое заземление LLM-текста (ТЗ v1.2 §1 п.6, §20.3).

Закрывает P8: LLM пишет числа только плейсхолдерами {{metric:<id>}}, значения
подставляет код из реестра. Любая цифра вне плейсхолдера (кроме идентификаторов
вроде TOP 10, CR10, R5b, D30, ASIN, §11.2) — нарушение.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

PLACEHOLDER = re.compile(r"\{\{metric:([A-Za-z0-9_.\-]+)\}\}")

ALLOWED_IDENTIFIERS = [
    r"\bTOP\s?\d+(?:/\d+)*",                 # TOP 10, TOP 3/5/10
    r"\bCR\d+(?:/\d+)*",                     # CR10, CR3/5/10
    r"\bR[0-5][a-d]?\b",                     # правила Decision Engine
    r"\b[DM]\d{1,3}\b",                      # D30, M6
    r"\bQ[1-4]\b",
    r"\bP(?:25|50|75)\b",
    r"\bB0[A-Z0-9]{8}\b",                    # ASIN
    r"§\d+(?:\.\d+)*",                       # ссылки на разделы ТЗ
    r"\bv\d+(?:\.\d+)*",                     # версии
    r"№\s?\d+",                              # Agent №1
    r"\b(?:Phase|фаза)\s?\d\b",
    r"^\s*\d{1,2}[.)]\s",                    # нумерация списка (MULTILINE)
]
_ALLOWED = re.compile("|".join(ALLOWED_IDENTIFIERS), re.IGNORECASE | re.MULTILINE)
_NUMBER = re.compile(r"\d[\d\s.,]*\d|\d")

CURRENCY_SIGNS = {"EUR": "€", "USD": "$", "GBP": "£"}


def _fmt_number(x: float, decimals: int) -> str:
    s = f"{x:,.{decimals}f}".replace(",", " ")   # узкий неразрывный пробел как разделитель тысяч
    return s.replace(".", ",") if decimals else s


@dataclass
class Metric:
    metric_id: str
    value: object
    unit: str                 # EUR|USD|GBP|pct|units|count|days|month|score|ratio|date|text
    data_type: str            # observed|estimated|derived|assumed|calibrated
    source: str | None = None
    decimals: int | None = None


class MetricRegistry:
    def __init__(self):
        self._m: dict[str, Metric] = {}

    def add(self, metric_id, value, unit, data_type, source=None, decimals=None) -> str:
        if metric_id in self._m:
            raise ValueError(f"duplicate metric_id {metric_id}")
        self._m[metric_id] = Metric(metric_id, value, unit, data_type, source, decimals)
        return metric_id

    def __contains__(self, metric_id):
        return metric_id in self._m

    def get(self, metric_id) -> Metric:
        return self._m[metric_id]

    def ids(self):
        return list(self._m)

    def as_list(self) -> list:
        return [m.__dict__.copy() for m in self._m.values()]

    def format(self, metric_id: str) -> str:
        m = self._m[metric_id]
        v = m.value
        if v is None:
            return "н/д"
        if isinstance(v, dict) and {"low", "base", "high"} <= set(v):
            lo, ba, hi = (self._fmt_scalar(m, v[k]) for k in ("low", "base", "high"))
            return f"{lo} – {hi} (base {ba})"
        return self._fmt_scalar(m, v)

    @staticmethod
    def _fmt_scalar(m: Metric, v) -> str:
        if m.unit in ("date", "text"):
            return str(v)
        if m.unit in CURRENCY_SIGNS:
            d = 2 if m.decimals is None else m.decimals
            return f"{CURRENCY_SIGNS[m.unit]}{_fmt_number(v, d)}"
        if m.unit == "pct":
            d = 1 if m.decimals is None else m.decimals
            return f"{_fmt_number(v * 100, d)} %"
        if m.unit == "units":
            return f"{_fmt_number(v, 0 if m.decimals is None else m.decimals)} шт."
        if m.unit == "days":
            return f"{_fmt_number(v, 0)} дн."
        if m.unit == "month":
            return f"месяц {int(v)}"
        d = (0 if isinstance(v, int) else 2) if m.decimals is None else m.decimals
        return _fmt_number(v, d)

    def render(self, template: str) -> str:
        def sub(mo):
            mid = mo.group(1)
            if mid not in self._m:
                raise KeyError(f"unknown metric_id {mid}")
            return self.format(mid)
        return PLACEHOLDER.sub(sub, template)


@dataclass
class Violation:
    kind: str          # unknown_metric | ungrounded_number
    token: str
    context: str


def validate(template: str, registry: MetricRegistry, facts=None) -> list:
    """facts: factcheck.FactTable — добавляет проверку {{cmp|rank|ing|count:…}} и словесных сравнений."""
    out = []
    for mo in PLACEHOLDER.finditer(template):
        if mo.group(1) not in registry:
            out.append(Violation("unknown_metric", mo.group(1), _ctx(template, mo.start(), mo.end())))
    if facts is not None:
        out.extend(facts.lint(template))
        template = facts.strip(template)
    stripped = PLACEHOLDER.sub(lambda mo: " " * len(mo.group(0)), template)
    stripped = _ALLOWED.sub(lambda mo: " " * len(mo.group(0)), stripped)
    for mo in _NUMBER.finditer(stripped):
        out.append(Violation("ungrounded_number", mo.group(0).strip(), _ctx(template, mo.start(), mo.end())))
    return out


def _ctx(text, a, b, pad=30):
    return text[max(0, a - pad):min(len(text), b + pad)].replace("\n", " ")


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass
class GroundedText:
    text: str
    attempts: int
    dropped_sentences: list = field(default_factory=list)
    violations: list = field(default_factory=list)


def grounded_generate(llm, prompt: str, registry: MetricRegistry, max_retries: int = 2,
                      facts=None) -> GroundedText:
    """llm(prompt) -> str. До max_retries перегенераций с обратной связью; затем
    из текста удаляются предложения с нарушениями (и это логируется в результате).
    facts: factcheck.FactTable — сравнения и состав конкурентов тоже только через плейсхолдеры."""
    def render(text):
        return registry.render(facts.render(text) if facts is not None else text)

    rules = "Числа допускаются только как {{metric:<id>}}."
    if facts is not None:
        rules += (" Сравнения — только {{cmp:<id>.<field>|<id>.<field>}}, место — {{rank:<id>.<field>}},"
                  " состав — {{ing:<id>:<ingredient>}}, количество — {{count:<kind>/<tag>}};"
                  " словесные числа («вдвое», «трёх») и «единственный» запрещены.")
    feedback, attempts, last, last_v = "", 0, "", []
    for attempts in range(1, max_retries + 2):
        last = llm(prompt + feedback)
        last_v = validate(last, registry, facts)
        if not last_v:
            return GroundedText(render(last), attempts)
        feedback = (f"\n\nОТКЛОНЕНО валидатором. {rules} "
                    "Нарушения: " + "; ".join(f"{v.kind}: '{v.token}' в «{v.context}»" for v in last_v)
                    + f"\nДоступные metric_id: {', '.join(registry.ids())}")
    kept, dropped = [], []
    for sentence in _SENTENCE_SPLIT.split(last):
        if not sentence.strip():
            continue
        (dropped if validate(sentence, registry, facts) else kept).append(sentence)
    return GroundedText(render(" ".join(kept)), attempts, dropped, last_v)
