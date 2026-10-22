"""Buy Box Engine для модели Resale (ТЗ v1.2 §5.3).

Закрывает проблему P4: при перепродаже продажи определяются долей Buy Box на
существующем ASIN, а не долей ниши. Равное деление Buy Box — гипотеза-заглушка,
которая заменяется калибровкой по собственным данным (bb_share_high_override / Phase 3).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config
from .contestable import ScenarioValues, RANGES


@dataclass(frozen=True)
class Offer:
    seller_id: str
    price: float
    is_fba: bool = False
    is_amazon: bool = False
    is_prime_fbm: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "Offer":
        return cls(str(d["seller_id"]), float(d["price"]), bool(d.get("is_fba", False)),
                   bool(d.get("is_amazon", False)), bool(d.get("is_prime_fbm", False)))


@dataclass
class BuyBoxResult:
    asin: str
    n_offers: int
    n_competitive: int
    amazon_present: bool
    bb_share: ScenarioValues
    units: ScenarioValues
    hard_stops: list = field(default_factory=list)    # → NO-GO
    reviews: list = field(default_factory=list)       # → REVIEW REQUIRED (HOLD)
    caps: list = field(default_factory=list)          # → решение не выше HOLD
    notes: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"asin": self.asin, "n_offers": self.n_offers, "n_competitive": self.n_competitive,
                "amazon_present": self.amazon_present, "bb_share": self.bb_share.as_dict(),
                "units": self.units.as_dict(), "hard_stops": self.hard_stops,
                "reviews": self.reviews, "caps": self.caps, "notes": self.notes}


def buybox_analysis(asin: str, offers: list, buy_box_price: float, asin_units: ScenarioValues,
                    cfg: Config, our_seller_id: str | None = None, new_sellers_90d: int = 0,
                    amazon_bb_share: float | None = None, bb_share_high_override: float | None = None,
                    has_resale_authorization: bool | None = None, brand_ip_complaints: bool = False,
                    bb_price_below_mvp_share: float | None = None) -> BuyBoxResult:
    others = [o for o in offers if o.seller_id != our_seller_id]
    limit = buy_box_price * (1 + cfg.bb_competitive_price_band)
    competitive = [o for o in others
                   if (o.is_fba or o.is_amazon or o.is_prime_fbm) and o.price <= limit]
    n = len(competitive)
    amazon_present = any(o.is_amazon for o in others)

    base = 1 / (n + 1)
    low = 1 / (n + 1 + max(new_sellers_90d, 0))
    notes = []
    if bb_share_high_override is not None:
        high = bb_share_high_override
    else:
        high = base
        notes.append("bb_share.high = base: нет калибровки по собственным данным.")
    notes.append("Равное деление Buy Box — гипотеза до калибровки (§5.3).")
    share = ScenarioValues(low, base, high)

    res = BuyBoxResult(asin, len(others), n, amazon_present, share,
                       ScenarioValues(*[asin_units.get(r) * share.get(r) for r in RANGES]),
                       notes=notes)

    if amazon_bb_share is not None and amazon_bb_share >= cfg.amazon_bb_dominance:
        res.hard_stops.append(
            f"Amazon Retail держит Buy Box {amazon_bb_share:.0%} времени (порог {cfg.amazon_bb_dominance:.0%}).")
    elif amazon_present and amazon_bb_share is None:
        res.caps.append("Amazon Retail присутствует, история его доли Buy Box неизвестна.")
    if bb_price_below_mvp_share is not None and bb_price_below_mvp_share > cfg.bb_below_mvp_max_share:
        res.hard_stops.append(
            f"Цена Buy Box ниже минимально жизнеспособной {bb_price_below_mvp_share:.0%} периода.")
    if has_resale_authorization is not True:
        res.reviews.append("Нет документального подтверждения права перепродажи (авторизация/инвойсы).")
    if brand_ip_complaints:
        res.caps.append("Бренд известен IP-жалобами против перепродавцов.")
    return res
