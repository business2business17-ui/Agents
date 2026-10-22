"""Запуск: python examples/scan_xray.py XRAY [2026-10-20]"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mia.scan import scan_folder  # noqa: E402

folder = sys.argv[1] if len(sys.argv) > 1 else "XRAY"
as_of = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()
res = scan_folder(folder, as_of)


def pct(v):
    return "—" if v is None else f"{v:.0%}"


def num(v):
    return "—" if v is None else f"{v:,.0f}".replace(",", " ")


print(f"{'Файл':36} {'MP':3} {'Категория':12} {'Выручка':>10} {'По бейджу':>10} {'Расх':>5} {'CR3':>4} "
      f"{'HHI':>5} {'AMZ':>4} {'Отз.T10':>7} {'Цена P10–P90':>13} {'Новые':>6} {'Цены':>5}")
for r in res:
    if "error" in r:
        print(f"{r['file'][:36]:36} ошибка: {r['error']}")
        continue
    dup = f"  = дубль {r['duplicate_of']}" if r["duplicate_of"] else ""
    print(f"{r['file'][:36]:36} {r['marketplace']:3} {r['category'][:12]:12} {num(r['revenue_base']):>10} "
          f"{num(r['revenue_badge_consistent']):>10} {pct(r['badge_divergence']):>5} {pct(r['cr3']):>4} "
          f"{num(r['hhi_brand']):>5} {pct(r['amazon_retail_share']):>4} {num(r['review_median_top10']):>7} "
          f"{r['price_p10']:>6.2f}–{r['price_p90']:<6.2f} {pct(r['new_asins_revenue_share']):>6} "
          f"{r['price_fixed'] + r['price_gap']:>5}{dup}")
print("\nРасх — расхождение оценки Helium с бейджем Amazon «X+ bought» (§3.3); Новые — доля выручки ASIN "
      "моложе 18 мес. (только выжившие в выгрузке); Цены — исправленные + помеченные цены.")
out = Path(folder) / f"scan_{as_of.isoformat()}.json"
out.write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(f"Полный результат: {out}")
