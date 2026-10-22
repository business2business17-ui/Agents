"""Contestable Market Engine и когорты новых входов (ТЗ v1.2 §5.1, §5.2).

Закрывает проблему P5: доступный новому товару объём — это минимум из независимых
ограничений (спрос / бюджет / предложение / эмпирика когорт), а не «рынок минус TOP 10».

Все значения ScenarioValues выровнены по сценарию, а не отсортированы:
cpc.low — это CPC *для пессимистичного сценария* (т. е. обычно самый высокий).
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from .config import Config

RANGES = ("low", "base", "high")


@dataclass(frozen=True)
class ScenarioValues:
    low: float
    base: float
    high: float

    @classmethod
    def from_any(cls, v) -> "ScenarioValues":
        if isinstance(v, ScenarioValues):
            return v
        if isinstance(v, (int, float)):
            return cls(float(v), float(v), float(v))
        return cls(float(v["low"]), float(v["base"]), float(v["high"]))

    def get(self, r: str) -> float:
        return getattr(self, r)

    def as_dict(self) -> dict:
        return {"low": self.low, "base": self.base, "high": self.high}


@dataclass(frozen=True)
class KeywordCluster:
    cluster_id: str
    keywords: tuple
    search_volume_month: float
    click_share: ScenarioValues     # достижимая доля кликов кластера
    cvr: ScenarioValues             # конверсия клика в заказ

    @classmethod
    def from_dict(cls, d: dict) -> "KeywordCluster":
        return cls(d["cluster_id"], tuple(k.strip().lower() for k in d["keywords"]),
                   float(d["search_volume_month"]),
                   ScenarioValues.from_any(d["click_share"]), ScenarioValues.from_any(d["cvr"]))


# ---------------------------------------------------------------- когорты (§5.2)

@dataclass
class CohortResult:
    status: str                        # OK | LOW | NOT_MEASURABLE
    cohort_size: int
    units: ScenarioValues | None       # P25 / P50 / P75 продаж новых ASIN на месяц M
    share_reaching: dict = field(default_factory=dict)   # порог шт./мес. → доля когорты
    notes: list = field(default_factory=list)


def cohort_stats(units_at_month: list, cfg: Config, thresholds=(50, 100, 300),
                 exited_count: int = 0) -> CohortResult:
    """units_at_month — продажи каждого нового ASIN когорты на месяце M (выбывшие = 0)."""
    values = [float(u) for u in units_at_month] + [0.0] * exited_count
    n = len(values)
    if n < cfg.cohort_min_low:
        return CohortResult("NOT_MEASURABLE", n, None,
                            notes=[f"Когорта {n} < {cfg.cohort_min_low}: статистика не считается."])
    q = statistics.quantiles(values, n=4, method="inclusive")
    res = CohortResult(
        "OK" if n >= cfg.cohort_min_ok else "LOW", n, ScenarioValues(q[0], q[1], q[2]),
        share_reaching={t: sum(v >= t for v in values) / n for t in thresholds})
    if exited_count == 0:
        res.notes.append("Выбывшие ASIN не переданы: возможен survival bias.")
    return res


# ---------------------------------------------------------------- contestable (§5.1)

@dataclass
class ContestableResult:
    units: ScenarioValues
    revenue: ScenarioValues
    binding_constraint: dict           # сценарий → имя ограничения
    components: dict                   # ограничение → ScenarioValues | None
    empirical_status: str
    notes: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "units": self.units.as_dict(),
            "revenue": self.revenue.as_dict(),
            "binding_constraint": self.binding_constraint,
            "components": {k: (v.as_dict() if v else None) for k, v in self.components.items()},
            "empirical_status": self.empirical_status,
            "notes": self.notes,
        }


def check_clusters_disjoint(clusters: list) -> None:
    """Один и тот же спрос не должен учитываться дважды (§8)."""
    seen = {}
    for c in clusters:
        for kw in c.keywords:
            if kw in seen:
                raise ValueError(f"keyword '{kw}' is in clusters '{seen[kw]}' and '{c.cluster_id}'")
            seen[kw] = c.cluster_id


def contestable_market(clusters: list, ppc_budget_month: float, cpc: ScenarioValues,
                       cvr_ads: ScenarioValues, organic_multiplier: ScenarioValues,
                       price: ScenarioValues, supply_units_month: float | None,
                       cohort: CohortResult | None) -> ContestableResult:
    check_clusters_disjoint(clusters)
    notes = []

    demand = ScenarioValues(*[
        sum(c.search_volume_month * c.click_share.get(r) * c.cvr.get(r) for c in clusters)
        for r in RANGES])
    budget = ScenarioValues(*[
        (ppc_budget_month / cpc.get(r)) * cvr_ads.get(r) * (1 + organic_multiplier.get(r))
        if cpc.get(r) > 0 else 0.0 for r in RANGES])
    supply = ScenarioValues.from_any(supply_units_month) if supply_units_month is not None else None
    if supply is None:
        notes.append("Ограничение по запасу не задано (MOQ/производство/FBA capacity).")

    empirical_status = cohort.status if cohort else "NOT_MEASURABLE"
    empirical = cohort.units if cohort and cohort.units else None
    if empirical is None:
        notes.append("Эмпирика когорт недоступна (NOT MEASURABLE): ограничение не участвует, "
                     "confidence понижается.")

    components = {"demand": demand, "budget": budget, "supply": supply, "empirical": empirical}
    units, binding = {}, {}
    for r in RANGES:
        candidates = {k: v.get(r) for k, v in components.items() if v is not None}
        name = min(candidates, key=lambda k: (candidates[k], k))
        units[r], binding[r] = candidates[name], name
    if cpc.low < cpc.high:
        notes.append("Проверьте выравнивание CPC: в пессимистичном сценарии CPC обычно выше.")
    u = ScenarioValues(units["low"], units["base"], units["high"])
    rev = ScenarioValues(*[u.get(r) * price.get(r) for r in RANGES])
    return ContestableResult(u, rev, binding, components, empirical_status, notes)
