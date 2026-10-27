"""Сквозной детерминированный анализ ниши → Decision Package (ТЗ v1.2 §15, §22.3).

Это инструмент `run_decision_engine` для LLM-оркестратора: на вход — нормализованные
данные (после импорта и определения ниши), на выход — решение, трассировка, метрики
с metric_id и шаблон нарратива, прошедший валидатор числового заземления.
"""
from __future__ import annotations

import json
from datetime import date

from . import __version__ as CALC_VERSION
from .buybox import Offer, buybox_analysis
from .cashflow import LaunchParams, analyze_scenarios, build_scenarios, sales_start_month
from .compliance import run_compliance
from .confidence import assess_confidence
from .config import Config, DEFAULT_CONFIG, SCENARIOS, SCENARIO_TO_RANGE
from .contestable import KeywordCluster, ScenarioValues, cohort_stats, contestable_market
from .decision import DecisionInputs, decide
from .economics import (FeeSchedule, TaxContext, UnitCosts, best_contribution_in_range,
                        break_even_units, min_viable_price, unit_economics)
from .grounding import MetricRegistry, validate
from .score import niche_score

SCHEMA_VERSION = "1.2"

# Где взять недостающее поле (§20.2: не выдумывать, а сказать, какой экспорт нужен).
HOW_TO_GET = {
    "niche_definition_id": "Утвердить определение ниши (define_niche, §3.1).",
    "market.niche_revenue_month": "Экспорт Helium 10 Xray / SmartScout по ASIN ниши.",
    "market.price_range": "Текущие цены конкурентов из Xray/Keepa.",
    "fees": "Актуальная fee schedule marketplace (size tier по габаритам и весу).",
    "tax": "Ставка НДС marketplace из таблицы vat_rates.",
    "costs.cogs": "Оффер поставщика или пользовательский диапазон COGS.",
    "ppc.cpc": "Suggested bid из Amazon Ads / Helium 10 Magnet или собственные отчёты Amazon Ads "
               "(в экспорте Cerebro CPC нет).",
    "keywords.clusters": "Кластеры небрендовых ключей из Cerebro + доля клика и CVR нового бренда "
                         "(keyword_clusters, keyword_assumptions в niche.build_input).",
    "buybox.offers": "Список офферов ASIN (Keepa / страница офферов).",
    "buybox.asin_units": "Оценка продаж целевого ASIN (Xray / SmartScout).",
    "budget_or_max_test_loss": "Бюджет запуска или допустимый убыток теста от пользователя.",
    "scenarios.prices": "Цены сценариев (из ценового анализа §10).",
    "launch": "Lead time, предоплата, MOQ от поставщика.",
}


def _get(d, path):
    cur = d
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur or cur[p] is None:
            return None
        cur = cur[p]
    return cur


def critical_missing(inp: dict) -> list:
    bm = inp.get("business_model")
    req = ["niche_definition_id", "market.price_range", "fees", "tax", "costs.cogs",
           "scenarios.prices", "launch"]
    if bm == "resale":
        req += ["buybox.offers", "buybox.asin_units"]
    else:
        req += ["market.niche_revenue_month", "ppc.cpc", "keywords.clusters"]
    missing = [p for p in req if _get(inp, p) in (None, [], {})]
    if inp.get("budget") is None and inp.get("max_test_loss") is None:
        missing.append("budget_or_max_test_loss")
    return missing


def _sv(v):
    return ScenarioValues.from_any(v)


def _by_scenario(v) -> dict:
    """{conservative,base,optimistic} или скаляр → словарь по сценариям."""
    if isinstance(v, dict):
        return {s: float(v[s]) for s in SCENARIOS}
    return {s: float(v) for s in SCENARIOS}


def analyze(inp: dict, cfg: Config = DEFAULT_CONFIG) -> dict:
    if inp.get("business_model") not in ("private_label", "resale"):
        raise ValueError("business_model must be private_label or resale")
    as_of = date.fromisoformat(inp["data_as_of"])
    reg = MetricRegistry()
    warnings = list(inp.get("_import", {}).get("warnings", []))
    pkg = {
        "schema_version": SCHEMA_VERSION,
        "marketplace": inp["marketplace"],
        "business_model": inp["business_model"],
        "niche_definition_id": inp.get("niche_definition_id"),
        "data_as_of": inp["data_as_of"],
        "versions": {"calculation_version": CALC_VERSION, "config_version": cfg.version,
                     "fee_schedule_version": _get(inp, "fees.schedule_version"),
                     "prompt_version": None, "model_id": None},
        "approval": {"status": "pending", "approved_by": None, "approved_at": None,
                     "overrides": [], "comment": None},
    }
    if inp.get("_import"):
        pkg["import"] = inp["_import"]          # источники, определение ниши, качество данных (§18)

    missing = critical_missing(inp)
    if missing:
        pkg["decision"] = {"status": "INSUFFICIENT DATA", "confidence": None, "score": None,
                           "rule_fired": "R0",
                           "decision_trace": [{"rule": "R0", "fired": True, "values": {"missing": missing}}],
                           "reasons": [f"Не хватает: {', '.join(missing)}"],
                           "how_to_get": {m: HOW_TO_GET.get(m, "") for m in missing}}
        pkg["metrics"] = []
        pkg["warnings"] = warnings
        return pkg

    bm, mp, cur = inp["business_model"], inp["marketplace"], inp.get("currency", "EUR")
    tax = TaxContext.from_dict(mp, inp["tax"])
    fees = FeeSchedule.from_dict(inp["fees"])
    costs = UnitCosts.from_dict(inp["costs"])
    launch = LaunchParams.from_dict(inp["launch"])
    market = inp.get("market", {})
    prices = _by_scenario(inp["scenarios"]["prices"])
    tacos = _by_scenario(inp["scenarios"].get("tacos_net", 0.10))
    price_sv = ScenarioValues(*(prices[s] for s in SCENARIOS))
    tax_basis = "gross_incl_vat" if tax.price_includes_vat else "gross_excl_sales_tax"

    age = fees.age_days(as_of)
    if age is None or age > cfg.fee_schedule_max_age_days:
        warnings.append(f"Fee schedule не сверялась {age if age is not None else '?'} дн. "
                        f"(порог {cfg.fee_schedule_max_age_days}).")

    # ---------- объём продаж: Contestable (PL) или Buy Box (Resale)
    contest, bb, cohort = None, None, None
    if bm == "private_label":
        clusters = [KeywordCluster.from_dict(c) for c in inp.get("keywords", {}).get("clusters", [])]
        if inp.get("cohort"):
            cohort = cohort_stats(inp["cohort"]["units_at_month"], cfg,
                                  exited_count=inp["cohort"].get("exited_count", 0))
        ppc = inp["ppc"]
        contest = contestable_market(
            clusters, float(ppc["budget_month"]), _sv(ppc["cpc"]), _sv(ppc["cvr_ads"]),
            _sv(ppc.get("organic_multiplier", 0.0)), price_sv,
            inp.get("supply_units_month"), cohort)
        units = {s: contest.units.get(SCENARIO_TO_RANGE[s]) for s in SCENARIOS}
    else:
        b = inp["buybox"]
        bb = buybox_analysis(
            b["asin"], [Offer.from_dict(o) for o in b["offers"]], float(b["buy_box_price"]),
            _sv(b["asin_units"]), cfg, our_seller_id=b.get("our_seller_id"),
            new_sellers_90d=int(b.get("new_sellers_90d", 0)), amazon_bb_share=b.get("amazon_bb_share"),
            bb_share_high_override=b.get("bb_share_high_override"),
            has_resale_authorization=b.get("has_resale_authorization"),
            brand_ip_complaints=bool(b.get("brand_ip_complaints", False)),
            bb_price_below_mvp_share=b.get("bb_price_below_mvp_share"))
        units = {s: bb.units.get(SCENARIO_TO_RANGE[s]) for s in SCENARIOS}

    # ---------- экономика и сценарии
    scen = build_scenarios(units, prices, tacos, bm, cfg)
    sa = analyze_scenarios(scen, launch, tax, fees, costs, cfg)
    ue_base = unit_economics(prices["base"], tax, fees, costs, tacos_net=tacos["base"])
    lo, hi = market["price_range"]
    best = best_contribution_in_range((lo, hi), tax, fees, costs, tacos["base"])
    mvp_price = min_viable_price(tax, fees, costs, tacos["base"], search_max=hi * 3)
    be_units = break_even_units(launch.fixed_launch_costs, ue_base.post_ad_contribution)

    # ---------- confidence, compliance, score
    peak = bool(market.get("peak_period", False))
    seasonality = market.get("seasonality_source", "none")
    conf = assess_confidence(
        cfg, coverage=float(market.get("coverage", 0.0)),
        source_divergence=market.get("source_divergence"),
        calibrated=bool(market.get("calibrated", False)),
        data_age_days=(as_of - date.fromisoformat(market.get("observed_at", inp["data_as_of"]))).days,
        cogs_status=costs.cogs_status, seasonality=seasonality, peak_period=peak,
        empirical_status=contest.empirical_status if contest else None)

    comp_in = inp.get("compliance", {})
    compliance = run_compliance(mp, inp.get("category", "other"), bm,
                                comp_in.get("flags"), comp_in.get("statuses"), inp.get("claims"))

    base_res = sa.results["base"]
    score_metrics = {
        "niche_revenue_month": _get(inp, "market.niche_revenue_month.base")
        if isinstance(market.get("niche_revenue_month"), dict) else market.get("niche_revenue_month"),
        "nonbranded_share": market.get("nonbranded_share"),
        "monthly_cv": market.get("monthly_cv"),
        "trend_12m": market.get("trend_12m"),
        "contestable_revenue_base": contest.revenue.base if contest else None,
        "nesr": (cohort.share_reaching.get(100) if cohort and cohort.status != "NOT_MEASURABLE" else None),
        "bb_share_base": bb.bb_share.base if bb else None,
        "bb_price_cv": _get(inp, "buybox.bb_price_cv"),
        "contribution_margin": ue_base.contribution_margin,
        "capital_roi_12m": base_res.capital_roi_12m,
        "review_median_top10": market.get("review_median_top10"),
        "hhi_brand": market.get("hhi_brand"),
        "amazon_retail_share": market.get("amazon_retail_share"),
        "cpc": _sv(inp["ppc"]["cpc"]).base if inp.get("ppc") else None,
        "cvr_ads": _sv(inp["ppc"]["cvr_ads"]).base if inp.get("ppc") else None,
        "pre_ad_contribution": ue_base.pre_ad_contribution,
        "addressable_pain_points": inp.get("addressable_pain_points"),
    }
    sc = niche_score(cfg, bm, score_metrics)

    budget = inp.get("budget")
    max_loss = inp.get("max_test_loss")
    if max_loss is None:
        max_loss = budget * cfg.default_max_test_loss_share_of_budget
        warnings.append(f"Допустимый убыток теста не задан: принят {cfg.default_max_test_loss_share_of_budget:.0%} "
                        f"бюджета (assumed).")

    d = decide(DecisionInputs(
        business_model=bm, missing_critical=[], compliance_overall=compliance.overall,
        compliance_hard_block=compliance.hard_block,
        compliance_open_items=[f"{i.check_id}: {i.status}" for i in compliance.open_items()],
        best_base_post_ad_contribution=best.post_ad_contribution if best else None,
        score=sc.score, confidence=conf.level, cogs_assumed=costs.cogs_assumed,
        conservative_loss=sa.results["conservative"].loss_at_horizon,
        capital_at_risk=sa.capital_at_risk, max_test_loss=float(max_loss),
        required_capital_base=base_res.required_capital, budget=budget,
        fba_capacity_ok=sa.capacity_ok,
        seasonal_anomaly=peak and seasonality == "none",
        resale_hard_stops=bb.hard_stops if bb else [], resale_reviews=bb.reviews if bb else [],
        resale_caps=bb.caps if bb else []), cfg)

    # ---------- реестр метрик (единственный источник чисел для текста)
    R = reg.add
    R("decision.score", sc.score, "score", "derived", decimals=1)
    R("market.contestable_units", contest.units.as_dict() if contest else None, "units", "estimated")
    R("market.contestable_revenue", contest.revenue.as_dict() if contest else None, cur, "estimated", decimals=0)
    R("market.bb_share", bb.bb_share.as_dict() if bb else None, "pct", "estimated")
    R("market.target_units_base", units["base"], "units", "estimated")
    R("price.recommended", prices["base"], cur, "assumed")
    R("price.min_viable", mvp_price, cur, "derived")
    R("ue.net_revenue", ue_base.net_revenue, cur, "derived")
    R("ue.pre_ad_contribution", ue_base.pre_ad_contribution, cur, "derived")
    R("ue.post_ad_contribution", ue_base.post_ad_contribution, cur, "derived")
    R("ue.contribution_margin", ue_base.contribution_margin, "pct", "derived")
    R("ue.be_acos_net", ue_base.be_acos_net, "pct", "derived")
    R("ue.be_acos_console", ue_base.be_acos_console, "pct", "derived")
    R("ue.break_even_units", be_units, "units", "derived")
    R("inv.initial_units", sa.initial_units, "units", "derived")
    R("inv.reorder_point", sa.reorder_point_units, "units", "derived")
    R("cf.required_capital", base_res.required_capital, cur, "derived", decimals=0)
    R("cf.capital_at_risk", sa.capital_at_risk, cur, "derived", decimals=0)
    R("cf.payback_month", base_res.payback_month, "month", "derived")
    R("cf.expected_profit_12m", sa.expected_profit_12m, cur, "derived", decimals=0)
    for s in SCENARIOS:
        R(f"cf.profit_12m.{s}", sa.results[s].profit_12m, cur, "derived", decimals=0)
    R("cf.capital_roi_12m", base_res.capital_roi_12m, "pct", "derived")

    narrative = _narrative_template(d, conf, contest, bb, base_res, be_units, cur)
    violations = validate(narrative, reg)
    if violations:   # шаблон наш собственный: нарушение = баг кода, а не LLM
        raise AssertionError(f"narrative template not grounded: {violations}")

    pkg.update({
        "decision": {"status": d.status, "confidence": conf.level, "score": sc.score,
                     "rule_fired": d.rule, "decision_trace": d.trace, "reasons": d.reasons,
                     "conditional_after_fix": d.conditional_after_fix, "caps_applied": d.caps_applied,
                     "risks": [], "hard_stops": bb.hard_stops if bb else []},
        "confidence": conf.as_dict(),
        "score": sc.as_dict(),
        "compliance": compliance.as_dict(),
        "market": {
            "contestable": contest.as_dict() if contest else None,
            "buybox": bb.as_dict() if bb else None,
            "cohort": None if cohort is None else {"status": cohort.status, "size": cohort.cohort_size,
                                                   "share_reaching": cohort.share_reaching,
                                                   "notes": cohort.notes},
        },
        "launch_plan": {
            "recommended_price": {"currency": cur, "amount": prices["base"], "tax_basis": tax_basis},
            "min_viable_price": {"currency": cur, "amount": mvp_price, "tax_basis": tax_basis},
            "target_units_month_base": units["base"],
            "initial_inventory_units": sa.initial_units,
            "reorder_point_units": sa.reorder_point_units,
            "sales_start_month": sales_start_month(launch.lead_time),
            "inventory_notes": sa.inventory_notes,
        },
        "economics": {
            "unit_economics_base": ue_base.as_dict(),
            "break_even_units": be_units,
            "scenarios": {s: _cf_summary(r) for s, r in sa.results.items()},
            "stress_tests": {k: _cf_summary(r) for k, r in sa.stress.items()},
            "expected_profit_12m": sa.expected_profit_12m,
            "required_capital": base_res.required_capital,
            "capital_at_risk": sa.capital_at_risk,
            "risk_return": sa.risk_return,
        },
        "test_plan": _test_plan(sa, float(max_loss)),
        "metrics": reg.as_list(),
        "narrative_template": narrative,
        "narrative": reg.render(narrative),
        "warnings": warnings + (contest.notes if contest else []) + (bb.notes if bb else []) + sc.notes,
        "assumptions": _assumptions(costs, inp, cfg),
    })
    return pkg


def _cf_summary(r) -> dict:
    return {"profit_12m": r.profit_12m, "cum_cash_12m": r.cum_cash_12m,
            "liquidity_gap": r.liquidity_gap, "required_capital": r.required_capital,
            "payback_month": r.payback_month, "loss_at_horizon": r.loss_at_horizon,
            "capital_roi_12m": r.capital_roi_12m, "stockout_months": r.stockout_months,
            "monthly": [row.__dict__ for row in r.rows]}


def _test_plan(sa, max_loss: float) -> dict:
    cons = sa.results["conservative"]
    start = cons.sales_start_month
    checkpoints = []
    for day, k in ((30, 0), (60, 1), (90, 2)):
        m = start + k
        if m < len(cons.rows):
            checkpoints.append({"day": day, "calendar_month": m,
                                "min_units_month": round(cons.rows[m].units_sold, 1),
                                "basis": "Conservative-сценарий"})
    return {"checkpoints": checkpoints,
            "stop_loss": [
                {"trigger": "Накопленный убыток превысил допустимый убыток теста",
                 "threshold": max_loss, "action": "Остановить рекламу, ликвидировать остаток, статус HOLD"},
                {"trigger": "Продажи < 50 % от min_units_month на двух контрольных точках подряд",
                 "action": "Пересмотр цены/листинга; при повторении — выход"}]}


def _assumptions(costs, inp, cfg) -> list:
    out = [f"config_version={cfg.version}",
           "Кривые разгона и TACoS — стартовые значения конфигурации (§12.1)."]
    if costs.cogs_assumed:
        out.append("ASSUMED_COGS: себестоимость не подтверждена поставщиком.")
    if inp.get("business_model") == "resale":
        out.append("Доля Buy Box по равному делению — гипотеза до калибровки.")
    return out


def _narrative_template(d, conf, contest, bb, base_res, be_units, cur) -> str:
    """Детерминированный шаблон; все числа — через {{metric:...}}."""
    lines = [f"Решение: {d.status} (правило {d.rule}), уверенность {conf.level}, "
             "Score {{metric:decision.score}}."]
    if contest:
        lines.append("Доступный спрос: {{metric:market.contestable_units}} в месяц, "
                     f"ограничение в Base — {contest.binding_constraint['base']}.")
    if bb:
        lines.append("Ожидаемая доля Buy Box: {{metric:market.bb_share}}.")
    lines.append("Рекомендованная цена {{metric:price.recommended}}, минимально жизнеспособная "
                 "{{metric:price.min_viable}}.")
    lines.append("Post-Ad Contribution на единицу {{metric:ue.post_ad_contribution}} "
                 "(маржа {{metric:ue.contribution_margin}}); break-even ACoS для консоли Ads "
                 "{{metric:ue.be_acos_console}}.")
    lines.append("Требуемый капитал {{metric:cf.required_capital}}, капитал под риском "
                 "{{metric:cf.capital_at_risk}}, ожидаемая прибыль за год {{metric:cf.expected_profit_12m}}.")
    if base_res.payback_month is not None:
        lines.append("Окупаемость в Base: {{metric:cf.payback_month}}.")
    else:
        lines.append("В Base окупаемость на горизонте модели не достигается.")
    if d.conditional_after_fix:
        lines.append(f"После устранения препятствий решение было бы: {d.conditional_after_fix}.")
    return "\n".join(lines)


def analyze_file(path: str, cfg: Config = DEFAULT_CONFIG) -> dict:
    with open(path, encoding="utf-8") as f:
        return analyze(json.load(f), cfg)
