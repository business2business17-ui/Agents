"""Decision Engine (ТЗ v1.2 §15.3).

Закрывает P1/P2: решение выдаётся упорядоченными правилами R0–R5 с трассировкой.
LLM это решение не меняет — только объясняет по decision_trace.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config

ORDER = ["NO-GO", "HOLD", "TEST", "GO"]   # по возрастанию «разрешённости»


def cap(status: str, ceiling: str) -> str:
    """Понизить статус до ceiling, если он выше (INSUFFICIENT DATA не трогаем)."""
    if status not in ORDER:
        return status
    return ORDER[min(ORDER.index(status), ORDER.index(ceiling))]


@dataclass
class DecisionInputs:
    business_model: str
    missing_critical: list
    compliance_overall: str              # PASS | REVIEW REQUIRED | BLOCKED
    compliance_hard_block: bool
    compliance_open_items: list
    best_base_post_ad_contribution: float | None
    score: float | None
    confidence: str
    cogs_assumed: bool
    conservative_loss: float
    capital_at_risk: float
    max_test_loss: float
    required_capital_base: float
    budget: float | None
    fba_capacity_ok: bool
    seasonal_anomaly: bool = False
    resale_hard_stops: list = field(default_factory=list)
    resale_reviews: list = field(default_factory=list)
    resale_caps: list = field(default_factory=list)


@dataclass
class Decision:
    status: str
    rule: str
    confidence: str
    trace: list = field(default_factory=list)
    reasons: list = field(default_factory=list)
    conditional_after_fix: str | None = None
    caps_applied: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _score_rules(i: DecisionInputs, cfg: Config, trace: list) -> tuple:
    s = i.score
    conf_ok = i.confidence in ("MEDIUM", "HIGH")
    loss_ok = i.conservative_loss <= i.max_test_loss
    car_ok = i.capital_at_risk <= i.max_test_loss
    vals = {"score": s, "confidence": i.confidence, "cogs_assumed": i.cogs_assumed,
            "conservative_loss": round(i.conservative_loss, 2),
            "capital_at_risk": round(i.capital_at_risk, 2), "max_test_loss": round(i.max_test_loss, 2)}
    if s >= cfg.score_go and conf_ok and not i.cogs_assumed and loss_ok:
        trace.append({"rule": "R5a", "fired": True, "values": vals})
        return "GO", "R5a"
    trace.append({"rule": "R5a", "fired": False, "values": vals})
    if s >= cfg.score_test:
        if car_ok:
            trace.append({"rule": "R5b", "fired": True, "values": vals})
            return "TEST", "R5b"
        trace.append({"rule": "R5c", "fired": True, "values": vals,
                      "why": "Capital at Risk больше допустимого убытка теста"})
        return "HOLD", "R5c"
    if s >= cfg.score_hold:
        trace.append({"rule": "R5c", "fired": True, "values": vals})
        return "HOLD", "R5c"
    trace.append({"rule": "R5d", "fired": True, "values": vals})
    return "NO-GO", "R5d"


def _apply_caps(status: str, i: DecisionInputs, caps: list) -> str:
    if i.confidence == "LOW" and ORDER.index(status) > ORDER.index("TEST"):
        caps.append("Confidence LOW → не выше TEST")
        status = cap(status, "TEST")
    if i.cogs_assumed and ORDER.index(status) > ORDER.index("TEST"):
        caps.append("ASSUMED_COGS → не выше TEST")
        status = cap(status, "TEST")
    if i.seasonal_anomaly and status == "GO":
        caps.append("Срез на сезонной аномалии → GO понижен до TEST")
        status = "TEST"
    if i.resale_caps and ORDER.index(status) > ORDER.index("HOLD"):
        caps.append("Resale-риски → не выше HOLD: " + "; ".join(i.resale_caps))
        status = cap(status, "HOLD")
    return status


def decide(i: DecisionInputs, cfg: Config) -> Decision:
    trace = []

    # R0 — критичные поля
    if i.missing_critical or i.score is None:
        missing = list(i.missing_critical) + ([] if i.score is not None else ["score (недостаточно компонентов)"])
        trace.append({"rule": "R0", "fired": True, "values": {"missing": missing}})
        return Decision("INSUFFICIENT DATA", "R0", i.confidence, trace,
                        reasons=[f"Не хватает: {', '.join(missing)}"])
    trace.append({"rule": "R0", "fired": False})

    # R1 — неустранимый compliance-блок
    if i.compliance_hard_block:
        trace.append({"rule": "R1", "fired": True, "values": {"open_items": i.compliance_open_items}})
        return Decision("NO-GO", "R1", i.confidence, trace,
                        reasons=["Compliance BLOCKED по неустранимой причине"] + i.compliance_open_items)
    trace.append({"rule": "R1", "fired": False})

    # R2 — экономика / доминирование Amazon (Resale)
    contrib = i.best_base_post_ad_contribution
    if contrib is not None and contrib <= 0:
        trace.append({"rule": "R2", "fired": True,
                      "values": {"best_base_post_ad_contribution": round(contrib, 4)}})
        return Decision("NO-GO", "R2", i.confidence, trace,
                        reasons=["Post-Ad Contribution ≤ 0 в Base при любой цене допустимого диапазона"])
    if i.resale_hard_stops:
        trace.append({"rule": "R2", "fired": True, "values": {"resale_hard_stops": i.resale_hard_stops}})
        return Decision("NO-GO", "R2", i.confidence, trace, reasons=list(i.resale_hard_stops))
    trace.append({"rule": "R2", "fired": False,
                  "values": {"best_base_post_ad_contribution": None if contrib is None else round(contrib, 4)}})

    # Условный итог «после устранения» нужен для R3/R4.
    shadow_trace = []
    shadow, shadow_rule = _score_rules(i, cfg, shadow_trace)
    shadow = _apply_caps(shadow, i, [])

    # R3 — устранимые compliance-вопросы
    if i.compliance_overall in ("REVIEW REQUIRED", "BLOCKED") or i.resale_reviews:
        items = i.compliance_open_items + i.resale_reviews
        trace.append({"rule": "R3", "fired": True, "values": {"open_items": items}})
        return Decision("HOLD", "R3", i.confidence, trace,
                        reasons=["Требуется устранить compliance-вопросы"] + items,
                        conditional_after_fix=f"{shadow} ({shadow_rule})")
    trace.append({"rule": "R3", "fired": False})

    # R4 — ресурсы: капитал и FBA capacity
    over_budget = i.budget is not None and i.required_capital_base > i.budget
    if over_budget or not i.fba_capacity_ok:
        reasons = []
        if over_budget:
            reasons.append(f"Required Capital (Base) {i.required_capital_base:.0f} > бюджета {i.budget:.0f}")
        if not i.fba_capacity_ok:
            reasons.append("FBA capacity недостаточна для минимального работающего набора")
        trace.append({"rule": "R4", "fired": True, "values": {
            "required_capital_base": round(i.required_capital_base, 2), "budget": i.budget,
            "fba_capacity_ok": i.fba_capacity_ok}})
        return Decision("HOLD", "R4", i.confidence, trace, reasons=reasons,
                        conditional_after_fix=f"{shadow} ({shadow_rule})")
    trace.append({"rule": "R4", "fired": False})

    # R5 — Score + Confidence + риск
    status, rule = _score_rules(i, cfg, trace)
    caps = []
    status = _apply_caps(status, i, caps)
    if caps:
        trace.append({"rule": "caps", "applied": caps})
    return Decision(status, rule, i.confidence, trace, caps_applied=caps,
                    reasons=[f"Score {i.score}, confidence {i.confidence}"])
