"""Версионированная конфигурация порогов (ТЗ v1.2, «Соглашение о порогах").

Все значения — стартовые для калибровки, а не доказанные константы.
Ставки комиссий Amazon и НДС здесь намеренно отсутствуют: они передаются
во входных данных из версионированных таблиц (§11.1).
"""
from dataclasses import dataclass, field

SCENARIOS = ("conservative", "base", "optimistic")
# Соответствие сценариев финмодели и диапазонов low/base/high рыночных оценок.
SCENARIO_TO_RANGE = {"conservative": "low", "base": "base", "optimistic": "high"}


@dataclass(frozen=True)
class Config:
    version: str = "2026.10-cfg1"

    # §11.4 — веса сценариев для E[Profit]
    scenario_weights: dict = field(default_factory=lambda: {
        "conservative": 0.25, "base": 0.50, "optimistic": 0.25})

    # §12.1 — кривые разгона (доля от steady state по месяцам продаж; последнее значение тянется дальше)
    ramp: dict = field(default_factory=lambda: {
        "conservative": [0.15, 0.30, 0.50, 0.65, 0.80, 1.00],
        "base": [0.25, 0.45, 0.70, 0.85, 1.00],
        "optimistic": [0.40, 0.70, 0.90, 1.00],
    })
    resale_ramp: list = field(default_factory=lambda: [0.70, 1.00])
    # Множитель TACoS по месяцам продаж (запуск дороже steady state)
    tacos_curve: dict = field(default_factory=lambda: {
        "conservative": [3.0, 2.5, 2.0, 1.6, 1.3, 1.0],
        "base": [2.5, 2.0, 1.5, 1.2, 1.0],
        "optimistic": [2.0, 1.5, 1.2, 1.0],
    })
    resale_tacos_curve: list = field(default_factory=lambda: [1.0])

    # §11.3 — cash-flow
    horizon_months: int = 18
    capital_buffer: float = 0.15
    inventory_salvage_rate: float = 0.30   # остаточная стоимость нераспроданного запаса для Capital at Risk
    default_max_test_loss_share_of_budget: float = 0.30

    # §11.4 — стресс-тесты
    stress_price: float = -0.15
    stress_cpc: float = 0.30
    stress_cvr: float = -0.30
    stress_unsold_share: float = 0.50
    stress_unsold_months: int = 6
    stress_delay_days: int = 45

    # §11.5 — запасы
    service_level_z: float = 1.65
    default_coverage_target_days: int = 60

    # §3.3 / §15.2 — confidence
    divergence_high: float = 0.25
    divergence_medium: float = 0.50
    coverage_high: float = 0.80
    coverage_medium: float = 0.60
    freshness_high_days: int = 30
    freshness_medium_days: int = 60
    fee_schedule_max_age_days: int = 90

    # §5.2 — когорты новых входов
    cohort_min_ok: int = 20
    cohort_min_low: int = 10

    # §9 — модель-конкурент для карточки продукта (factcheck.check_product_card, evidence)
    model_min_units: float = 100

    # §13 — правила доказательности гипотезы (evidence.py)
    evidence_min_brands: int = 2              # моделей разных брендов с продажами ≥ model_min_units
    evidence_young_months: int = 18           # «молодая» модель: листинг моложе …
    evidence_young_reviews: int = 500         # … или отзывов меньше …
    evidence_price_band: float = 0.25         # цена гипотезы в коридоре цен моделей ± доля
    evidence_top1_max_share: float = 0.50     # спрос сегмента держится на одном ASIN, если его доля больше

    # §13 — портфель (portfolio.py)
    cannibalization_overlap: float = 0.30     # доля общего спроса (ключи / ASIN), выше — каннибализация
    moq_max_cover_months: float = 6.0         # MOQ покрывает больше месяцев продаж Base → риск неликвида

    # §5.3 — Buy Box
    bb_competitive_price_band: float = 0.02
    amazon_bb_dominance: float = 0.50
    bb_below_mvp_max_share: float = 0.30

    # §14.2 — Score
    score_weights: dict = field(default_factory=lambda: {
        "demand": 0.15, "growth": 0.10, "contestable": 0.20, "economics": 0.25,
        "barriers": 0.10, "ppc": 0.10, "differentiation": 0.10})
    score_max_missing_weight: float = 0.25
    score_go: float = 80
    score_test: float = 65
    score_hold: float = 50
    # Кусочно-линейные полосы: список (x, score). Значения вне диапазона — по крайним точкам.
    bands: dict = field(default_factory=lambda: {
        "niche_revenue_month": [(0, 0), (20_000, 30), (100_000, 70), (500_000, 100)],
        "nonbranded_share": [(0.2, 0), (0.5, 60), (0.8, 100)],
        "monthly_cv": [(0.2, 100), (0.5, 60), (1.0, 0)],
        "trend_12m": [(-0.30, 0), (-0.05, 40), (0.05, 60), (0.30, 100)],
        "contestable_share": [(0, 0), (0.02, 40), (0.05, 70), (0.10, 100)],
        "nesr": [(0, 0), (0.10, 40), (0.30, 80), (0.50, 100)],
        "bb_share": [(0, 0), (0.10, 40), (0.25, 80), (0.50, 100)],
        "contribution_margin": [(0, 0), (0.10, 40), (0.20, 70), (0.30, 100)],
        "capital_roi_12m": [(0, 0), (0.5, 50), (1.0, 80), (2.0, 100)],
        "review_median_top10": [(50, 100), (500, 60), (2000, 30), (5000, 0)],
        "hhi_brand": [(1000, 100), (1800, 60), (3000, 30), (5000, 0)],
        "amazon_retail_share": [(0, 100), (0.2, 60), (0.5, 20), (0.8, 0)],
        "cost_per_order_to_contribution": [(0.3, 100), (1.0, 0)],
        "bb_price_cv": [(0.02, 100), (0.10, 50), (0.25, 0)],
    })


DEFAULT_CONFIG = Config()


def interpolate(points, x):
    """Кусочно-линейная интерполяция по полосе [(x, y), ...] (x возрастает)."""
    if x <= points[0][0]:
        return float(points[0][1])
    if x >= points[-1][0]:
        return float(points[-1][1])
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    raise ValueError("unreachable")
