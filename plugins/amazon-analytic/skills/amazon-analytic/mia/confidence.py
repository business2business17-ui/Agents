"""Confidence по принципу «слабого звена» (ТЗ v1.2 §15.2).

Закрывает часть P3: качество данных влияет на уверенность, а не на Score.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config

LEVELS = ("LOW", "MEDIUM", "HIGH")


def level_min(*levels: str) -> str:
    return min(levels, key=LEVELS.index)


@dataclass
class ConfidenceResult:
    level: str
    dimensions: dict = field(default_factory=dict)   # измерение → (уровень, пояснение)

    def weakest(self) -> list:
        return [k for k, (lvl, _) in self.dimensions.items() if lvl == self.level]

    def as_dict(self) -> dict:
        return {"level": self.level,
                "dimensions": {k: {"level": l, "why": w} for k, (l, w) in self.dimensions.items()}}


def assess_confidence(cfg: Config, coverage: float, source_divergence: float | None,
                      calibrated: bool, data_age_days: int, cogs_status: str,
                      seasonality: str, peak_period: bool,
                      empirical_status: str | None = None) -> ConfidenceResult:
    """
    source_divergence: None — единственный источник продаж.
    seasonality: history | search_trends | none.
    empirical_status: статус когорт (OK | LOW | NOT_MEASURABLE) — только Private Label.
    """
    d = {}
    if coverage >= cfg.coverage_high:
        d["coverage"] = ("HIGH", f"покрытие {coverage:.0%}")
    elif coverage >= cfg.coverage_medium:
        d["coverage"] = ("MEDIUM", f"покрытие {coverage:.0%}")
    else:
        d["coverage"] = ("LOW", f"покрытие {coverage:.0%} < {cfg.coverage_medium:.0%}")

    if calibrated or (source_divergence is not None and source_divergence <= cfg.divergence_high):
        d["sources"] = ("HIGH", "калибровка по своим продажам" if calibrated
                        else f"расхождение источников {source_divergence:.0%}")
    elif source_divergence is None:
        d["sources"] = ("MEDIUM", "единственный источник без калибровки")
    elif source_divergence <= cfg.divergence_medium:
        d["sources"] = ("MEDIUM", f"расхождение источников {source_divergence:.0%}")
    else:
        d["sources"] = ("LOW", f"расхождение источников {source_divergence:.0%} > {cfg.divergence_medium:.0%}")

    if data_age_days <= cfg.freshness_high_days:
        d["freshness"] = ("HIGH", f"данным {data_age_days} дн.")
    elif data_age_days <= cfg.freshness_medium_days:
        d["freshness"] = ("MEDIUM", f"данным {data_age_days} дн.")
    else:
        d["freshness"] = ("LOW", f"данным {data_age_days} дн.")

    d["cogs"] = {"supplier_quote": ("HIGH", "оффер поставщика"),
                 "user_estimate": ("MEDIUM", "оценка пользователя"),
                 "assumed": ("LOW", "ASSUMED_COGS")}[cogs_status]

    if seasonality == "history":
        d["seasonality"] = ("HIGH", "сезонный индекс по истории")
    elif seasonality == "search_trends":
        d["seasonality"] = ("MEDIUM", "сезонный индекс по трендам поиска")
    elif peak_period:
        d["seasonality"] = ("LOW", "пиковый срез без сезонного индекса")
    else:
        d["seasonality"] = ("MEDIUM", "сезонный индекс отсутствует")

    if empirical_status is not None:
        d["entrant_history"] = {"OK": ("HIGH", "когорта новых входов достаточна"),
                                "LOW": ("MEDIUM", "малая когорта новых входов"),
                                "NOT_MEASURABLE": ("MEDIUM", "история новых входов не измерима")
                                }[empirical_status]

    return ConfidenceResult(level_min(*(lvl for lvl, _ in d.values())), d)
