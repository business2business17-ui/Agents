"""Портфель гипотез: минимальный работающий набор SKU (ТЗ v1.2 §13, §14.1).

Не «запускаем всё, что прошло порог» (14 SKU в отчёте по хондропротекторам), а:
1. в волну 1 попадают только гипотезы с решением GO/TEST и доказательностью validated;
2. GO/TEST со слабой доказательностью — волна 2, после проверки волны 1;
3. HOLD с устранимым препятствием — список «после устранения» с тем, что устранить;
4. гипотезы, делящие один спрос (общие ключи / общие конкуренты), в одну волну не идут;
5. отбор жадный по эффективности капитала (E[Profit 12m] / Required Capital) в пределах бюджета
   и FBA capacity; останавливается, как только достигнута цель по прибыли, а без цели —
   на одном SKU (минимальный набор), остальные становятся расширением по KPI волны 1.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config
from .grounding import _fmt_number
from .evidence import VALIDATED

LAUNCHABLE = ("GO", "TEST")


@dataclass
class Candidate:
    id: str
    name: str
    decision: str
    rule: str | None
    conditional_after_fix: str | None
    evidence: str
    evidence_failed: list
    expected_profit_12m: float | None
    required_capital: float | None
    capital_at_risk: float | None
    initial_units: float | None
    units_month_base: float | None
    moq: float | None
    keywords: dict = field(default_factory=dict)       # фраза → search volume
    asins: set = field(default_factory=set)
    reasons: list = field(default_factory=list)

    @property
    def capital_efficiency(self) -> float:
        if not self.required_capital or self.expected_profit_12m is None:
            return float("-inf")
        return self.expected_profit_12m / self.required_capital

    @property
    def conditional_launchable(self) -> bool:
        return bool(self.conditional_after_fix) and self.conditional_after_fix.split(" ")[0] in LAUNCHABLE


def overlap(a: Candidate, b: Candidate) -> dict:
    """Доля общего спроса: по search volume общих ключей и по общим ASIN-конкурентам."""
    kw = 0.0
    shared = set(a.keywords) & set(b.keywords)
    if shared:
        base = min(sum(a.keywords.values()), sum(b.keywords.values())) or 1
        kw = sum(a.keywords[k] for k in shared) / base
    asin = len(a.asins & b.asins) / min(len(a.asins), len(b.asins)) if a.asins and b.asins else 0.0
    return {"keywords": kw, "asins": asin, "max": max(kw, asin)}


def _select(cands: list, budget: float | None, fba_capacity: float | None, target_profit: float | None,
            max_skus: int | None, pairs: dict, cfg: Config) -> tuple:
    chosen, deferred = [], []
    capital = units = profit = 0.0
    limit = max_skus if max_skus else (None if target_profit else 1)
    for c in sorted(cands, key=lambda c: -c.capital_efficiency):
        reason = None
        if target_profit is not None and profit >= target_profit:
            reason = "цель по прибыли уже достигнута — расширение по KPI волны 1"
        elif limit is not None and len(chosen) >= limit:
            reason = ("минимальный набор: цели по прибыли нет, запускаем один SKU — расширение по KPI волны 1"
                      if not max_skus else f"лимит SKU ({max_skus})")
        else:
            clash = [o.id for o in chosen if pairs.get(frozenset((c.id, o.id)), {}).get("max", 0)
                     > cfg.cannibalization_overlap]
            if clash:
                reason = f"каннибализация с {', '.join(clash)} (общий спрос > {cfg.cannibalization_overlap:.0%})"
            elif budget is not None and capital + (c.required_capital or 0) > budget:
                reason = f"не помещается в бюджет ({capital + (c.required_capital or 0):.0f} > {budget:.0f})"
            elif fba_capacity is not None and units + (c.initial_units or 0) > fba_capacity:
                reason = f"не помещается в FBA capacity ({units + (c.initial_units or 0):.0f} > {fba_capacity:.0f})"
        if reason:
            deferred.append({"id": c.id, "reason": reason})
            continue
        chosen.append(c)
        capital += c.required_capital or 0
        units += c.initial_units or 0
        profit += c.expected_profit_12m or 0
    return chosen, deferred, {"required_capital": capital, "initial_units": units, "expected_profit_12m": profit}


def build_portfolio(cands: list, cfg: Config, budget: float | None = None, fba_capacity: float | None = None,
                    target_profit_12m: float | None = None, max_skus: int | None = None) -> dict:
    pairs = {}
    for i, a in enumerate(cands):
        for b in cands[i + 1:]:
            pairs[frozenset((a.id, b.id))] = overlap(a, b)
    cannibal = [{"a": sorted(k)[0], "b": sorted(k)[1], **{x: round(y, 2) for x, y in v.items()}}
                for k, v in pairs.items() if v["max"] > cfg.cannibalization_overlap]

    risks = {}
    for c in cands:
        r = []
        if c.moq and c.units_month_base:
            cover = c.moq / c.units_month_base
            if cover > cfg.moq_max_cover_months:
                r.append(f"MOQ {_fmt_number(c.moq, 0)} шт. = {_fmt_number(cover, 1)} мес. продаж Base "
                         f"(> {cfg.moq_max_cover_months:g}): "
                         "риск неликвида")
        elif c.moq and c.units_month_base == 0:
            r.append("Продаж в Base нет: MOQ не распродаётся")
        if r:
            risks[c.id] = r

    now = [c for c in cands if c.decision in LAUNCHABLE and c.evidence == VALIDATED]
    weak = [c for c in cands if c.decision in LAUNCHABLE and c.evidence != VALIDATED]
    cond = [c for c in cands if c.decision == "HOLD" and c.conditional_launchable]
    rejected = []
    for c in cands:
        if c in now or c in weak or c in cond:
            continue
        why = {"NO-GO": f"NO-GO ({c.rule})", "INSUFFICIENT DATA": "не хватает данных",
               "HOLD": f"HOLD ({c.rule}); после устранения — {c.conditional_after_fix or 'не GO/TEST'}"}
        rejected.append({"id": c.id, "reason": why.get(c.decision, c.decision), "evidence": c.evidence})

    chosen, deferred, totals = _select(now, budget, fba_capacity, target_profit_12m, max_skus, pairs, cfg)
    wave2 = deferred + [{"id": c.id, "reason": f"доказательность {c.evidence}: не пройдено {c.evidence_failed}"}
                        for c in weak]

    after_fix_pool = now + [c for c in cond if c.evidence == VALIDATED]
    af_chosen, af_deferred, af_totals = _select(after_fix_pool, budget, fba_capacity, target_profit_12m,
                                                max_skus, pairs, cfg)
    return {
        "wave_1": [c.id for c in chosen],
        "wave_1_totals": totals,
        "target_profit_12m": target_profit_12m,
        "target_met": None if target_profit_12m is None else totals["expected_profit_12m"] >= target_profit_12m,
        "wave_2": wave2,
        "after_fix": {
            "candidates": [{"id": c.id, "evidence": c.evidence, "fix": c.reasons,
                            "decision_after_fix": c.conditional_after_fix} for c in cond],
            "plan": [c.id for c in af_chosen], "plan_totals": af_totals, "deferred": af_deferred,
        },
        "rejected": rejected,
        "cannibalization": cannibal,
        "risks": risks,
        "budget": budget, "fba_capacity_units": fba_capacity,
    }
