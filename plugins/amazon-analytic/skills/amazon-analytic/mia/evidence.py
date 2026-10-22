"""Правила доказательности продуктовой гипотезы (ТЗ v1.2 §5.2, §7, §13).

Заменяют единственный порог «есть конкурент с >100 продаж/мес», на котором держался
отчёт по хондропротекторам. Гипотеза = подниша (правило включения), её модели —
ASIN подниши с продажами не ниже порога.

Проверки:
1. brands  — ≥ N моделей РАЗНЫХ брендов: один бренд может быть выбросом;
2. young   — хотя бы одна модель молодая (листинг < 18 мес. или < 500 отзывов): новый бренд
             способен войти, а не только старожилы с тысячами отзывов;
3. price   — цена гипотезы в коридоре цен моделей ± 25 %, иначе это экстраполяция;
4. top1    — спрос сегмента не держится на одном ASIN (leave-one-out).

Продажи моделей берутся консервативно: оценка Helium, зажатая сверху следующей ступенью
бейджа Amazon «X+ bought», если бейдж есть.

Статусы: validated (все проверки) · weak (модели есть, но проверка не пройдена) ·
hypothesis (моделей нет) · white_space (в выгрузке нет ни одного ASIN такого продукта —
вывод «нет продукта → есть спрос» запрещён, §7).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .config import Config
from .grounding import _fmt_number
from .importers.helium10 import badge_bounds

VALIDATED, WEAK, HYPOTHESIS, WHITE_SPACE = "validated", "weak", "hypothesis", "white_space"


@dataclass
class EvidenceResult:
    status: str
    models: list = field(default_factory=list)
    brands: int = 0
    young_models: int = 0
    price_corridor: list | None = None
    price: float | None = None
    top1_share: float | None = None
    checks: list = field(default_factory=list)       # {"check", "passed", "detail"}

    @property
    def failed(self) -> list:
        return [c["check"] for c in self.checks if not c["passed"]]

    def as_dict(self) -> dict:
        return {"status": self.status, "brands": self.brands, "young_models": self.young_models,
                "price": self.price, "price_corridor": self.price_corridor, "top1_share": self.top1_share,
                "checks": self.checks, "failed": self.failed, "models": self.models}


def conservative_units(row) -> float | None:
    """Оценка Helium, не выше верхней границы бейджа Amazon (если бейдж есть)."""
    if row.units is None:
        return None
    b = badge_bounds(row.badge_floor)
    if b and b[1] is not None:
        return min(row.units, b[1] - 1)        # «50+» = 50–99: следующая ступень не включается
    return row.units


def assess(rows: list, hypothesis_price: float | None, as_of: date, cfg: Config) -> EvidenceResult:
    """rows — ASIN подниши гипотезы (после контроля качества и правила включения)."""
    if not rows:
        return EvidenceResult(WHITE_SPACE, checks=[{
            "check": "demand_seen", "passed": False,
            "detail": "В выгрузке нет ни одного ASIN такого продукта: спрос не подтверждён (§7)."}])

    models = []
    for r in rows:
        u = conservative_units(r)
        if u is None or u < cfg.model_min_units:
            continue
        age = (as_of - r.created).days / 30.44 if r.created else None
        young = (age is not None and age < cfg.evidence_young_months) or \
                (r.reviews is not None and r.reviews < cfg.evidence_young_reviews)
        models.append({"asin": r.asin, "brand": r.brand, "title": r.title[:80], "units": u,
                       "units_helium": r.units, "price": r.price, "reviews": r.reviews,
                       "age_months": round(age, 1) if age is not None else None, "young": young})
    models.sort(key=lambda m: -m["units"])

    revenue = [(r.revenue or 0) for r in rows]
    total = sum(revenue)
    top1 = max(revenue) / total if total else None

    if not models:
        return EvidenceResult(HYPOTHESIS, top1_share=top1, price=hypothesis_price, checks=[{
            "check": "models", "passed": False,
            "detail": f"Нет ни одного ASIN с продажами ≥ {cfg.model_min_units:g}/мес."}])

    brands = len({(m["brand"] or m["asin"]).strip().lower() for m in models})
    young = sum(m["young"] for m in models)
    prices = [m["price"] for m in models if m["price"]]
    corridor = [round(min(prices) * (1 - cfg.evidence_price_band), 2),
                round(max(prices) * (1 + cfg.evidence_price_band), 2)] if prices else None

    checks = [
        {"check": "brands", "passed": brands >= cfg.evidence_min_brands,
         "detail": f"{brands} бренд(ов) среди {len(models)} моделей (нужно ≥ {cfg.evidence_min_brands})"},
        {"check": "young", "passed": young >= 1,
         "detail": f"молодых моделей {young} (< {cfg.evidence_young_months} мес. или "
                   f"< {cfg.evidence_young_reviews} отзывов)"},
        {"check": "top1", "passed": top1 is not None and top1 <= cfg.evidence_top1_max_share,
         "detail": f"доля крупнейшего ASIN в выручке сегмента {top1:.0%} "
                   f"(порог {cfg.evidence_top1_max_share:.0%})" if top1 is not None else "нет выручки"},
    ]
    if hypothesis_price is not None and corridor:
        ok = corridor[0] <= hypothesis_price <= corridor[1]
        checks.append({"check": "price", "passed": ok,
                       "detail": f"цена {_fmt_number(hypothesis_price, 2)} "
                                 f"{'в коридоре' if ok else 'вне коридора'} цен моделей "
                                 f"{_fmt_number(corridor[0], 2)}–{_fmt_number(corridor[1], 2)}"})
    status = VALIDATED if all(c["passed"] for c in checks) else WEAK
    return EvidenceResult(status, models, brands, young, corridor, hypothesis_price, top1, checks)
