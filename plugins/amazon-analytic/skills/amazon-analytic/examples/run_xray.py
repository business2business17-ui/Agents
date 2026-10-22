"""Запуск: python examples/run_xray.py examples/de_tanning_xray.json [--pdf]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mia.report import write_report  # noqa: E402
from mia.xray_run import run_file  # noqa: E402


def fmt(v, d=0):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.{d}f}".replace(",", " ")
    return str(v)


args = [a for a in sys.argv[1:] if not a.startswith("--")]
path = args[0] if args else "examples/de_tanning_xray.json"
res = run_file(path)

niche = res["results"][0]["package"]
imp = niche.get("import", {})
mm = imp.get("market_metrics", {})
print(f"Ниша {niche['niche_definition_id']}: {imp.get('included')} ASIN включено, "
      f"{len(imp.get('excluded', []))} исключено")
if mm:
    rv = mm["revenue_month"]
    print(f"  Выручка/мес: low {fmt(rv['low'])} · base {fmt(rv['base'])} · high {fmt(rv['high'])}; "
          f"CR3 {mm['cr'][3]:.0%}, HHI {fmt(mm['hhi_brand'])}, Amazon Retail {mm['amazon_retail_share']:.0%}, "
          f"медиана отзывов TOP10 {fmt(mm['review_median_top10'])}")
    if mm.get("badge_check"):
        b = mm["badge_check"]
        print(f"  Бейдж Amazon vs Helium: в интервале {b['in_band']:.0%}, Helium выше {b['helium_above_badge']:.0%}; "
              f"выручка в согласии с бейджем {fmt(b['revenue_badge_consistent'])}, расхождение {b['divergence']:.0%}")
km = imp.get("keyword_metrics")
if km:
    print(f"  Ключи: {km['keywords']}, объём {fmt(km['search_volume_total'])}, небрендовые "
          f"{km['nonbranded_share']:.0%}, тренд {km['trend_weighted']:+.0%}")

ROW = "{:<22} {:<11} {:<5} {:<5} {:>5} {:>5} {:>7} {:>8} {:>9} {:>9}  {}"
print()
print(ROW.format("Гипотеза", "Статус", "R", "Conf", "Score", "ASIN", "Цена", "Contr/ед", "Капитал",
                 "E[П 12м]", "Доказательность"))
for t in res["summary"]:
    print(ROW.format(
        t["id"][:22], t["status"][:11], t["rule"] or "", (t["confidence"] or "")[:5], fmt(t["score"], 1),
        fmt(t["asins"]), fmt(t.get("price"), 2), fmt(t.get("post_ad_contribution"), 2),
        fmt(t.get("required_capital")), fmt(t.get("expected_profit_12m")), t.get("evidence") or ""))
    if t.get("missing"):
        print("    не хватает:", ", ".join(t["missing"]))

for r in res["results"]:
    ev = r["evidence"]
    if r["package"] is None:
        print(f"\n[{r['id']}] {r['name']}: WHITE SPACE — {ev['checks'][0]['detail']}")
        continue
    d = r["package"]["decision"]
    print(f"\n[{r['id']}] {r['name']}: {d['status']} ({d.get('rule_fired')}), доказательность {ev['status']}")
    for c in ev["checks"]:
        print(f"   {'✓' if c['passed'] else '✗'} {c['check']}: {c['detail']}")
    reasons = d.get("reasons", [])
    review = [x for x in reasons if x.endswith("REVIEW REQUIRED")]
    for x in reasons:
        if x not in review:
            print("   -", x)
    if review:
        print(f"   - compliance без подтверждения: {len(review)} пунктов")
    if d.get("conditional_after_fix"):
        print("   после устранения:", d["conditional_after_fix"])

pf = res["portfolio"]
t1 = pf["wave_1_totals"]
print("\n=== Портфель (§13) ===")
if pf["wave_1"]:
    print(f"Волна 1: {', '.join(pf['wave_1'])} — капитал {fmt(t1['required_capital'])}, "
          f"E[П 12м] {fmt(t1['expected_profit_12m'])}, стартовый запас {fmt(t1['initial_units'])} шт.")
else:
    print("Волна 1: пусто — запускать нечего")
if pf["target_met"] is not None:
    print(f"Цель по прибыли {fmt(pf['target_profit_12m'])}: {'достигнута' if pf['target_met'] else 'не достигнута'}")
for x in pf["wave_2"]:
    print(f"Волна 2: {x['id']} — {x['reason']}")
af = pf["after_fix"]
if af["candidates"]:
    print(f"После устранения препятствий: план {', '.join(af['plan']) or 'пусто'}")
    for c in af["candidates"]:
        print(f"   {c['id']}: станет {c['decision_after_fix']}, доказательность {c['evidence']}")
for x in pf["rejected"]:
    print(f"Отклонено: {x['id']} — {x['reason']} (доказательность {x['evidence']})")
for c in pf["cannibalization"]:
    print(f"Каннибализация: {c['a']} ↔ {c['b']} (ключи {c['keywords']:.0%}, ASIN {c['asins']:.0%})")
for hid, rs in pf["risks"].items():
    for x in rs:
        print(f"Риск {hid}: {x}")

print("\nПредупреждения по данным:")
for w in niche.get("warnings", []):
    print("  !", w)

out = Path(path).with_suffix(".result.json")
out.write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(f"\nПолный результат: {out}")
want_pdf = "--pdf" in sys.argv
rep = write_report(res, str(Path(path).with_suffix(".report.html")), pdf=want_pdf)
print(f"Отчёт: {rep['html']}" + (f", PDF: {rep['pdf']}" if rep["pdf"]
                                 else (" (PDF не создан: нет Edge/Chrome)" if want_pdf else "")))
if rep["audit"]:
    print(f"Валидатор отклонил предложений: {len(rep['audit'])}")
