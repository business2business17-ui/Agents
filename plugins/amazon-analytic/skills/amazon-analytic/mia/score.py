"""Niche Opportunity Score 0–100 с явной нормализацией (ТЗ v1.2 §14.2).

Закрывает P3: каждый компонент вычислим по абсолютным полосам конфигурации,
поэтому Score ниши не зависит от набора сравниваемых ниш. Качество данных в Score
не входит. Если не хватает > score_max_missing_weight весов, Score не считается.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config, interpolate


@dataclass
class ScoreResult:
    score: float | None
    components: dict = field(default_factory=dict)    # компонент → балл 0–100 или None
    missing: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"score": self.score, "components": self.components,
                "missing": self.missing, "notes": self.notes}


def _avg(cfg, pairs):
    vals = [interpolate(cfg.bands[band], x) for band, x in pairs if x is not None]
    return sum(vals) / len(vals) if vals else None


def niche_score(cfg: Config, business_model: str, m: dict) -> ScoreResult:
    """m — плоский словарь метрик (ключи см. ниже); отсутствующие = None."""
    notes = []
    comp = {}
    comp["demand"] = _avg(cfg, [("niche_revenue_month", m.get("niche_revenue_month")),
                                ("nonbranded_share", m.get("nonbranded_share")),
                                ("monthly_cv", m.get("monthly_cv"))])
    comp["growth"] = _avg(cfg, [("trend_12m", m.get("trend_12m"))])

    if business_model == "resale":
        comp["contestable"] = _avg(cfg, [("bb_share", m.get("bb_share_base"))])
        comp["differentiation"] = _avg(cfg, [("bb_price_cv", m.get("bb_price_cv"))])
        notes.append("Resale: доступная доля = доля Buy Box, дифференциация = стабильность цены Buy Box.")
    else:
        cshare = None
        if m.get("contestable_revenue_base") is not None and m.get("niche_revenue_month"):
            cshare = m["contestable_revenue_base"] / m["niche_revenue_month"]
        comp["contestable"] = _avg(cfg, [("contestable_share", cshare), ("nesr", m.get("nesr"))])
        if m.get("nesr") is None and cshare is not None:
            notes.append("NESR = NOT MEASURABLE: компонент «доступная доля» только по contestable.")
        pp = m.get("addressable_pain_points")
        comp["differentiation"] = None if pp is None else {0: 0.0, 1: 50.0, 2: 75.0}.get(pp, 100.0)

    cm = m.get("contribution_margin")
    if cm is not None and cm <= 0:
        comp["economics"] = 0.0
    else:
        comp["economics"] = _avg(cfg, [("contribution_margin", cm),
                                       ("capital_roi_12m", m.get("capital_roi_12m"))])

    comp["barriers"] = _avg(cfg, [("review_median_top10", m.get("review_median_top10")),
                                  ("hhi_brand", m.get("hhi_brand")),
                                  ("amazon_retail_share", m.get("amazon_retail_share"))])

    ratio = None
    if all(m.get(k) is not None for k in ("cpc", "cvr_ads", "pre_ad_contribution")):
        if m["pre_ad_contribution"] <= 0 or m["cvr_ads"] <= 0:
            ratio = float("inf")
        else:
            ratio = (m["cpc"] / m["cvr_ads"]) / m["pre_ad_contribution"]
    if business_model == "resale" and ratio is None:
        comp["ppc"] = 100.0        # для resale реклама опциональна; без данных — не штрафуем
        notes.append("Resale без PPC-данных: компонент PPC = 100 (реклама не требуется).")
    else:
        comp["ppc"] = None if ratio is None else interpolate(
            cfg.bands["cost_per_order_to_contribution"], min(ratio, 1e9))

    w = cfg.score_weights
    missing = [k for k, v in comp.items() if v is None]
    missing_w = sum(w[k] for k in missing)
    if missing_w > cfg.score_max_missing_weight:
        notes.append(f"Отсутствуют компоненты с весом {missing_w:.0%} > "
                     f"{cfg.score_max_missing_weight:.0%}: Score не рассчитан.")
        return ScoreResult(None, comp, missing, notes)
    present_w = 1 - missing_w
    score = sum(w[k] * v for k, v in comp.items() if v is not None) / present_w
    if missing:
        notes.append(f"Score частичный: нет {missing}, веса перераспределены.")
    return ScoreResult(round(score, 1), comp, missing, notes)
