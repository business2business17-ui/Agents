"""Определение ниши и рыночные метрики из Helium 10 Xray / Cerebro (ТЗ v1.2 §3, §4, §5.2, §18).

Цепочка: строки Xray → контроль качества (§18) → правило включения (§3.1) →
метрики ниши (§3.2, §14) → вход для pipeline.analyze().

Что честно НЕ выводится из этих выгрузок и остаётся на пользователе/других источниках:
fee schedule и НДС, COGS, CPC (в Cerebro его нет), доля клика и CVR нового бренда,
сезонность и тренд 12 мес. (нужен Keepa), выбывшие ASIN для когорт.
"""
from __future__ import annotations

import copy
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date

from .categories import DEFAULTS_VERSION, compliance_category, default_referral, detect_category
from .importers.helium10 import badge_bounds

XRAY_ROW_CAP = 100            # экспорт Xray категории обрезается на 100 строк
PRICE_ANOMALY = 0.5           # |цена/(выручка/шт.) − 1| выше — помечаем расхождение
PRICE_X100_BAND = (60, 160)   # цена/(выручка/шт.) в этом коридоре — цена в центах/пенсах


# ---------------------------------------------------------------- контроль качества (§18)

@dataclass
class QualityReport:
    rows_in: int
    issues: list = field(default_factory=list)       # {"asin", "issue", "detail"}
    price_fixed: int = 0
    price_gap: int = 0
    no_estimate: int = 0

    def add(self, asin, issue, detail):
        self.issues.append({"asin": asin, "issue": issue, "detail": detail})


def clean_rows(rows: list) -> tuple:
    """→ (строки, QualityReport).

    - цена ≈ ×100 к выручке/шт. (в части экспортов цена приходит в центах/пенсах) → цена / 100;
    - цены нет → выручка/шт.;
    - иное расхождение (акция, смена цены за месяц) — не исправляется, только помечается:
      текущая цена и средняя цена продажи законно отличаются."""
    q = QualityReport(len(rows))
    out = []
    for r in copy.deepcopy(rows):
        if r.units is None or r.revenue is None:
            q.no_estimate += 1
            q.add(r.asin, "no_sales_estimate", "Нет оценки продаж/выручки")
        elif r.units > 0:
            asp = r.revenue / r.units
            ratio = r.price / asp if r.price else None
            if ratio is None:
                r.price = round(asp, 2)
                q.price_fixed += 1
                q.add(r.asin, "price_missing", f"Цены нет; взята выручка/шт. {asp:.2f}")
            elif PRICE_X100_BAND[0] <= ratio <= PRICE_X100_BAND[1]:
                q.add(r.asin, "price_x100", f"Цена {r.price} ≈ ×100 к выручке/шт. {asp:.2f}; цена / 100")
                r.price = round(r.price / 100, 2)
                q.price_fixed += 1
            elif abs(ratio - 1) > PRICE_ANOMALY:
                q.price_gap += 1
                q.add(r.asin, "price_asp_gap",
                      f"Текущая цена {r.price} отличается от выручки/шт. {asp:.2f} (×{ratio:.1f}): "
                      "акция или смена цены; не исправлено")
        out.append(r)
    return out, q


# ---------------------------------------------------------------- определение ниши (§3.1)

@dataclass
class NicheDefinition:
    niche_id: str
    version: int = 1
    include_any: list = field(default_factory=list)     # слова/фразы в title (любое)
    exclude_any: list = field(default_factory=list)     # исключающие слова в title
    price_min: float | None = None
    price_max: float | None = None
    exclude_asins: dict = field(default_factory=dict)   # ASIN → причина (ручное/LLM-исключение)
    include_asins: list = field(default_factory=list)   # принудительно включить
    relevance: dict = field(default_factory=dict)       # ASIN → relevant|adjacent|irrelevant (LLM, §3.1 п.3)

    @property
    def definition_id(self) -> str:
        return f"{self.niche_id}@v{self.version}"

    @classmethod
    def from_dict(cls, d: dict) -> "NicheDefinition":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def apply(self, rows: list) -> tuple:
        """→ (включённые, исключённые [{asin, title, reason}], пограничные adjacent)."""
        inc_rx = _terms_rx(self.include_any)
        exc_rx = _terms_rx(self.exclude_any)
        included, excluded, adjacent = [], [], []
        for r in rows:
            reason = None
            if r.asin in self.include_asins:
                pass
            elif r.asin in self.exclude_asins:
                reason = f"manual: {self.exclude_asins[r.asin]}"
            elif self.relevance.get(r.asin) == "irrelevant":
                reason = "llm: irrelevant"
            elif inc_rx and not inc_rx.search(r.title):
                reason = "нет ни одного include-слова в title"
            elif exc_rx and (m := exc_rx.search(r.title)):
                reason = f"exclude-слово «{m.group(0)}»"
            elif self.price_min is not None and (r.price or 0) < self.price_min:
                reason = f"цена {r.price} < {self.price_min}"
            elif self.price_max is not None and (r.price or 0) > self.price_max:
                reason = f"цена {r.price} > {self.price_max}"
            if reason:
                excluded.append({"asin": r.asin, "title": r.title[:80], "reason": reason})
                continue
            if self.relevance.get(r.asin) == "adjacent":
                adjacent.append(r)
            included.append(r)
        return included, excluded, adjacent

    def as_dict(self) -> dict:
        return {"niche_definition_id": self.definition_id, **{k: getattr(self, k) for k in (
            "include_any", "exclude_any", "price_min", "price_max", "exclude_asins", "include_asins")}}


def _terms_rx(terms, word_start: bool = True):
    """word_start=True — термин с начала слова (title); False — подстрока, для немецких
    составных слов в ключах («bräunungsbeschleuniger» ловится по «beschleuniger»)."""
    terms = [t for t in terms if t]
    if not terms:
        return None
    pre = r"\b" if word_start else ""
    return re.compile("|".join(rf"{pre}{re.escape(t)}" for t in terms), re.IGNORECASE)


# ---------------------------------------------------------------- метрики ниши (§3.2, §4, §14)

def _pct(values, p):
    v = sorted(values)
    if not v:
        return None
    k = (len(v) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def _shares(rows, key):
    """Доли по числу ASIN, штукам и выручке для группировки key(row)."""
    out = {}
    tot_n = len(rows)
    tot_u = sum(r.units or 0 for r in rows) or 1
    tot_r = sum(r.revenue or 0 for r in rows) or 1
    groups = defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    for g, rs in groups.items():
        out[g] = {"asins": len(rs) / tot_n, "units": sum(r.units or 0 for r in rs) / tot_u,
                  "revenue": sum(r.revenue or 0 for r in rs) / tot_r}
    return out


def _brand_key(b: str) -> str:
    return re.sub(r"[^a-z0-9]", "", b.lower())


def market_metrics(rows: list, as_of: date, rows_exported: int | None = None,
                   cohort_age_months=(3, 18)) -> dict:
    """Метрики по включённым ASIN. rows_exported — сколько строк было в выгрузке до фильтра
    (для предупреждения об обрезке на XRAY_ROW_CAP)."""
    est = [r for r in rows if r.units is not None and r.revenue is not None]
    warnings = []
    if not est:
        raise ValueError("Нет ни одного ASIN с оценкой продаж")
    units = sum(r.units for r in est)
    revenue = sum(r.revenue for r in est)

    # Бейдж Amazon «X+ bought» — наблюдаемая нижняя граница; low/high по нему, base — Helium.
    lo_rev = hi_rev = capped_rev = 0.0
    in_band = under = over = badge_rev = 0.0
    for r in est:
        asp = r.revenue / r.units if r.units else (r.price or 0)
        b = badge_bounds(r.badge_floor)
        if b is None:
            lo_rev += r.revenue
            hi_rev += r.revenue
            capped_rev += r.revenue
            continue
        floor, nxt = b
        lo_rev += min(r.units, floor) * asp
        hi_rev += max(r.units, floor) * asp
        # оценка Helium, зажатая в интервал бейджа: второй источник для расхождения (§3.3)
        capped_rev += min(max(r.units, floor), nxt - 1 if nxt is not None else r.units) * asp
        badge_rev += r.revenue
        if r.units < floor:
            under += r.revenue
        elif nxt is not None and r.units >= nxt:
            over += r.revenue
        else:
            in_band += r.revenue
    badge = None
    if badge_rev:
        badge = {"revenue_share_with_badge": badge_rev / revenue, "in_band": in_band / badge_rev,
                 "helium_below_badge": under / badge_rev, "helium_above_badge": over / badge_rev,
                 "revenue_badge_consistent": capped_rev,
                 # div = |A − B| / min(A, B), как в §3.3
                 "divergence": abs(revenue - capped_rev) / min(revenue, capped_rev) if capped_rev else None}
        if badge["in_band"] < 0.5:
            warnings.append(f"Оценки Helium попадают в интервал бейджа Amazon только для "
                            f"{badge['in_band']:.0%} выручки (ниже бейджа {badge['helium_below_badge']:.0%}, "
                            f"выше {badge['helium_above_badge']:.0%}).")

    # Концентрация по брендам
    by_brand = Counter()
    for r in est:
        by_brand[_brand_key(r.brand) or r.asin] += r.revenue
    shares = sorted((v / revenue for v in by_brand.values()), reverse=True)
    cr = {n: sum(shares[:n]) for n in (3, 5, 10)}
    hhi = sum((s * 100) ** 2 for s in shares)

    top10 = sorted(est, key=lambda r: -r.revenue)[:10]
    prices = [r.price for r in est if r.price]
    amazon_rev = sum(r.revenue for r in est if r.is_amazon_retail)

    # Когорта новых входов (§5.2): только выжившие в выгрузке → survival bias
    lo_m, hi_m = cohort_age_months
    cohort = [r.units for r in est if r.created and lo_m <= _months_between(r.created, as_of) <= hi_m]

    if rows_exported is not None and rows_exported >= XRAY_ROW_CAP:
        warnings.append(f"Выгрузка Xray обрезана на {XRAY_ROW_CAP} ASIN: выручка ниши — нижняя граница, "
                        "хвост ниши не виден.")
    coverage = len(est) / len(rows)

    return {
        "asins": len(rows), "asins_with_estimate": len(est),
        "brands": len(by_brand), "sellers": len({r.seller or r.buy_box for r in est}),
        "units_month": units, "revenue_month": {"low": lo_rev, "base": revenue, "high": hi_rev},
        "badge_check": badge,
        "price": {"min": min(prices), "max": max(prices), "median": statistics.median(prices),
                  "p10": _pct(prices, 0.10), "p90": _pct(prices, 0.90), "asp_unit_weighted": revenue / units},
        "cr": cr, "hhi_brand": hhi,
        "top_brands": [{"brand": b, "revenue_share": v / revenue} for b, v in by_brand.most_common(10)],
        "amazon_retail_share": amazon_rev / revenue,
        "fulfillment_shares": _shares(est, lambda r: r.fulfillment),
        "review_median_top10": statistics.median([r.reviews or 0 for r in top10]),
        "rating_median": statistics.median([r.rating for r in est if r.rating] or [0]),
        "coverage_by_count": coverage,
        "cohort": {"age_months": list(cohort_age_months), "units_at_month": cohort, "survivors_only": True},
        "reference": _reference(top10),
        "warnings": warnings,
    }


def _months_between(d0: date, d1: date) -> float:
    return (d1 - d0).days / 30.44


def _reference(top10):
    """Габариты/вес/комиссии эталонных конкурентов (для FBA fee, §15.1)."""
    tiers = Counter(r.size_tier for r in top10 if r.size_tier and r.size_tier != "N/A")
    w = [r.weight_kg for r in top10 if r.weight_kg]
    return {"size_tier_mode": tiers.most_common(1)[0][0] if tiers else None,
            "weight_kg_median": statistics.median(w) if w else None,
            "rows": [{"asin": r.asin, "price": r.price, "fees": r.fees, "size_tier": r.size_tier,
                      "weight_kg": r.weight_kg, "dimensions_cm": r.dimensions_cm} for r in top10]}


def estimate_fulfillment_fee(rows: list, referral_fee) -> float | None:
    """FBA fee ≈ медиана(Fees − referral(цена)) по эталонным ASIN с FBA/AMZ.
    referral_fee: функция gross_price → комиссия (economics.ReferralRule.fee)."""
    vals = [r.fees - referral_fee(r.price) for r in rows
            if r.fees is not None and r.price and r.fulfillment in ("FBA", "AMZ")]
    vals = [v for v in vals if v > 0]
    return round(statistics.median(vals), 2) if vals else None


# ---------------------------------------------------------------- ключи (§8)

def brand_tokens(rows: list) -> set:
    toks = set()
    for r in rows:
        b = r.brand.lower().strip()
        if len(b) >= 3:
            toks.add(b)
            first = re.split(r"[\s\-&']+", b)[0]
            if len(first) >= 4:
                toks.add(first)
    return toks


def keyword_metrics(keywords: list, brands: set) -> dict:
    """Доля небрендового спроса (по search volume), объём и средневзвешенный тренд."""
    def is_branded(p):
        return any(re.search(rf"\b{re.escape(b)}\b", p) for b in brands)

    kw = [k for k in keywords if k.search_volume]
    total = sum(k.search_volume for k in kw)
    branded = sum(k.search_volume for k in kw if is_branded(k.phrase))
    tr = [(k.trend, k.search_volume) for k in kw if k.trend is not None]
    return {"keywords": len(kw), "search_volume_total": total,
            "nonbranded_share": (total - branded) / total if total else None,
            "trend_weighted": sum(t * v for t, v in tr) / sum(v for _, v in tr) / 100 if tr else None,
            "branded_keywords": sorted(k.phrase for k in kw if is_branded(k.phrase))[:30]}


def build_clusters(keywords: list, brands: set, cluster_terms: dict, assumptions: dict) -> tuple:
    """Небрендовые ключи → непересекающиеся кластеры (первое совпадение по порядку cluster_terms).

    cluster_terms: {cluster_id: [термины]}; assumptions: {"click_share": {low,base,high},
    "cvr": {low,base,high}} — доля клика и CVR нового бренда (гипотезы пользователя).
    → (clusters для pipeline, нераспределённые ключи)."""
    rx = {cid: _terms_rx(terms, word_start=False) for cid, terms in cluster_terms.items()}
    buckets = {cid: [] for cid in cluster_terms}
    rest = []
    for k in keywords:
        if not k.search_volume or any(re.search(rf"\b{re.escape(b)}\b", k.phrase) for b in brands):
            continue
        cid = next((c for c, r in rx.items() if r and r.search(k.phrase)), None)
        (buckets[cid] if cid else rest).append(k)
    clusters = []
    for cid, ks in buckets.items():
        if not ks:
            continue
        a = assumptions.get(cid, assumptions)
        clusters.append({"cluster_id": cid, "keywords": [k.phrase for k in ks],
                         "search_volume_month": sum(k.search_volume for k in ks),
                         "click_share": a["click_share"], "cvr": a["cvr"]})
    return clusters, [k.phrase for k in rest]


# ---------------------------------------------------------------- вход для pipeline

class EmptyNicheError(ValueError):
    """Правило включения не оставило ни одного ASIN: спроса на такой продукт в выгрузке не видно."""


def niche_rows(definition: NicheDefinition, xray_rows: list) -> tuple:
    """Контроль качества + правило включения → (включённые, исключённые, adjacent, QualityReport)."""
    cleaned, quality = clean_rows(xray_rows)
    included, excluded, adjacent = definition.apply(cleaned)
    return included, excluded, adjacent, quality


def build_input(definition: NicheDefinition, xray_rows: list, user: dict,
                keywords: list | None = None, as_of: date | None = None,
                sources: list | None = None) -> dict:
    """Сводит выгрузки и пользовательские параметры во вход pipeline.analyze().

    user: всё, чего нет в выгрузках (tax, fees, costs, ppc, scenarios, launch, budget,
    compliance, claims, keyword_clusters, keyword_assumptions, business_model, category).
    Явно заданные пользователем ключи market.* перекрывают вычисленные."""
    as_of = as_of or date.today()
    included, excluded, adjacent, quality = niche_rows(definition, xray_rows)
    if not included:
        raise EmptyNicheError("Определение ниши не оставило ни одного ASIN")
    mm = market_metrics(included, as_of, rows_exported=len(xray_rows))
    mps = {r.marketplace for r in included}
    curs = {r.currency for r in included}
    if len(mps) != 1 or len(curs) != 1:
        raise ValueError(f"Смешаны marketplace/валюты в одной нише: {mps} {curs}")

    inp = copy.deepcopy({k: v for k, v in user.items()
                         if k not in ("keyword_clusters", "keyword_assumptions", "keyword_clusters_only",
                                      "market")})
    inp.setdefault("marketplace", mps.pop())
    inp.setdefault("currency", curs.pop())
    inp["niche_definition_id"] = definition.definition_id
    inp["data_as_of"] = as_of.isoformat()

    # Категория: из выгрузки, если пользователь не задал; ведёт compliance, claims и стартовый referral
    cat_key, cat_share, cat_all = detect_category([r.category for r in included])
    category_warnings = []
    if "category" not in user:
        inp["category"] = compliance_category(cat_key)
        if cat_key == "other":
            category_warnings.append("Категория не распознана по колонке Category: compliance только общий, "
                                     "задайте category явно.")
    if cat_share and cat_share < 0.8:
        category_warnings.append(f"В нише смешаны категории Amazon {cat_all}: проверьте определение ниши.")
    if isinstance(inp.get("fees"), dict) and not inp["fees"].get("referral"):
        ref = default_referral(cat_key, inp["marketplace"])
        if ref:
            inp["fees"]["referral"] = ref
            inp["fees"].setdefault("schedule_version", DEFAULTS_VERSION)
            category_warnings.append(f"Referral — стартовая ставка категории {cat_key} ({DEFAULTS_VERSION}), "
                                     "не сверенная fee schedule.")

    km = None
    market = {
        "niche_revenue_month": mm["revenue_month"],
        "price_range": [round(mm["price"]["p10"], 2), round(mm["price"]["p90"], 2)],
        "coverage": mm["coverage_by_count"],
        # второй источник — бейдж Amazon «X+ bought», если он есть у большей части выручки
        "source_divergence": (mm["badge_check"]["divergence"]
                              if mm["badge_check"] and mm["badge_check"]["revenue_share_with_badge"] >= 0.5
                              else None),
        "observed_at": as_of.isoformat(),
        "seasonality_source": "none",
        "review_median_top10": mm["review_median_top10"],
        "hhi_brand": mm["hhi_brand"],
        "amazon_retail_share": mm["amazon_retail_share"],
    }
    if keywords:
        km = keyword_metrics(keywords, brand_tokens(included))
        market["nonbranded_share"] = km["nonbranded_share"]
        if user.get("keyword_clusters") and user.get("keyword_assumptions"):
            terms = user["keyword_clusters"]
            only = user.get("keyword_clusters_only")       # гипотеза берёт только свои кластеры
            clusters, rest = build_clusters(keywords, brand_tokens(included), terms,
                                            user["keyword_assumptions"])
            if only:
                clusters = [c for c in clusters if c["cluster_id"] in only]
            inp["keywords"] = {"clusters": clusters, "unassigned": rest}
    market.update(user.get("market", {}))
    inp["market"] = market

    if mm["cohort"]["units_at_month"] and "cohort" not in user:
        inp["cohort"] = {"units_at_month": mm["cohort"]["units_at_month"], "exited_count": 0}

    fba_fee = None
    if isinstance(inp.get("fees"), dict) and inp["fees"].get("fulfillment_fee") is None \
            and inp["fees"].get("referral"):
        from .economics import ReferralRule
        rule = ReferralRule.from_dict(inp["fees"]["referral"])
        fee = estimate_fulfillment_fee(sorted(included, key=lambda r: -(r.revenue or 0))[:10], rule.fee)
        if fee is not None:
            fba_fee = fee
            inp["fees"]["fulfillment_fee"] = fee
            inp["fees"]["fulfillment_fee_source"] = "xray_estimate: медиана(Fees − referral) по топ-10"

    warnings = list(mm["warnings"]) + category_warnings
    if quality.price_fixed:
        warnings.append(f"Цена исправлена у {quality.price_fixed} ASIN (в центах ×100 или отсутствует).")
    if quality.price_gap:
        warnings.append(f"Текущая цена заметно отличается от выручки/шт. у {quality.price_gap} ASIN "
                        "(акции/смена цены): ценовые сегменты по текущей цене менее надёжны.")
    if mm["cohort"]["units_at_month"]:
        warnings.append("Когорта новых ASIN — только выжившие в выгрузке (выбывшие неизвестны): "
                        "доля успешных входов завышена.")
    if keywords and not inp.get("keywords"):
        warnings.append("Кластеры ключей не построены: нужны keyword_clusters и keyword_assumptions "
                        "(доля клика и CVR нового бренда).")
    inp["_import"] = {
        "sources": sources or [],
        "niche_definition": definition.as_dict(),
        "category": {"detected": cat_key, "share": cat_share, "all": cat_all, "used": inp.get("category")},
        "included": len(included), "excluded": excluded,
        "adjacent_for_review": [r.asin for r in adjacent],
        "quality": {"rows_in": quality.rows_in, "price_fixed": quality.price_fixed,
                    "no_estimate": quality.no_estimate, "issues": quality.issues},
        "market_metrics": mm, "keyword_metrics": km, "fba_fee_estimate": fba_fee,
        "keyword_clusters": [{"cluster_id": c["cluster_id"], "keywords": len(c["keywords"]),
                              "search_volume_month": c["search_volume_month"]}
                             for c in inp.get("keywords", {}).get("clusters", [])],
        "warnings": warnings,
    }
    return inp
