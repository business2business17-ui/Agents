"""Скрининг папки выгрузок Xray: сравнимые метрики по всем категориям/нишам (ТЗ v1.2 §14).

Это не решение (для решения нужны COGS, CPC и прочее — xray_run), а быстрый отбор:
размер, концентрация, барьер отзывов, доля Amazon, доля новых ASIN, согласие Helium с
бейджем Amazon, качество данных. Одинаковые выгрузки (тот же набор ASIN) помечаются дублями.
"""
from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

from .categories import detect_category
from .importers import read_xray
from .niche import clean_rows, market_metrics

NEW_ASIN_MONTHS = 18


def scan_file(path: str, as_of: date) -> dict:
    rows = read_xray(path)
    cleaned, q = clean_rows(rows)
    mm = market_metrics(cleaned, as_of, rows_exported=len(rows))
    cat, share, _ = detect_category([r.category for r in rows])
    est = [r for r in cleaned if r.revenue is not None]
    new = [r for r in est if r.created and (as_of - r.created).days / 30.44 <= NEW_ASIN_MONTHS]
    revenue = mm["revenue_month"]["base"]
    b = mm["badge_check"] or {}
    return {
        "file": Path(path).name, "marketplace": rows[0].marketplace, "currency": rows[0].currency,
        "category": cat, "category_share": share, "asins": len(rows),
        "revenue_base": revenue, "revenue_badge_consistent": b.get("revenue_badge_consistent"),
        "badge_divergence": b.get("divergence"), "badge_in_band": b.get("in_band"),
        "cr3": mm["cr"][3], "hhi_brand": mm["hhi_brand"], "amazon_retail_share": mm["amazon_retail_share"],
        "review_median_top10": mm["review_median_top10"], "price_p10": mm["price"]["p10"],
        "price_p90": mm["price"]["p90"], "asp": mm["price"]["asp_unit_weighted"],
        "new_asins": len(new), "new_asins_revenue_share": sum(r.revenue for r in new) / revenue if revenue else None,
        "price_fixed": q.price_fixed, "price_gap": q.price_gap,
        "asin_fingerprint": hashlib.sha1(",".join(sorted(r.asin for r in rows)).encode()).hexdigest()[:12],
        "warnings": mm["warnings"],
    }


def scan_folder(folder: str, as_of: date | None = None, pattern: str = "*xray*.xlsx") -> list:
    as_of = as_of or date.today()
    patterns = dict.fromkeys([pattern, pattern.replace(".xlsx", ".csv")])     # xlsx и csv-вариант, без повторов
    files = sorted({f for p in patterns for f in Path(folder).glob(p)})
    out, seen = [], {}
    for f in files:
        try:
            res = scan_file(str(f), as_of)
        except ValueError as exc:            # не Xray или пустая выгрузка
            out.append({"file": f.name, "error": str(exc)})
            continue
        fp = res["asin_fingerprint"]
        res["duplicate_of"] = seen.get(fp)
        seen.setdefault(fp, res["file"])
        out.append(res)
    return out
