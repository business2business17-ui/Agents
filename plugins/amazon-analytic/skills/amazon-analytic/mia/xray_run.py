"""Прогон ниши и продуктовых гипотез по выгрузкам Helium 10 (ТЗ v1.2 §3, §13, §15).

Конфиг (JSON):
{
  "as_of": "2026-10-20",
  "xray": "XRAY/....xlsx", "cerebro": "XRAY/....xlsx",
  "niche": {NicheDefinition},
  "user": {параметры, которых нет в выгрузках — см. niche.build_input},
  "hypotheses": [
    {"id": "h1", "name": "...", "niche": {переопределения правила включения},
     "user": {переопределения: scenarios.prices, costs, ...}}
  ]
}

Каждая гипотеза — своя подниша (правило включения поверх базового) со своими ценами и
затратами; решение по ней выносит Decision Engine, а не LLM. Итоговая таблица
сортируется по ожидаемой прибыли среди GO/TEST (§14.1).
"""
from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path

from .config import DEFAULT_CONFIG, Config
from .evidence import WHITE_SPACE, assess, conservative_units
from .importers import read_cerebro, read_xray
from .niche import EmptyNicheError, NicheDefinition, build_input, niche_rows
from .pipeline import analyze
from .portfolio import Candidate, build_portfolio

RANKABLE = ("GO", "TEST")


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _summary(hid, name, pkg, evidence=None) -> dict:
    if pkg is None:
        return {"id": hid, "name": name, "status": "WHITE SPACE", "rule": None, "confidence": None,
                "score": None, "asins": 0, "evidence": WHITE_SPACE, "missing": None}
    d = pkg["decision"]
    m = {x["metric_id"]: x["value"] for x in pkg.get("metrics", [])}
    imp = pkg.get("import", {})
    mm = imp.get("market_metrics", {})
    return {
        "id": hid, "name": name, "status": d["status"], "rule": d.get("rule_fired"),
        "confidence": d.get("confidence"), "score": d.get("score"),
        "asins": imp.get("included"), "niche_revenue_base": (mm.get("revenue_month") or {}).get("base"),
        "price": m.get("price.recommended"), "post_ad_contribution": m.get("ue.post_ad_contribution"),
        "required_capital": m.get("cf.required_capital"), "expected_profit_12m": m.get("cf.expected_profit_12m"),
        "payback_month": m.get("cf.payback_month"),
        "missing": (d.get("decision_trace") or [{}])[0].get("values", {}).get("missing")
        if d["status"] == "INSUFFICIENT DATA" else None,
        "evidence": evidence.status if evidence else None,
    }


def _candidate(r: dict) -> Candidate:
    pkg, ev, inp = r["package"], r["evidence"], r["input"]
    if pkg is None:
        return Candidate(r["id"], r["name"], "WHITE SPACE", None, None, WHITE_SPACE, ev.failed,
                         None, None, None, None, None, None)
    d, eco, lp = pkg["decision"], pkg.get("economics", {}), pkg.get("launch_plan", {})
    # объём кластера поровну на его ключи (точный объём ключа в кластер не передаётся)
    kws = {k: c["search_volume_month"] / max(len(c["keywords"]), 1)
           for c in inp.get("keywords", {}).get("clusters", []) for k in c["keywords"]}
    return Candidate(
        r["id"], r["name"], d["status"], d.get("rule_fired"), d.get("conditional_after_fix"), ev.status,
        ev.failed, eco.get("expected_profit_12m"), eco.get("required_capital"), eco.get("capital_at_risk"),
        lp.get("initial_inventory_units"), lp.get("target_units_month_base"),
        (inp.get("launch") or {}).get("moq"), kws, {x.asin for x in r["rows"]},
        reasons=[x for x in d.get("reasons", [])])


def run_config(conf: dict, base_dir: str | Path = ".", cfg: Config = DEFAULT_CONFIG) -> dict:
    base_dir = Path(base_dir)
    as_of = date.fromisoformat(conf["as_of"]) if conf.get("as_of") else date.today()
    xray_path = base_dir / conf["xray"]
    rows = read_xray(str(xray_path))
    keywords = read_cerebro(str(base_dir / conf["cerebro"])) if conf.get("cerebro") else None
    sources = [{"type": "helium10_xray", "file": conf["xray"], "rows": len(rows)}]
    if keywords is not None:
        sources.append({"type": "helium10_cerebro", "file": conf["cerebro"], "rows": len(keywords)})

    def run(hid, name, niche_over, user_over):
        nd = NicheDefinition.from_dict(deep_merge(conf["niche"], niche_over or {}))
        user = deep_merge(conf.get("user", {}), user_over or {})
        included = niche_rows(nd, rows)[0]
        price = ((user.get("scenarios") or {}).get("prices") or {}).get("base")
        ev = assess(included, price, as_of, cfg)
        try:
            inp = build_input(nd, rows, user, keywords=keywords, as_of=as_of, sources=sources)
        except EmptyNicheError:
            return {"id": hid, "name": name, "package": None, "input": {}, "rows": [], "evidence": ev}
        pkg = analyze(inp, cfg)
        pkg["evidence"] = ev.as_dict()
        return {"id": hid, "name": name, "package": pkg, "input": inp, "rows": included, "evidence": ev}

    results = [run("niche", "Ниша целиком", {}, {})]
    for h in conf.get("hypotheses", []):
        niche_over = dict(h.get("niche", {}))
        niche_over.setdefault("niche_id", f"{conf['niche']['niche_id']}--{h['id']}")
        results.append(run(h["id"], h.get("name", h["id"]), niche_over, h.get("user", {})))

    table = [_summary(r["id"], r["name"], r["package"], r["evidence"]) for r in results]
    ranked = sorted((t for t in table[1:] if t["status"] in RANKABLE),
                    key=lambda t: -(t["expected_profit_12m"] or float("-inf")))
    pconf = conf.get("portfolio", {})
    user = conf.get("user", {})
    portfolio = build_portfolio(
        [_candidate(r) for r in results[1:]], cfg,
        budget=pconf.get("budget", user.get("budget")),
        fba_capacity=pconf.get("fba_capacity_units", (user.get("launch") or {}).get("fba_capacity_units")),
        target_profit_12m=pconf.get("target_profit_12m"), max_skus=pconf.get("max_skus"))
    competitors = [_competitor(x, as_of) for x in sorted(results[0]["rows"], key=lambda x: -(x.revenue or 0))]
    for r in results:                       # строки и вход — рабочие данные, в результат не идут
        r.pop("rows", None)
        r.pop("input", None)
        r["evidence"] = r["evidence"].as_dict()
    return {"as_of": as_of.isoformat(), "config_version": cfg.version, "summary": table,
            "ranking_by_expected_profit": [t["id"] for t in ranked], "portfolio": portfolio,
            "competitors": competitors, "results": results}


def _competitor(r, as_of: date) -> dict:
    """Строка конкурента для отчёта (§4): только поля выгрузки, без интерпретации."""
    return {"asin": r.asin, "brand": r.brand, "title": r.title, "url": r.url, "price": r.price,
            "units": r.units, "units_conservative": conservative_units(r), "badge_floor": r.badge_floor,
            "revenue": r.revenue, "reviews": r.reviews, "rating": r.rating, "fulfillment": r.fulfillment,
            "amazon_retail": r.is_amazon_retail, "size_tier": r.size_tier,
            "age_months": round((as_of - r.created).days / 30.44, 1) if r.created else None,
            "currency": r.currency}


def run_file(path: str, cfg: Config = DEFAULT_CONFIG) -> dict:
    p = Path(path)
    with open(p, encoding="utf-8") as f:
        conf = json.load(f)
    return run_config(conf, base_dir=conf.get("base_dir") or p.parent.parent, cfg=cfg)
