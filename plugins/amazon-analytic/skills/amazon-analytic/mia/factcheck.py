"""Проверка фактических утверждений о конкурентах (ТЗ v1.2 §1 п.6, §20.3).

`grounding` ловит цифры без metric_id, но пропускает словесные сравнения и
утверждения о составе: «почти вдвое больше, чем ivvi», «оба без мидии»,
«единственный бренд, который…». В отчёте по хондропротекторам ES именно такие фразы
противоречили собственной таблице отчёта.

Правило то же, что для чисел: LLM не формулирует сравнение сама, а ставит плейсхолдер,
текст фразы считает код по таблице фактов:

    {{cmp:jointsure.units|ivvi.units}}   → «в 2,2 раза меньше»
    {{rank:faucare.units}}               → «#3 из 34»
    {{ing:veddelholzer:green_mussel}}    → «есть (этикетка)» / «нет» / «нет данных»
    {{count:hypothesis/mass_market}}     → число сущностей вида/тега

Числовые значения конкурентов выгружаются в MetricRegistry (`to_registry`) и
пишутся как {{metric:comp.<id>.<field>}}.

Карточки продуктов проверяются отдельно (`check_product_card`): модели должны быть
реальными конкурентами нужного сегмента с продажами не ниже порога, а не нашими же
гипотезами.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .grounding import Violation, _ctx, _fmt_number

COMPETITOR, HYPOTHESIS = "competitor", "hypothesis"
NO_DATA = "нет данных"

FACT_PLACEHOLDER = re.compile(r"\{\{(cmp|rank|ing|count):([^}]*)\}\}")

# Словесные числа и сравнения: в свободном тексте запрещены, нужен {{cmp:…}} / {{count:…}}.
_WORD_COMPARISON = re.compile(
    r"\b(вдвое|втрое|вчетверо|впятеро|вдесятеро|в разы|полтора|полторы|половин\w*|"
    r"в\s+(два|три|четыре|пять|десять|несколько)\s+раз\w*|"
    r"двух|трёх|трех|четырёх|четырех|пяти|шести|семи|восьми|девяти|десяти|"
    r"два|две|три|четыре|пять|шесть|семь|восемь|девять|десять|"
    r"twice|double|triple|half|(two|three|four|five|ten) times)\b",
    re.IGNORECASE)
# Утверждения об уникальности тоже считаются кодом.
_UNIQUENESS = re.compile(r"\b(единственн\w*|ни один\w*|никто|only one|the only|no other)\b", re.IGNORECASE)
_NEGATION = r"(без|нет|не\s+несёт|не\s+несет|не\s+содерж\w*|отсутству\w*|without|no|lacks?)"


@dataclass
class Entity:
    entity_id: str                     # короткий slug или ASIN
    name: str
    kind: str = COMPETITOR             # competitor | hypothesis (наш будущий продукт)
    brand: str | None = None
    values: dict = field(default_factory=dict)        # units, reviews, price, revenue, ...
    ingredients: dict | None = None    # {ingredient: source title|label|photo}; None — состав неизвестен
    tags: set = field(default_factory=set)            # сегменты: senior, large_breed, mass_market, ...


class FactTable:
    """Таблица фактов ниши: одна строка на конкурента или нашу гипотезу."""

    def __init__(self, ingredient_aliases: dict | None = None, units_field: str = "units"):
        self._e: dict[str, Entity] = {}
        # {ingredient: [основы слов RU/EN/ES]} — для поиска «без мидии» в свободном тексте
        self.aliases = {k: list(v) for k, v in (ingredient_aliases or {}).items()}
        self.units_field = units_field

    def add(self, entity: Entity) -> Entity:
        if entity.entity_id in self._e:
            raise ValueError(f"duplicate entity_id {entity.entity_id}")
        if "." in entity.entity_id or "|" in entity.entity_id or ":" in entity.entity_id:
            raise ValueError(f"entity_id must not contain . | : — {entity.entity_id}")
        entity.tags = set(entity.tags)
        self._e[entity.entity_id] = entity
        return entity

    def add_row(self, row: dict) -> Entity:
        r = dict(row)
        return self.add(Entity(r.pop("id"), r.pop("name", r.get("brand") or ""), r.pop("kind", COMPETITOR),
                               r.pop("brand", None), r.pop("values", {}), r.pop("ingredients", None),
                               set(r.pop("tags", ()))))

    def __contains__(self, entity_id):
        return entity_id in self._e

    def get(self, entity_id) -> Entity:
        return self._e[entity_id]

    def competitors(self) -> list:
        return [e for e in self._e.values() if e.kind == COMPETITOR]

    # ---------- значения
    def value(self, ref: str) -> float:
        eid, fld = _split_ref(ref)
        v = self._e[eid].values.get(fld)
        if v is None:
            raise KeyError(f"{eid} has no value {fld}")
        return float(v)

    def to_registry(self, registry, prefix: str = "comp", source: str | None = None) -> None:
        """Значения конкурентов → MetricRegistry как {prefix}.{id}.{field} (data_type=estimated)."""
        units = {"units": "units", "price": "EUR", "revenue": "EUR"}
        for e in self.competitors():
            for fld, v in e.values.items():
                if isinstance(v, (int, float)):
                    registry.add(f"{prefix}.{e.entity_id}.{fld}", v, units.get(fld, "count"),
                                 "estimated", source=source)

    # ---------- рендеринг плейсхолдеров
    def render(self, text: str) -> str:
        return FACT_PLACEHOLDER.sub(lambda mo: self._render_one(mo.group(1), mo.group(2)), text)

    def _render_one(self, kind: str, arg: str) -> str:
        if kind == "cmp":
            a, b = arg.split("|")
            return compare_phrase(self.value(a), self.value(b))
        if kind == "rank":
            k, n = self.rank(arg)
            return f"#{k} из {n}"
        if kind == "ing":
            eid, ing = arg.split(":")
            return self.ingredient_phrase(eid, ing)
        if kind == "count":
            return str(self.count(arg))
        raise KeyError(kind)

    def rank(self, ref: str) -> tuple:
        """Место сущности среди конкурентов по полю (по убыванию)."""
        eid, fld = _split_ref(ref)
        mine = self.value(ref)
        pool = [e.values[fld] for e in self.competitors() if e.values.get(fld) is not None]
        if self._e[eid].kind != COMPETITOR:
            pool.append(mine)
        return 1 + sum(1 for v in pool if v > mine), len(pool)

    def has_ingredient(self, eid: str, ing: str):
        """True / False / None (состав неизвестен)."""
        e = self._e[eid]
        if e.ingredients is None:
            return None
        return ing in e.ingredients

    def ingredient_phrase(self, eid: str, ing: str) -> str:
        h = self.has_ingredient(eid, ing)
        if h is None:
            return NO_DATA
        if not h:
            return "нет"
        src = self._e[eid].ingredients.get(ing)
        return f"есть ({_SOURCE_RU.get(src, src)})" if src else "есть"

    def count(self, selector: str) -> int:
        """selector: 'tag', 'kind/tag' или 'kind'. Пример: 'hypothesis/mass_market'."""
        kind, _, tag = selector.partition("/")
        if not tag and kind not in (COMPETITOR, HYPOTHESIS):
            kind, tag = "", kind
        return sum(1 for e in self._e.values()
                   if (not kind or e.kind == kind) and (not tag or tag in e.tags))

    # ---------- проверка свободного текста
    def strip(self, text: str) -> str:
        return FACT_PLACEHOLDER.sub(lambda mo: " " * len(mo.group(0)), text)

    def lint(self, text: str) -> list:
        """Нарушения в тексте: неизвестные ссылки в плейсхолдерах, словесные сравнения,
        утверждения об уникальности и об отсутствии ингредиента без {{ing:…}}."""
        out = []
        for mo in FACT_PLACEHOLDER.finditer(text):
            try:
                self._render_one(mo.group(1), mo.group(2))
            except (KeyError, ValueError, ZeroDivisionError) as exc:
                out.append(Violation("unknown_fact", mo.group(0), f"{exc}"))
        bare = self.strip(text)
        for rx, kind in ((_WORD_COMPARISON, "ungrounded_comparison"), (_UNIQUENESS, "ungrounded_uniqueness")):
            for mo in rx.finditer(bare):
                out.append(Violation(kind, mo.group(0), _ctx(text, mo.start(), mo.end())))
        for ing, stems in self.aliases.items():
            alt = "|".join(re.escape(s) for s in stems)
            rx = re.compile(rf"\b{_NEGATION}\s+(?:\w+\s+){{0,2}}?(?:{alt})\w*", re.IGNORECASE)
            for mo in rx.finditer(bare):
                out.append(Violation("ungrounded_ingredient_claim", mo.group(0),
                                     _ctx(text, mo.start(), mo.end()) + f" → используйте {{{{ing:<id>:{ing}}}}}"))
        return out

    # ---------- структурированные утверждения (JSON от LLM)
    def check_assertion(self, a: dict) -> tuple:
        """a: {"type": gt|lt|has|lacks, ...} → (ok: bool|None, пояснение). None — данных нет."""
        t = a["type"]
        if t in ("gt", "lt"):
            x, y = self.value(a["left"]), self.value(a["right"])
            ok = x > y if t == "gt" else x < y
            return ok, f"{a['left']}={_fmt_number(x, 0)} vs {a['right']}={_fmt_number(y, 0)}"
        if t in ("has", "lacks"):
            h = self.has_ingredient(a["entity"], a["ingredient"])
            if h is None:
                return None, f"{a['entity']}: состав неизвестен"
            return (h if t == "has" else not h), f"{a['entity']}.{a['ingredient']}={h}"
        raise ValueError(f"unknown assertion type {t}")


@dataclass
class CardCheck:
    product_id: str
    valid_models: list
    brands: int
    violations: list


def check_product_card(card: dict, facts: FactTable, min_units: float) -> CardCheck:
    """card: {"product_id", "segment_tags": [...], "models": [entity_id, ...], "models_count"?: int}.

    Модель засчитывается, если это реальный конкурент (не наша гипотеза), с продажами
    ≥ min_units и со всеми тегами сегмента карточки."""
    pid, need = card["product_id"], set(card.get("segment_tags", ()))
    valid, violations = [], []
    for mid in card.get("models", ()):
        if mid not in facts:
            violations.append(Violation("unknown_model", mid, pid))
            continue
        e = facts.get(mid)
        if e.kind != COMPETITOR:
            violations.append(Violation("circular_evidence", mid, f"{pid}: модель — наша же гипотеза"))
            continue
        units = e.values.get(facts.units_field)
        if units is None or units < min_units:
            violations.append(Violation("model_below_threshold", mid,
                                        f"{pid}: {facts.units_field}={units} < {min_units}"))
            continue
        missing = need - e.tags
        if missing:
            violations.append(Violation("model_out_of_segment", mid,
                                        f"{pid}: у модели нет тегов {sorted(missing)}"))
            continue
        valid.append(mid)
    declared = card.get("models_count")
    if declared is not None and declared != len(valid):
        violations.append(Violation("models_count_mismatch", str(declared),
                                    f"{pid}: заявлено {declared}, подтверждено {len(valid)}"))
    brands = len({(facts.get(m).brand or m).lower() for m in valid})
    return CardCheck(pid, valid, brands, violations)


def compare_phrase(a: float, b: float) -> str:
    """Словесное сравнение a с b, посчитанное кодом."""
    if b == 0:
        raise ZeroDivisionError("compare with zero")
    r = a / b
    if 1 / 1.1 <= r <= 1.1:
        return "примерно столько же"
    if r > 1:
        return f"на {round((r - 1) * 100)} % больше" if r < 2 else f"в {_fmt_number(r, 1)} раза больше"
    if a == 0:
        raise ValueError("compare zero with non-zero")
    q = b / a
    return f"на {round((1 - r) * 100)} % меньше" if q < 2 else f"в {_fmt_number(q, 1)} раза меньше"


_SOURCE_RU = {"title": "заголовок", "bullets": "буллеты", "label": "этикетка", "photo": "фото упаковки"}


def _split_ref(ref: str) -> tuple:
    eid, _, fld = ref.strip().partition(".")
    if not fld:
        raise ValueError(f"reference must be <entity>.<field>: {ref}")
    return eid, fld
