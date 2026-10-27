"""Помесячная cash-flow модель, сценарии, стресс-тесты (ТЗ v1.2 §11.3, §11.4, §12.1).

Закрывает проблему P7: payback, liquidity gap и Required Capital считаются из явной
модели денежного потока (предоплата поставщику, lead time, выплаты Amazon, дозаказы).

Упрощения (документированы, т. к. влияют на результат):
- шаг модели — 30 дней; продажи партии начинаются с первого полного месяца после поступления;
- закупочное решение (стартовая партия) принимается один раз по Base-сценарию и одинаково
  для всех сценариев — в Conservative мы рискуем тем же запасом;
- неликвидный остаток возвратов учтён в accrual-прибыли (через returns_cost), но не уменьшает запас.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from .config import Config, SCENARIOS
from .economics import (FeeSchedule, LeadTime, TaxContext, UnitCosts, plan_initial_inventory,
                        reorder_point, unit_economics)


@dataclass(frozen=True)
class ScenarioParams:
    name: str
    gross_price: float
    steady_units_month: float
    tacos_steady_net: float
    ramp: tuple
    tacos_curve: tuple
    demand_multiplier: float = 1.0
    ad_cost_multiplier: float = 1.0


@dataclass(frozen=True)
class LaunchParams:
    lead_time: LeadTime
    deposit_pct: float
    moq: int
    fixed_launch_costs: float = 0.0
    monthly_fixed_costs: float = 0.0
    payout_delay_days: int = 14
    coverage_target_days: int = 60
    reorder_cover_days: int = 90
    fba_capacity_units: int | None = None
    seasonality: tuple | None = None   # 12 индексов (январь..декабрь), среднее ≈ 1
    start_month: int = 1               # календарный месяц размещения первого заказа
    niche_cv: float = 0.5

    @classmethod
    def from_dict(cls, d: dict) -> "LaunchParams":
        season = d.get("seasonality")
        if season is not None:
            if len(season) != 12:
                raise ValueError("seasonality must have 12 monthly indices")
            mean = sum(season) / 12
            season = tuple(s / mean for s in season)   # нормировка к среднему 1
        return cls(
            lead_time=LeadTime.from_dict(d["lead_time"]),
            deposit_pct=float(d["deposit_pct"]),
            moq=int(d["moq"]),
            fixed_launch_costs=float(d.get("fixed_launch_costs", 0)),
            monthly_fixed_costs=float(d.get("monthly_fixed_costs", 0)),
            payout_delay_days=int(d.get("payout_delay_days", 14)),
            coverage_target_days=int(d.get("coverage_target_days", 60)),
            reorder_cover_days=int(d.get("reorder_cover_days", 90)),
            fba_capacity_units=d.get("fba_capacity_units"),
            seasonality=season,
            start_month=int(d.get("start_month", 1)),
            niche_cv=float(d.get("niche_cv", 0.5)),
        )


@dataclass
class MonthRow:
    month: int
    demand: float
    units_sold: float
    lost_units: float
    inventory_end: float
    net_revenue: float
    ad_spend: float
    profit: float
    cash_in: float
    cash_out: float
    net_cash: float
    cum_cash: float


@dataclass
class CashFlowResult:
    scenario: str
    rows: list
    initial_units: int
    sales_start_month: int
    profit_12m: float
    cum_cash_12m: float
    liquidity_gap: float
    required_capital: float
    payback_month: int | None
    loss_at_horizon: float       # убыток на конец горизонта модели с учётом ликвидационной стоимости запаса
    capital_roi_12m: float | None
    stockout_months: list = field(default_factory=list)


def _curve(curve, k):
    return curve[min(k, len(curve) - 1)]


def demand_series(sc: ScenarioParams, launch: LaunchParams, horizon: int) -> list:
    """Спрос по календарным месяцам модели (0 до начала продаж)."""
    start = sales_start_month(launch.lead_time)
    out = []
    for m in range(horizon):
        if m < start:
            out.append(0.0)
            continue
        season = 1.0
        if launch.seasonality:
            season = launch.seasonality[(launch.start_month - 1 + m) % 12]
        out.append(sc.steady_units_month * _curve(sc.ramp, m - start) * season * sc.demand_multiplier)
    return out


def sales_start_month(lead_time: LeadTime) -> int:
    return math.ceil(lead_time.total_days / 30)


def simulate(sc: ScenarioParams, launch: LaunchParams, tax: TaxContext, fees: FeeSchedule,
             costs: UnitCosts, initial_units: int, cfg: Config) -> CashFlowResult:
    H = cfg.horizon_months
    lt = launch.lead_time
    start = sales_start_month(lt)
    prod_m = lt.production_days // 30
    ue = unit_economics(sc.gross_price, tax, fees, costs, tacos_net=0.0)
    landed_extra = costs.landed_cogs - costs.cogs          # фрахт, prep, пошлины — при отгрузке
    payout_same = max(0.0, 1 - launch.payout_delay_days / 30)
    # Денежная часть возвратов (неликвид уже оплачен при закупке и учтён в accrual).
    returns_cash = costs.return_rate * (fees.return_processing_fee + (
        costs.lost_fees_per_return if costs.lost_fees_per_return is not None else fees.fulfillment_fee))
    cash_per_unit = ue.net_revenue - ue.marketplace_fees - returns_cash - costs.other_variable

    demand = demand_series(sc, launch, H + 3)
    cash_out = [0.0] * (H + 24)
    cash_in = [0.0] * (H + 24)
    arrivals = [0.0] * (H + 24)
    orders = []   # (месяц заказа, месяц поступления, количество)

    def place_order(order_month_end_day: int, qty: int, month_idx: int):
        cash_out[month_idx] += launch.deposit_pct * qty * costs.cogs
        ship_day = order_month_end_day + lt.production_days
        cash_out[ship_day // 30] += (1 - launch.deposit_pct) * qty * costs.cogs + qty * landed_extra
        arrival = math.ceil((order_month_end_day + lt.total_days) / 30)
        arrivals[arrival] += qty
        orders.append((month_idx, arrival, qty))

    place_order(0, initial_units, 0)
    cash_out[0] += launch.fixed_launch_costs

    on_hand, on_order = 0.0, float(initial_units)
    rows, cum, stockouts = [], 0.0, []
    for m in range(H):
        on_hand += arrivals[m]
        on_order -= arrivals[m]
        sold = min(demand[m], on_hand)
        lost = demand[m] - sold
        if lost > 1e-9:
            stockouts.append(m)
        on_hand -= sold
        k = max(0, m - start)
        tacos = sc.tacos_steady_net * _curve(sc.tacos_curve, k) * sc.ad_cost_multiplier
        ad = sold * ue.net_revenue * tacos
        payout = sold * cash_per_unit
        cash_in[m] += payout * payout_same
        cash_in[m + 1] += payout * (1 - payout_same)
        cash_out[m] += ad + launch.monthly_fixed_costs
        profit = sold * ue.pre_ad_contribution - ad - launch.monthly_fixed_costs
        if m == 0:
            profit -= launch.fixed_launch_costs

        # Дозаказ по точке перезаказа на основе прогноза ближайших месяцев (§11.5).
        if m >= start - 1:
            daily_next = (demand[m + 1] if m + 1 < len(demand) else demand[m]) / 30
            rop = reorder_point(daily_next, daily_next * launch.niche_cv, lt.total_days,
                                cfg.service_level_z)
            arrival_m = math.ceil(((m + 1) * 30 + lt.total_days) / 30)
            if on_hand + on_order < rop and daily_next > 0 and arrival_m < H:
                qty = max(launch.moq, math.ceil(daily_next * launch.reorder_cover_days))
                place_order((m + 1) * 30, qty, m)
                on_order += qty

        net = cash_in[m] - cash_out[m]
        cum += net
        rows.append(MonthRow(m, demand[m], sold, lost, on_hand, sold * ue.net_revenue, ad,
                             profit, cash_in[m], cash_out[m], net, cum))

    cums = [r.cum_cash for r in rows]
    gap = max(0.0, -min(cums))
    payback = None
    went_negative = False
    for r in rows:
        if r.cum_cash < 0:
            went_negative = True
        elif went_negative:
            payback = r.month
            break
    profit_12 = sum(r.profit for r in rows[:12])
    cum_12 = rows[min(11, H - 1)].cum_cash
    # Убыток считаем на конец горизонта: так чистый сдвиг продаж во времени (задержка поставки)
    # не выглядит как потеря. Запас = на складе + заказанное, но не поступившее, по ликвидационной цене.
    last = H - 1
    in_transit = sum(q for om, am, q in orders if om <= last and am > last)
    inv_end = rows[last].inventory_end + in_transit
    salvage = inv_end * costs.landed_cogs * cfg.inventory_salvage_rate
    required = gap * (1 + cfg.capital_buffer)
    return CashFlowResult(
        scenario=sc.name, rows=rows, initial_units=initial_units, sales_start_month=start,
        profit_12m=profit_12, cum_cash_12m=cum_12, liquidity_gap=gap, required_capital=required,
        payback_month=payback, loss_at_horizon=max(0.0, -(rows[last].cum_cash + salvage)),
        capital_roi_12m=profit_12 / required if required > 0 else None,
        stockout_months=stockouts)


# ---------------------------------------------------------------- сценарии и стресс

def build_scenarios(units: dict, prices: dict, tacos: dict, business_model: str,
                    cfg: Config) -> dict:
    """units/prices/tacos — словари по сценариям conservative/base/optimistic."""
    out = {}
    for s in SCENARIOS:
        if business_model == "resale":
            ramp, curve = tuple(cfg.resale_ramp), tuple(cfg.resale_tacos_curve)
        else:
            ramp, curve = tuple(cfg.ramp[s]), tuple(cfg.tacos_curve[s])
        out[s] = ScenarioParams(s, prices[s], units[s], tacos[s], ramp, curve)
    return out


@dataclass
class ScenarioAnalysis:
    initial_units: int
    inventory_notes: list
    capacity_ok: bool
    reorder_point_units: int
    results: dict          # сценарий → CashFlowResult
    stress: dict           # имя стресса → CashFlowResult
    expected_profit_12m: float
    capital_at_risk: float
    risk_return: float | None


def analyze_scenarios(scenarios: dict, launch: LaunchParams, tax, fees, costs, cfg: Config) -> ScenarioAnalysis:
    base = scenarios["base"]
    start = sales_start_month(launch.lead_time)
    base_demand = [d for d in demand_series(base, launch, cfg.horizon_months + 6)[start:]]
    inv = plan_initial_inventory(base_demand, launch.lead_time, launch.coverage_target_days,
                                 launch.moq, launch.fba_capacity_units, cfg.service_level_z,
                                 niche_cv=launch.niche_cv)
    # Если стартовый запас не помещается в FBA capacity, моделируем ровно то, что можно завезти;
    # сам факт ограничения уходит в Decision Engine (R4).
    initial = inv.initial_units
    if not inv.capacity_ok:
        initial = max(int(launch.fba_capacity_units), 0)

    results = {s: simulate(sc, launch, tax, fees, costs, initial, cfg) for s, sc in scenarios.items()}

    stress = {
        "price_-15%": simulate(replace(base, gross_price=base.gross_price * (1 + cfg.stress_price)),
                               launch, tax, fees, costs, initial, cfg),
        "cpc_+30%": simulate(replace(base, ad_cost_multiplier=1 + cfg.stress_cpc),
                             launch, tax, fees, costs, initial, cfg),
        "cvr_-30%": simulate(replace(base, demand_multiplier=1 + cfg.stress_cvr,
                                     ad_cost_multiplier=1 / (1 + cfg.stress_cvr)),
                             launch, tax, fees, costs, initial, cfg),
        f"delay_+{cfg.stress_delay_days}d": simulate(
            base, replace(launch, lead_time=launch.lead_time.delayed(cfg.stress_delay_days)),
            tax, fees, costs, initial, cfg),
    }
    # 50 % стартового запаса не продано за N месяцев продаж: масштабируем спрос Base.
    window = base_demand[:cfg.stress_unsold_months]
    target_sold = initial * (1 - cfg.stress_unsold_share)
    mult = min(1.0, target_sold / sum(window)) if sum(window) > 0 else 1.0
    stress["unsold_50%"] = simulate(replace(base, demand_multiplier=mult),
                                    launch, tax, fees, costs, initial, cfg)

    w = cfg.scenario_weights
    expected = sum(w[s] * results[s].profit_12m for s in SCENARIOS)
    car = max([results["conservative"].loss_at_horizon] + [r.loss_at_horizon for r in stress.values()])
    return ScenarioAnalysis(
        initial_units=initial, inventory_notes=inv.notes, capacity_ok=inv.capacity_ok,
        reorder_point_units=inv.reorder_point_units, results=results, stress=stress,
        expected_profit_12m=expected, capital_at_risk=car,
        risk_return=expected / car if car > 0 else None)
