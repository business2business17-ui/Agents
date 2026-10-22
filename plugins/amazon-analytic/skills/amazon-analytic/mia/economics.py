"""Юнит-экономика с явной налоговой базой (ТЗ v1.2 §10, §11.1, §11.2, §11.5).

Закрывает проблему P6: однозначные формулы pre/post-ad contribution,
break-even ACoS в net- и console-базе, база referral fee, break-even units.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from datetime import date


# ---------------------------------------------------------------- налоговая база

@dataclass(frozen=True)
class TaxContext:
    """vat_rate берётся из версионированной таблицы vat_rates, а не из памяти."""
    marketplace: str
    vat_rate: float
    price_includes_vat: bool

    @classmethod
    def from_dict(cls, marketplace: str, d: dict) -> "TaxContext":
        return cls(marketplace, float(d["vat_rate"]), bool(d["price_includes_vat"]))

    def net_of_tax(self, gross: float) -> float:
        """EU/UK: витринная цена включает НДС. US: sales tax собирает Amazon, цена = net."""
        return gross / (1 + self.vat_rate) if self.price_includes_vat else gross


# ---------------------------------------------------------------- комиссии

@dataclass(frozen=True)
class ReferralRule:
    """Referral fee считается от итоговой цены продажи (в EU — с НДС).

    kind="whole":    вся цена по ставке того уровня, в который она попала (напр. 8 % до порога, 15 % выше).
    kind="marginal": ставка применяется к части цены внутри каждого уровня.
    tiers: [(upper_bound | None, rate), ...] по возрастанию; None — без верхней границы.
    """
    kind: str
    tiers: tuple
    min_fee: float = 0.0

    @classmethod
    def from_dict(cls, d: dict) -> "ReferralRule":
        if d["kind"] not in ("whole", "marginal"):
            raise ValueError(f"unknown referral kind: {d['kind']}")
        tiers = tuple((None if u is None else float(u), float(r)) for u, r in d["tiers"])
        if tiers[-1][0] is not None:
            raise ValueError("last referral tier must have upper bound null")
        return cls(d["kind"], tiers, float(d.get("min_fee", 0.0)))

    def fee(self, gross_price: float) -> float:
        if self.kind == "whole":
            for upper, rate in self.tiers:
                if upper is None or gross_price <= upper:
                    fee = gross_price * rate
                    break
        else:
            fee, lower = 0.0, 0.0
            for upper, rate in self.tiers:
                top = gross_price if upper is None else min(gross_price, upper)
                if top > lower:
                    fee += (top - lower) * rate
                if upper is None or gross_price <= upper:
                    break
                lower = upper
        return max(fee, self.min_fee)


@dataclass(frozen=True)
class FeeSchedule:
    referral: ReferralRule
    fulfillment_fee: float          # FBA/FBM fulfillment на единицу для данного size tier
    storage_per_unit: float = 0.0   # хранение, приведённое к проданной единице
    other_amazon_fees: float = 0.0  # inbound placement, low-inventory и т. п. на единицу
    return_processing_fee: float = 0.0
    schedule_version: str = "unknown"
    checked_at: str | None = None   # ISO-дата последней сверки с официальным источником

    @classmethod
    def from_dict(cls, d: dict) -> "FeeSchedule":
        return cls(
            referral=ReferralRule.from_dict(d["referral"]),
            fulfillment_fee=float(d["fulfillment_fee"]),
            storage_per_unit=float(d.get("storage_per_unit", 0.0)),
            other_amazon_fees=float(d.get("other_amazon_fees", 0.0)),
            return_processing_fee=float(d.get("return_processing_fee", 0.0)),
            schedule_version=d.get("schedule_version", "unknown"),
            checked_at=d.get("checked_at"),
        )

    def age_days(self, as_of: date) -> int | None:
        if not self.checked_at:
            return None
        return (as_of - date.fromisoformat(self.checked_at)).days


# ---------------------------------------------------------------- себестоимость

@dataclass(frozen=True)
class UnitCosts:
    cogs: float
    cogs_status: str = "supplier_quote"     # supplier_quote | user_estimate | assumed
    inbound_freight: float = 0.0
    prep: float = 0.0
    duties: float = 0.0
    non_recoverable_taxes: float = 0.0
    other_variable: float = 0.0             # платёжные и прочие переменные расходы на единицу
    coupon_gross: float = 0.0               # скидки/купоны за счёт продавца, на единицу, в gross-цене
    return_rate: float = 0.0
    unsellable_share: float = 0.0           # доля возвратов, которые нельзя перепродать
    lost_fees_per_return: float | None = None  # невозвращаемые комиссии на возврат; None → fulfillment fee

    @classmethod
    def from_dict(cls, d: dict) -> "UnitCosts":
        allowed = cls.__dataclass_fields__.keys()
        unknown = set(d) - set(allowed)
        if unknown:
            raise ValueError(f"unknown cost fields: {sorted(unknown)}")
        return cls(**d)

    @property
    def landed_cogs(self) -> float:
        return self.cogs + self.inbound_freight + self.prep + self.duties + self.non_recoverable_taxes

    @property
    def cogs_assumed(self) -> bool:
        return self.cogs_status == "assumed"


# ---------------------------------------------------------------- юнит-экономика

@dataclass(frozen=True)
class UnitEconomics:
    gross_price: float
    net_revenue: float
    landed_cogs: float
    referral_fee: float
    marketplace_fees: float
    returns_cost: float
    other_variable: float
    pre_ad_contribution: float
    ad_cost_per_unit: float
    post_ad_contribution: float
    contribution_margin: float | None
    be_acos_net: float | None
    be_acos_console: float | None

    def as_dict(self) -> dict:
        return asdict(self)


def unit_economics(gross_price: float, tax: TaxContext, fees: FeeSchedule, costs: UnitCosts,
                   tacos_net: float = 0.0, ad_cost_per_unit: float | None = None) -> UnitEconomics:
    """Формулы §11.2. Реклама задаётся либо TACoS (в net-базе), либо прямой стоимостью на единицу."""
    if gross_price <= 0:
        raise ValueError("gross_price must be positive")
    net_revenue = tax.net_of_tax(gross_price) - tax.net_of_tax(costs.coupon_gross)
    referral = fees.referral.fee(gross_price)
    marketplace_fees = referral + fees.fulfillment_fee + fees.storage_per_unit + fees.other_amazon_fees
    landed = costs.landed_cogs
    lost_fees = (costs.lost_fees_per_return if costs.lost_fees_per_return is not None
                 else fees.fulfillment_fee)
    returns_cost = costs.return_rate * (
        fees.return_processing_fee + costs.unsellable_share * landed + lost_fees)
    pre_ad = net_revenue - landed - marketplace_fees - returns_cost - costs.other_variable
    ad = ad_cost_per_unit if ad_cost_per_unit is not None else tacos_net * net_revenue
    post_ad = pre_ad - ad
    return UnitEconomics(
        gross_price=gross_price,
        net_revenue=net_revenue,
        landed_cogs=landed,
        referral_fee=referral,
        marketplace_fees=marketplace_fees,
        returns_cost=returns_cost,
        other_variable=costs.other_variable,
        pre_ad_contribution=pre_ad,
        ad_cost_per_unit=ad,
        post_ad_contribution=post_ad,
        contribution_margin=post_ad / net_revenue if net_revenue > 0 else None,
        # BE ACoS: какую долю рекламной продажи можно отдать рекламе, не уходя в минус.
        be_acos_net=pre_ad / net_revenue if net_revenue > 0 else None,
        # Консоль Amazon Ads в EU считает ACoS от продаж с НДС → сравнивать с этим значением.
        be_acos_console=pre_ad / gross_price,
    )


def break_even_units(fixed_launch_costs: float, post_ad_contribution: float) -> float | None:
    """None означает «не окупается» (contribution ≤ 0) — деление не выполняется."""
    if post_ad_contribution <= 0:
        return None
    return math.ceil(fixed_launch_costs / post_ad_contribution)


def min_viable_price(tax: TaxContext, fees: FeeSchedule, costs: UnitCosts, tacos_net: float,
                     search_max: float, step: float = 0.01) -> float | None:
    """Минимальная gross-цена с post-ad contribution ≥ 0 (§10).

    Сканирование, а не бисекция: при «whole»-тарифах referral fee функция немонотонна
    на границе уровня (цена чуть выше порога может быть хуже цены на пороге).
    """
    cents = int(round(step * 100))
    for c in range(cents, int(round(search_max * 100)) + 1, cents):
        price = c / 100
        if unit_economics(price, tax, fees, costs, tacos_net).post_ad_contribution >= 0:
            return price
    return None


def best_contribution_in_range(price_range: tuple, tax, fees, costs, tacos_net, step=0.01):
    """Максимум post-ad contribution по допустимому ценовому диапазону (для правила R2)."""
    lo, hi = price_range
    best = None
    c = int(round(lo * 100))
    while c <= int(round(hi * 100)):
        ue = unit_economics(c / 100, tax, fees, costs, tacos_net)
        if best is None or ue.post_ad_contribution > best.post_ad_contribution:
            best = ue
        c += int(round(step * 100))
    return best


# ---------------------------------------------------------------- запасы (§11.5)

@dataclass(frozen=True)
class LeadTime:
    production_days: int
    transit_days: int
    customs_days: int = 0
    receiving_days: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "LeadTime":
        return cls(int(d["production_days"]), int(d["transit_days"]),
                   int(d.get("customs_days", 0)), int(d.get("receiving_days", 0)))

    @property
    def total_days(self) -> int:
        return self.production_days + self.transit_days + self.customs_days + self.receiving_days

    def delayed(self, extra_days: int) -> "LeadTime":
        return LeadTime(self.production_days, self.transit_days + extra_days,
                        self.customs_days, self.receiving_days)


def safety_stock(daily_sd: float, lead_time_days: int, z: float) -> float:
    return z * daily_sd * math.sqrt(lead_time_days)


REVIEW_PERIOD_DAYS = 30   # запас проверяется раз в месяц (шаг модели) → периодический пересмотр


def reorder_point(avg_daily_units: float, daily_sd: float, lead_time_days: int, z: float,
                  review_period_days: int = REVIEW_PERIOD_DAYS) -> float:
    """ROP при периодическом пересмотре: спрос за (LT + R) + safety stock на (LT + R)."""
    exposure = lead_time_days + review_period_days
    return avg_daily_units * exposure + safety_stock(daily_sd, exposure, z)


@dataclass
class InventoryPlan:
    initial_units: int
    reorder_point_units: int
    safety_stock_units: int
    capacity_ok: bool
    sd_assumed: bool
    notes: list = field(default_factory=list)


def plan_initial_inventory(monthly_demand: list, lead_time: LeadTime, coverage_target_days: int,
                           moq: int, fba_capacity_units: int | None, z: float,
                           daily_sd: float | None = None, niche_cv: float = 0.5) -> InventoryPlan:
    """Стартовый запас = спрос за (lead time + coverage target) по кривой Base, не меньше MOQ.

    monthly_demand — спрос по месяцам продаж (после разгона), начиная с первого месяца продаж.
    FBA capacity — hard constraint (§11.5): при превышении capacity_ok=False → правило R4.
    """
    days = lead_time.total_days + coverage_target_days
    units, remaining = 0.0, days
    for m in monthly_demand:
        take = min(30, remaining)
        units += m * take / 30
        remaining -= take
        if remaining <= 0:
            break
    if remaining > 0 and monthly_demand:
        units += monthly_demand[-1] * remaining / 30
    steady_daily = (monthly_demand[-1] if monthly_demand else 0) / 30
    sd_assumed = daily_sd is None
    sd = daily_sd if daily_sd is not None else steady_daily * niche_cv
    ss = safety_stock(sd, lead_time.total_days + REVIEW_PERIOD_DAYS, z)
    rop = reorder_point(steady_daily, sd, lead_time.total_days, z)
    initial = max(int(math.ceil(units)), moq)
    notes = []
    if initial == moq and units < moq:
        notes.append(f"Стартовый запас поднят до MOQ ({moq}).")
    if sd_assumed:
        notes.append("σ дневных продаж принята по CV ниши (assumed).")
    capacity_ok = fba_capacity_units is None or initial <= fba_capacity_units
    if not capacity_ok:
        notes.append(f"Стартовый запас {initial} > FBA capacity {fba_capacity_units}.")
    return InventoryPlan(initial, int(math.ceil(rop)), int(math.ceil(ss)), capacity_ok, sd_assumed, notes)
