"""Отчёт по нише: HTML (+PDF через headless Edge/Chrome) из результата xray_run (ТЗ v1.2 §19, §20.3).

Структура — решение на первой странице, а не на тридцатой:
1. Решение: статус ниши, Score, уверенность и слабое звено, рынок, волна 1 портфеля, главные риски.
2. Шорт-лист гипотез: решение, доказательность, экономика, капитал.
3. Портфель: волны, «после устранения», каннибализация, риски MOQ.
4. Конкуренты (§4) и подниши гипотез.
5. Карточки гипотез: проверки доказательности, причины решения, модели.
6. Отклонённые идеи и white space.
7. Чего не хватает и как получить.
8. Приложение: метрики с metric_id, источники, версии, журнал валидатора.

Числа в связном тексте — только плейсхолдеры {{metric:…}} / {{cmp:…}} и т. п., которые
подставляет код; шаблоны проходят grounding.validate + factcheck (§20.3). Текст от LLM
передаётся в `narratives` и проверяется так же: предложения с нарушениями не попадают в
отчёт и перечисляются в приложении. Таблицы строит код напрямую из данных.
"""
from __future__ import annotations

import html
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .factcheck import COMPETITOR, HYPOTHESIS, Entity, FactTable
from .grounding import CURRENCY_SIGNS, MetricRegistry, _SENTENCE_SPLIT, _fmt_number, validate

STATUS_CLASS = {"GO": "go", "TEST": "test", "HOLD": "hold", "NO-GO": "nogo",
                "INSUFFICIENT DATA": "nodata", "WHITE SPACE": "nodata"}
EVIDENCE_RU = {"validated": "подтверждена", "weak": "слабая", "hypothesis": "гипотеза",
               "white_space": "white space"}
CHECK_RU = {"brands": "разные бренды", "young": "молодая модель", "price": "цена в коридоре",
            "top1": "не держится на одном ASIN", "models": "модели ≥ порога", "demand_seen": "спрос в выдаче"}
HOW_TO_GET = {
    "cogs": "Оффер поставщика (цена, MOQ, сроки) — снимает ограничение «не выше TEST».",
    "sources": "Второй источник оценок (SmartScout/Jungle Scout) или свои продажи (SP-API) для калибровки.",
    "seasonality": "История BSR/продаж за 12 мес. (Keepa) — сезонный индекс и тренд.",
    "entrant_history": "История новых входов с выбывшими ASIN (Keepa) — NESR.",
    "coverage": "Расширить выгрузку (больше ASIN, несколько seed-запросов).",
    "freshness": "Свежая выгрузка Xray/Cerebro.",
}


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def num(v, d=0) -> str:
    return "—" if v is None else _fmt_number(float(v), d)


def money(v, cur, d=0) -> str:
    if v is None:
        return "—"
    sign = "−" if float(v) < 0 else ""
    return f"{sign}{CURRENCY_SIGNS.get(cur, cur + ' ')}{_fmt_number(abs(float(v)), d)}"


def pct(v, d=0) -> str:
    return "—" if v is None else f"{_fmt_number(float(v) * 100, d)} %"


def badge(status: str) -> str:
    return f'<span class="badge {STATUS_CLASS.get(status, "nodata")}">{esc(status)}</span>'


# ---------------------------------------------------------------- реестр и факты для текста

def _registry(res: dict, cur: str) -> MetricRegistry:
    niche = res["results"][0]["package"]
    imp = niche.get("import") or {}
    mm = imp.get("market_metrics") or {}
    km = imp.get("keyword_metrics") or {}
    pf = res["portfolio"]
    reg = MetricRegistry()
    src = ", ".join(s["file"] for s in imp.get("sources", []))
    if mm:
        reg.add("niche.revenue", mm["revenue_month"], cur, "estimated", src, decimals=0)
        reg.add("niche.asins", mm["asins"], "count", "observed", src)
        reg.add("niche.brands", mm["brands"], "count", "observed", src)
        reg.add("niche.cr3", mm["cr"][3], "pct", "derived", decimals=0)
        reg.add("niche.amazon_share", mm["amazon_retail_share"], "pct", "derived", decimals=0)
        reg.add("niche.review_median_top10", mm["review_median_top10"], "count", "observed", src, decimals=0)
        if mm.get("badge_check"):
            reg.add("niche.revenue_badge", mm["badge_check"]["revenue_badge_consistent"], cur, "derived",
                    "Amazon «X+ bought»", decimals=0)
            reg.add("niche.badge_divergence", mm["badge_check"]["divergence"], "pct", "derived", decimals=0)
    if km:
        reg.add("kw.nonbranded", km["nonbranded_share"], "pct", "derived", decimals=0)
        if km.get("trend_weighted") is not None:
            reg.add("kw.trend", km["trend_weighted"], "pct", "derived", decimals=0)
    reg.add("niche.score", niche["decision"].get("score"), "score", "derived", decimals=1)
    t = pf["wave_1_totals"]
    reg.add("pf.wave1_capital", t["required_capital"], cur, "derived", decimals=0)
    reg.add("pf.wave1_profit", t["expected_profit_12m"], cur, "derived", decimals=0)
    reg.add("pf.wave1_units", t["initial_units"], "units", "derived")
    reg.add("pf.wave1_count", len(pf["wave_1"]), "count", "derived")
    reg.add("pf.hypotheses", len(res["results"]) - 1, "count", "derived")
    if pf.get("budget") is not None:
        reg.add("pf.budget", pf["budget"], cur, "observed", "пользователь", decimals=0)
    return reg


def _facts(res: dict) -> FactTable:
    ft = FactTable()
    for c in res.get("competitors", []):
        ft.add(Entity(c["asin"].lower(), c["title"][:60], COMPETITOR, c["brand"],
                      {k: c[k] for k in ("units", "units_conservative", "revenue", "price", "reviews")
                       if c.get(k) is not None}))
    for r in res["results"][1:]:
        ft.add(Entity(r["id"].lower(), r["name"], HYPOTHESIS, tags={r["evidence"]["status"]}))
    return ft


def _grounded(template: str, reg: MetricRegistry, facts: FactTable, audit: list, section: str) -> str:
    """Шаблон → текст. Предложения с нарушениями выбрасываются и попадают в журнал."""
    kept = []
    for sentence in _SENTENCE_SPLIT.split(template):
        if not sentence.strip():
            continue
        v = validate(sentence, reg, facts)
        if v:
            audit.append({"section": section, "sentence": sentence,
                          "violations": [f"{x.kind}: {x.token}" for x in v]})
        else:
            kept.append(reg.render(facts.render(sentence)))
    return " ".join(kept)


# ---------------------------------------------------------------- секции

def _risks(res: dict) -> list:
    """3–5 главных рисков детерминированно: слабые измерения уверенности, MOQ, концентрация, compliance."""
    niche = res["results"][0]["package"]
    out = []
    for dim, x in (niche.get("confidence") or {}).get("dimensions", {}).items():
        if x["level"] == "LOW":
            out.append(f"Уверенность LOW по «{dim}»: {x['why']}")
    for hid, rs in res["portfolio"]["risks"].items():
        out.extend(f"{hid}: {r}" for r in rs[:1])
    for r in res["results"][1:]:
        if "top1" in r["evidence"].get("failed", []):
            out.append(f"{r['id']}: спрос сегмента держится на одном листинге "
                       f"({pct(r['evidence']['top1_share'])})")
    opened = [i for i in (niche.get("compliance") or {}).get("items", [])
              if i["status"] in ("REVIEW REQUIRED", "BLOCKED")]
    if opened:
        out.append(f"Compliance: не подтверждено {len(opened)} пунктов (нужны документы)")
    return out[:6]


def _page1(res, reg, facts, audit, cur) -> str:
    niche = res["results"][0]["package"]
    d = niche["decision"]
    conf = niche.get("confidence") or {}
    weakest = [k for k, x in conf.get("dimensions", {}).items() if x["level"] == conf.get("level")]
    pf = res["portfolio"]
    lines = []
    if "niche.revenue" in reg:
        lines.append("Выручка ниши в месяц: {{metric:niche.revenue}} по оценке Helium.")
    if "niche.revenue_badge" in reg:
        lines.append("С поправкой на бейдж Amazon: {{metric:niche.revenue_badge}} "
                     "(расхождение {{metric:niche.badge_divergence}}).")
    if "niche.cr3" in reg:
        lines.append("Концентрация CR3 {{metric:niche.cr3}}, доля Amazon как продавца {{metric:niche.amazon_share}}, "
                     "медиана отзывов TOP10 — {{metric:niche.review_median_top10}}.")
    if "kw.nonbranded" in reg:
        lines.append("Небрендовый спрос {{metric:kw.nonbranded}}" +
                     (", тренд запросов {{metric:kw.trend}}." if "kw.trend" in reg else "."))
    if pf["wave_1"]:
        lines.append("Волна портфеля: SKU — {{metric:pf.wave1_count}}, капитал {{metric:pf.wave1_capital}}, "
                     "ожидаемая прибыль за год {{metric:pf.wave1_profit}}.")
    else:
        lines.append("Из проверенных гипотез ({{metric:pf.hypotheses}}) ни одна не проходит в волну запуска.")
    text = _grounded(" ".join(lines), reg, facts, audit, "Решение")

    wave = (", ".join(esc(_name(res, h)) for h in pf["wave_1"]) if pf["wave_1"]
            else "<b>пусто — запускать нечего</b>")
    after = pf["after_fix"]["plan"]
    risks = "".join(f"<li>{esc(r)}</li>" for r in _risks(res)) or "<li>—</li>"
    steps = "".join(f"<li>{esc(s)}</li>" for s in _next_steps(res)) or "<li>—</li>"
    return f"""
<section class="page1">
  <div class="decision">
    <div>{badge(d['status'])} <span class="rule">правило {esc(d.get('rule_fired'))}</span></div>
    <div class="kpis">
      <div><span>Score</span><b>{num(d.get('score'), 1)}</b></div>
      <div><span>Уверенность</span><b>{esc(conf.get('level', '—'))}</b><small>слабое звено: {esc(', '.join(weakest) or '—')}</small></div>
      <div><span>После устранения</span><b>{esc(d.get('conditional_after_fix') or '—')}</b></div>
    </div>
  </div>
  <p class="lead">{esc(text)}</p>
  <div class="grid2">
    <div class="card"><h3>Волна 1 портфеля</h3><p>{wave}</p>
      <p class="muted">После устранения препятствий: {esc(', '.join(_name(res, h) for h in after) or 'пусто')}</p></div>
    <div class="card"><h3>Главные риски</h3><ul>{risks}</ul></div>
  </div>
  <div class="card steps"><h3>Следующие шаги</h3><ol>{steps}</ol></div>
</section>"""


def _next_steps(res) -> list:
    """Что сделать, чтобы решение стало возможным или надёжнее: слабые измерения уверенности,
    недостающие критичные поля, затем compliance — в этом порядке."""
    niche = res["results"][0]["package"]
    out = []
    dims = (niche.get("confidence") or {}).get("dimensions", {})
    for k in sorted(dims, key=lambda k: {"LOW": 0, "MEDIUM": 1}.get(dims[k]["level"], 2)):
        if dims[k]["level"] != "HIGH" and HOW_TO_GET.get(k):
            out.append(HOW_TO_GET[k])
    for r in res["results"]:
        p = r["package"]
        if p and p["decision"]["status"] == "INSUFFICIENT DATA":
            out.extend(f"{m}: {how}" for m, how in p["decision"].get("how_to_get", {}).items())
    n = sum(i["status"] in ("REVIEW REQUIRED", "BLOCKED") for i in (niche.get("compliance") or {}).get("items", []))
    if n:
        out.append(f"Собрать документы по {n} пунктам compliance (список — в разделе «Чего не хватает»).")
    if not res["portfolio"]["wave_1"] and any(r["evidence"]["status"] == "weak" for r in res["results"][1:]):
        out.append("Пересобрать гипотезы под сегменты, где спрос не держится на одном листинге и есть молодые модели.")
    return list(dict.fromkeys(out))[:5]


def _name(res, hid) -> str:
    return next((r["name"] for r in res["results"] if r["id"] == hid), hid)


def _shortlist(res, cur) -> str:
    rows = []
    for t, r in zip(res["summary"][1:], res["results"][1:]):
        ev = r["evidence"]
        rows.append(f"""<tr><td><b>{esc(t['id'])}</b><br><small>{esc(t['name'])}</small></td>
<td>{badge(t['status'])}<br><small>{esc(t.get('rule') or '')}</small></td>
<td>{esc(EVIDENCE_RU.get(ev['status'], ev['status']))}</td>
<td class="n">{num(t.get('asins'))}</td><td class="n">{money(t.get('price'), cur, 2)}</td>
<td class="n">{money(t.get('post_ad_contribution'), cur, 2)}</td><td class="n">{money(t.get('required_capital'), cur)}</td>
<td class="n">{money(t.get('expected_profit_12m'), cur)}</td>
<td class="n">{esc(t.get('payback_month') or '—')}</td><td class="n">{num(t.get('score'), 1)}</td></tr>""")
    return f"""<section><h2>Гипотезы</h2>
<table><thead><tr><th>Гипотеза</th><th>Решение</th><th>Доказательность</th><th>ASIN</th><th>Цена</th>
<th>Вклад/ед.</th><th>Капитал</th><th>E[прибыль 12 мес.]</th><th>Окупаемость, мес.</th><th>Score</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p class="muted">Вклад/ед. — post-ad contribution в Base; E[прибыль] — взвешенная по сценариям (§11.4).</p></section>"""


def _portfolio(res) -> str:
    pf = res["portfolio"]
    items = []
    for x in pf["wave_2"]:
        items.append(f"<li><b>Волна 2:</b> {esc(_name(res, x['id']))} — {esc(x['reason'])}</li>")
    for c in pf["after_fix"]["candidates"]:
        fix = "; ".join(c["fix"][:3])
        items.append(f"<li><b>После устранения:</b> {esc(_name(res, c['id']))} → {esc(c['decision_after_fix'])} "
                     f"(доказательность {esc(EVIDENCE_RU.get(c['evidence']))}). Устранить: {esc(fix)}</li>")
    for x in pf["rejected"]:
        items.append(f"<li><b>Отклонено:</b> {esc(_name(res, x['id']))} — {esc(x['reason'])}</li>")
    for c in pf["cannibalization"]:
        items.append(f"<li><b>Каннибализация:</b> {esc(c['a'])} ↔ {esc(c['b'])} — общие ключи {pct(c['keywords'])}, "
                     f"общие конкуренты {pct(c['asins'])}</li>")
    for hid, rs in pf["risks"].items():
        items.extend(f"<li><b>Риск {esc(hid)}:</b> {esc(r)}</li>" for r in rs)
    target = ("" if pf["target_profit_12m"] is None else
              f"<p>Цель по прибыли: {num(pf['target_profit_12m'])} — "
              f"{'достигнута' if pf['target_met'] else 'не достигнута'}.</p>")
    return f"""<section><h2>Портфель (§13)</h2>
<p>Волна 1: <b>{esc(', '.join(_name(res, h) for h in pf['wave_1']) or 'пусто')}</b>.
В волну 1 попадают только GO/TEST с подтверждённой доказательностью; без цели по прибыли — один SKU.</p>
{target}<ul>{''.join(items) or '<li>—</li>'}</ul></section>"""


def _competitors(res, cur, top_n) -> str:
    rows = []
    for c in res.get("competitors", [])[:top_n]:
        rows.append(f"""<tr><td><a href="{esc(c['url'])}">{esc(c['asin'])}</a></td><td>{esc(c['brand'])}</td>
<td class="t">{esc(c['title'][:70])}</td><td class="n">{money(c['price'], cur, 2)}</td>
<td class="n">{num(c['units'])}</td><td class="n">{num(c['units_conservative'])}</td>
<td class="n">{'—' if c['badge_floor'] is None else num(c['badge_floor']) + '+'}</td>
<td class="n">{money(c['revenue'], cur)}</td><td class="n">{num(c['reviews'])}</td>
<td class="n">{num(c['age_months'])}</td><td>{esc('Amazon' if c['amazon_retail'] else c['fulfillment'])}</td></tr>""")
    total = len(res.get("competitors", []))
    return f"""<section><h2>Конкуренты ниши (TOP {min(top_n, total)} из {total} по выручке)</h2>
<table class="small"><thead><tr><th>ASIN</th><th>Бренд</th><th>Товар</th><th>Цена</th><th>Продажи Helium</th>
<th>Продажи осторожно</th><th>Бейдж Amazon</th><th>Выручка</th><th>Отзывы</th><th>Возраст, мес.</th><th>Продавец</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p class="muted">«Осторожно» — оценка Helium, не выше верхней границы бейджа Amazon «X+ bought».</p></section>"""


def _segments(res, cur) -> str:
    rows = []
    for r in res["results"]:
        p = r["package"]
        mm = ((p or {}).get("import") or {}).get("market_metrics") or {}
        if not mm:
            rows.append(f"<tr><td>{esc(r['name'])}</td><td colspan=7 class='muted'>ASIN в выдаче нет</td></tr>")
            continue
        rows.append(f"""<tr><td>{esc(r['name'])}</td><td class="n">{num(mm['asins'])}</td><td class="n">{num(mm['brands'])}</td>
<td class="n">{money(mm['revenue_month']['base'], cur)}</td><td class="n">{pct(mm['cr'][3])}</td>
<td class="n">{num(mm['hhi_brand'])}</td><td class="n">{pct(mm['amazon_retail_share'])}</td>
<td class="n">{money(mm['price']['p10'], cur, 2)}–{money(mm['price']['p90'], cur, 2)}</td></tr>""")
    return f"""<section><h2>Ниша и подниши гипотез</h2>
<table><thead><tr><th>Сегмент</th><th>ASIN</th><th>Брендов</th><th>Выручка/мес.</th><th>CR3</th><th>HHI</th>
<th>Amazon</th><th>Цена P10–P90</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>"""


def _cards(res, cur) -> str:
    out = []
    for r in res["results"][1:]:
        ev, p = r["evidence"], r["package"]
        checks = "".join(f"<li class='{'ok' if c['passed'] else 'bad'}'>{'✓' if c['passed'] else '✗'} "
                         f"{esc(CHECK_RU.get(c['check'], c['check']))}: {esc(c['detail'])}</li>"
                         for c in ev["checks"])
        models = "".join(f"<tr><td>{esc(m['asin'])}</td><td>{esc(m['brand'])}</td><td class='n'>{num(m['units'])}</td>"
                         f"<td class='n'>{money(m['price'], cur, 2)}</td><td class='n'>{num(m['reviews'])}</td>"
                         f"<td class='n'>{num(m['age_months'])}</td><td>{'да' if m['young'] else ''}</td></tr>"
                         for m in ev.get("models", [])[:8])
        if p is None:
            body = "<p>В выгрузке нет ни одного ASIN такого продукта: спрос не подтверждён (§7).</p>"
            status = "WHITE SPACE"
        else:
            d = p["decision"]
            status = d["status"]
            reasons = [x for x in d.get("reasons", []) if not x.endswith("REVIEW REQUIRED")]
            n_review = sum(x.endswith("REVIEW REQUIRED") for x in d.get("reasons", []))
            if n_review:
                reasons.append(f"Compliance без подтверждения: {n_review} пунктов")
            ue = (p.get("economics") or {}).get("unit_economics_base") or {}
            body = f"""<ul>{''.join(f'<li>{esc(x)}</li>' for x in reasons)}</ul>
<p>После устранения: <b>{esc(d.get('conditional_after_fix') or '—')}</b>.
Минимально жизнеспособная цена {money((p.get('launch_plan') or {}).get('min_viable_price', {}).get('amount'), cur, 2)},
pre-ad вклад {money(ue.get('pre_ad_contribution'), cur, 2)}, post-ad {money(ue.get('post_ad_contribution'), cur, 2)}.</p>"""
        table = (f"<table class='small'><thead><tr><th>Модель</th><th>Бренд</th><th>Продажи</th><th>Цена</th>"
                 f"<th>Отзывы</th><th>Возраст</th><th>Молодая</th></tr></thead><tbody>{models}</tbody></table>"
                 if models else "")
        out.append(f"""<div class="hcard"><h3>{esc(r['name'])} {badge(status)}
<span class="ev">доказательность: {esc(EVIDENCE_RU.get(ev['status'], ev['status']))}</span></h3>
<ul class="checks">{checks}</ul>{body}{table}</div>""")
    return f"<section><h2>Карточки гипотез</h2>{''.join(out)}</section>"


def _missing(res) -> str:
    niche = res["results"][0]["package"]
    items, seen = [], set()
    for k, x in (niche.get("confidence") or {}).get("dimensions", {}).items():
        if x["level"] != "HIGH" and k not in seen:
            seen.add(k)
            items.append(f"<li><b>{esc(k)}</b> ({esc(x['level'])}: {esc(x['why'])}) — {esc(HOW_TO_GET.get(k, ''))}</li>")
    for r in res["results"]:
        p = r["package"]
        if p and p["decision"]["status"] == "INSUFFICIENT DATA":
            for m, how in p["decision"].get("how_to_get", {}).items():
                if m not in seen:
                    seen.add(m)
                    items.append(f"<li><b>{esc(m)}</b> — {esc(how)}</li>")
    docs = {}
    for i in (niche.get("compliance") or {}).get("items", []):
        if i["status"] in ("REVIEW REQUIRED", "BLOCKED"):
            docs[i["title"]] = i["required_documents"]
    comp = "".join(f"<li>{esc(t)}: {esc(', '.join(dd))}</li>" for t, dd in docs.items())
    assumptions = "".join(f"<li>{esc(a)}</li>" for a in niche.get("assumptions", []))
    warnings = "".join(f"<li>{esc(w)}</li>" for w in niche.get("warnings", []))
    return f"""<section><h2>Чего не хватает и как получить</h2><ul>{''.join(items) or '<li>—</li>'}</ul>
<h3>Документы compliance</h3><ul>{comp or '<li>—</li>'}</ul>
<h3>Допущения</h3><ul>{assumptions or '<li>—</li>'}</ul>
<h3>Предупреждения по данным</h3><ul>{warnings or '<li>—</li>'}</ul></section>"""


def _appendix(res, reg, audit) -> str:
    niche = res["results"][0]["package"]
    imp = niche.get("import") or {}
    metrics = "".join(f"<tr><td><code>{esc(m['metric_id'])}</code></td><td class='n'>{esc(reg.format(m['metric_id']))}</td>"
                      f"<td>{esc(m['data_type'])}</td><td>{esc(m['source'] or '')}</td></tr>" for m in reg.as_list())
    core = "".join(f"<tr><td><code>{esc(m['metric_id'])}</code></td><td class='n'>{esc(_raw(m['value']))}</td>"
                   f"<td>{esc(m['data_type'])}</td><td>{esc(m.get('unit'))}</td></tr>" for m in niche.get("metrics", []))
    sources = "".join(f"<li>{esc(s['type'])}: {esc(s['file'])} ({esc(s['rows'])} строк)</li>" for s in imp.get("sources", []))
    v = niche.get("versions", {})
    rej = "".join(f"<li>[{esc(a['section'])}] «{esc(a['sentence'])}» — {esc('; '.join(a['violations']))}</li>"
                  for a in audit)
    excl = imp.get("excluded", [])
    excluded = "".join(f"<li>{esc(x['asin'])} — {esc(x['title'])}: {esc(x['reason'])}</li>" for x in excl[:40])
    return f"""<section class="appendix"><h2>Приложение</h2>
<h3>Метрики текста отчёта</h3><table class="small"><thead><tr><th>metric_id</th><th>Значение</th><th>Тип</th><th>Источник</th></tr></thead><tbody>{metrics}</tbody></table>
<h3>Метрики решения по нише</h3><table class="small"><thead><tr><th>metric_id</th><th>Значение</th><th>Тип</th><th>Ед.</th></tr></thead><tbody>{core}</tbody></table>
<h3>Источники и версии</h3><ul>{sources}<li>Срез: {esc(res['as_of'])}; config {esc(res['config_version'])}; расчёт {esc(v.get('calculation_version'))}; fee schedule {esc(v.get('fee_schedule_version'))}</li>
<li>Определение ниши: {esc(niche.get('niche_definition_id'))}</li></ul>
<h3>Исключённые ASIN ({len(excl)})</h3><ul class="small">{excluded or '<li>—</li>'}</ul>
<h3>Журнал валидатора (§20.3)</h3><ul>{rej or '<li>Нарушений нет: все числа текста заземлены.</li>'}</ul></section>"""


def _raw(v):
    if isinstance(v, dict):
        return " / ".join(f"{k} {num(x, 2)}" for k, x in v.items() if isinstance(x, (int, float)))
    return num(v, 2) if isinstance(v, (int, float)) else v


CSS = """
:root{--fg:#1d2330;--muted:#677084;--line:#dfe3ea;--bg:#ffffff;--card:#f6f7f9;
--go:#1f7a4d;--test:#2459a8;--hold:#a86a00;--nogo:#b3261e;--nodata:#5f6b7a}
*{box-sizing:border-box}body{font:13px/1.45 -apple-system,"Segoe UI",Roboto,Arial,sans-serif;color:var(--fg);
background:var(--bg);margin:0;padding:24px;max-width:1100px;margin:auto}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 10px;padding-bottom:4px;border-bottom:2px solid var(--line)}
h3{font-size:14px;margin:14px 0 6px}.muted,small{color:var(--muted)}small{font-size:11px}
.sub{color:var(--muted);margin-bottom:16px}
.badge{display:inline-block;padding:3px 10px;border-radius:12px;color:#fff;font-weight:600;font-size:12px}
.go{background:var(--go)}.test{background:var(--test)}.hold{background:var(--hold)}.nogo{background:var(--nogo)}.nodata{background:var(--nodata)}
.decision{display:flex;gap:24px;align-items:center;flex-wrap:wrap;padding:14px;border:1px solid var(--line);border-radius:8px}
.decision .badge{font-size:18px;padding:6px 16px}.rule{color:var(--muted);margin-left:6px}
.kpis{display:flex;gap:24px;flex-wrap:wrap}.kpis div{display:flex;flex-direction:column}.kpis span{color:var(--muted);font-size:11px}
.kpis b{font-size:16px}.lead{font-size:14px;margin:14px 0}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}.card{background:var(--card);border-radius:8px;padding:12px}
.card h3{margin-top:0}.steps{margin-top:14px}.steps ol{margin:0;padding-left:20px}table{width:100%;border-collapse:collapse;margin:6px 0}th,td{border-bottom:1px solid var(--line);
padding:5px 6px;text-align:left;vertical-align:top}th{font-size:11px;color:var(--muted);font-weight:600}
td.n,th.n{text-align:right;white-space:nowrap}table.small td,table.small th{font-size:11px;padding:3px 5px}
td.t{max-width:280px}.hcard{border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:10px 0;break-inside:avoid}
.hcard h3{margin:0 0 6px}.ev{font-weight:400;color:var(--muted);font-size:12px;margin-left:6px}
.checks{list-style:none;padding:0;margin:4px 0}.checks .ok{color:var(--go)}.checks .bad{color:var(--nogo)}
a{color:var(--test)}code{font-size:11px}ul.small{font-size:11px}
@media (max-width:720px){.grid2{grid-template-columns:1fr}body{padding:12px}}
@media print{body{padding:0;max-width:none}.page1{break-after:page}section{break-inside:auto}h2{break-after:avoid}
a{color:inherit;text-decoration:none}@page{size:A4;margin:14mm}}
"""


def build_report(res: dict, title: str | None = None, narratives: dict | None = None, top_n: int = 25) -> tuple:
    """→ (html, audit). narratives: {"после решения": "текст LLM с плейсхолдерами", …}."""
    niche = res["results"][0]["package"]
    cur = (res.get("competitors") or [{}])[0].get("currency") or "EUR"
    reg = _registry(res, cur)
    facts = _facts(res)
    facts.to_registry(reg, prefix="comp")
    audit = []
    page1 = _page1(res, reg, facts, audit, cur)
    extra = "".join(f"<section><h2>{esc(sec)}</h2><p>{esc(_grounded(t, reg, facts, audit, sec))}</p></section>"
                    for sec, t in (narratives or {}).items())
    title = title or f"Анализ ниши {niche.get('niche_definition_id')}"
    body = (page1 + extra + _shortlist(res, cur) + _portfolio(res) + _segments(res, cur) + _cards(res, cur)
            + _competitors(res, cur, top_n) + _missing(res) + _appendix(res, reg, audit))
    doc = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{CSS}</style></head>
<body><h1>{esc(title)}</h1><div class="sub">Amazon.{esc(niche.get('marketplace'))} · {esc(niche.get('business_model'))} ·
срез {esc(res['as_of'])} · решение выносит детерминированное ядро (ТЗ v1.2 §15), числа текста — с metric_id</div>
{body}</body></html>"""
    return doc, audit


# ---------------------------------------------------------------- файлы

def find_browser() -> str | None:
    """Edge или Chrome для печати в PDF (headless)."""
    candidates = [shutil.which(n) for n in ("msedge", "chrome", "google-chrome", "chromium", "chromium-browser")]
    candidates += [os.path.expandvars(p) for p in (
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")]
    return next((c for c in candidates if c and Path(c).exists()), None)


def html_to_pdf(html_path: str, pdf_path: str, timeout: int = 120) -> bool:
    browser = find_browser()
    if not browser:
        return False
    with tempfile.TemporaryDirectory() as profile:
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
               f"--user-data-dir={profile}", f"--print-to-pdf={Path(pdf_path).resolve()}",
               Path(html_path).resolve().as_uri()]
        try:
            subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return False
    return Path(pdf_path).exists() and Path(pdf_path).stat().st_size > 0


def write_report(res: dict, html_path: str, pdf: bool = False, **kw) -> dict:
    doc, audit = build_report(res, **kw)
    Path(html_path).write_text(doc, encoding="utf-8")
    out = {"html": str(html_path), "pdf": None, "audit": audit}
    if pdf:
        pdf_path = str(Path(html_path).with_suffix(".pdf"))
        if html_to_pdf(html_path, pdf_path):
            out["pdf"] = pdf_path
    return out
