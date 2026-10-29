# Формулы и правила расчёта

## Содержание
1. P&L
2. COGS и возвраты
3. Cash Flow / Settlement
4. Sales Analytics
5. Advertising
6. Inventory
7. Unit Economics
8. What-if
9. Контрольные примеры

## 1. P&L

```
Gross Sales            = product sales (Orders, net of VAT) + shipping/gift credits
− Discounts & Promotions
− Refunds
= Net Revenue
− COGS
= Gross Profit
− Marketplace Fees − Fulfillment & Logistics − Storage − Advertising − Promotions & Deals Fees
+ Reimbursements − Claims & Other Amazon
= Contribution Profit
− Operating Expenses
= Operating Profit
± Interest / FX / Other
= Profit Before Tax
− Income Taxes
= Net Profit / Loss
```

- Маржи (Gross, Contribution, Operating, Net) — от Net Revenue.
- **Net Revenue включает shipping/gift-wrap credits** покупателя (без VAT); у FBM парная стоимость доставки — в Fulfillment & Logistics (из Cost Master `fbm_shipping_cost`).
- **Расходы уровня аккаунта** (Subscription и Service Fees без order id) — отдельной строкой «Account-level costs» после Contribution по Marketplace; в SKU/Marketplace не распределять без методики пользователя. Погашение через `Seller repayment` — только Cash Flow.
- Нет COGS → Gross Profit и ниже UNAVAILABLE; строки выше считать.
- Нет OpEx → остановиться на Contribution Profit с пометкой.
- Нет налога → остановиться на Profit Before Tax; не называть его Net Profit.

**VAT.** Если продавец сам уплачивает VAT, а суммы в отчёте с VAT: `net = gross / (1 + v)`; ставка — по стране назначения (OSS) или Marketplace; без данных о стране — ставка Marketplace, статус ESTIMATED. Если в Date Range Report есть колонка `product sales tax`, то `product sales` уже net — не делить повторно. Facilitator Tax (`marketplace withheld tax`) — исключить полностью.

## 2. COGS и возвраты

- **Weighted Average:** `avg_cost = (стоимость остатка + стоимость поступлений) / (кол-во остатка + кол-во поступлений)`; COGS = Units Sold × avg_cost.
- **FIFO:** списывать партии в порядке поступления (нужны даты и цены партий).
- Без истории партий — Landed Cost из Cost Master по `valid_from` на дату продажи; метод = «стандартная себестоимость», статус CALCULATED.
- **Units Sold для COGS** = отгруженные единицы (Order) − возвращённые sellable единицы.
- Unsellable/утилизированные возвраты — COGS не сторнировать; себестоимость → «Потери от возвратов».
- Refund без возврата товара — COGS не сторнировать; кандидат в Reimbursements.
- Нет отчёта FBA Customer Returns → показать диапазон (0% … 100% sellable) или принять долю с пометкой ESTIMATED.

## 3. Cash Flow / Settlement

```
Closing Cash = Opening Cash + Cash Inflows − Cash Outflows
Net Cash Flow = Cash Inflows − Cash Outflows
Operating CF = поступления от Amazon и клиентов − платежи поставщикам, логистике, рекламе (если картой), OpEx, налоги
Investing CF = оборудование, ПО-капзатраты
Financing CF = кредиты/Amazon Lending/взносы − погашения тела − дивиденды
```

**Settlement & Payout Analysis** (без банковской выписки):
```
Settlement Total = Sales + Credits − Refunds − Fees − Ads(если удерживается) ± Reimbursements ± Reserve change ± Adjustments
Payout = Settlement Total (→ Transfer); сверка: Σ строк settlement = total-amount
Revenue → Payout bridge: Net Revenue − Amazon fees − Ads(в settlement) + Reimbursements ± Reserve ± timing (DD+7, переходящие settlement) = Payout
```
- Комиссии внутри settlement — не отдельный банковский отток.
- Pending / Deferred (DD+7) и Reserve — отдельные строки, не «получено».
- Прогноз 7/14/30/60/90 дней: средние дневные чистые поступления × дни + известные будущие платежи; помечать «Прогноз», перечислять допущения.

## 4. Sales Analytics

```
AOV = Net Revenue (или Ordered Product Sales — указать) / Orders
ASP = Net Revenue / Units Sold
Units per Order = Units / Orders
Refund Rate (units) = Refunded Units / Units Sold
Conversion (Unit Session %) = Units Ordered / Sessions
Growth % = (Текущий − Прошлый) / |Прошлый| × 100%
```
- Сравнивать только периоды равной длины (неполный месяц ↔ тот же диапазон дней прошлого месяца/года).

**Малая выборка.** Относительные метрики и выводы — только при достаточной базе:
| Метрика / вывод | Минимум |
|---|---|
| Refund Rate, CVR, доля возвратов по причинам | ≥ 30 заказов (единиц) в базе SKU/Marketplace |
| Growth %, тренды, сезонность | ≥ 2 сопоставимых периода по ≥ 10 заказов |
| Статистические аномалии Leakage (рост fee, «аномальные» возвраты) | ≥ 20 событий по SKU |
| AOV/ASP как KPI | ≥ 5 заказов |
Ниже порога — показывать абсолютные значения, а вместо процента/тренда писать «недостаточно данных (n = X)». Детерминированные проверки (комиссия vs тариф, сверки, VAT) работают на любом объёме.
- Business Report: Ordered Product Sales — с VAT и по дате заказа; не сравнивать напрямую с Net Revenue P&L.

## 5. Advertising

```
CTR  = Clicks / Impressions × 100%
CPC  = Spend / Clicks
CVR  = Orders / Clicks × 100%
ACoS = Spend / Attributed Sales × 100%
ROAS = Attributed Sales / Spend
TACoS = Spend / Total Net Revenue × 100%
Profit After Advertising (SKU) = Contribution до рекламы − Ad Spend SKU
```
- Spend — из одного источника (Ads-отчёт по дате показа ИЛИ Settlement/инвойсы по дате списания); второй — только сверка.
- Attributed Sales в EU — с VAT; для ACoS использовать как есть, при сравнении с Net Revenue — переводить в net и помечать.
- Окна: SP 7 дней, SB/SD 14 дней; последние 7/14 дней периода — атрибуция ещё не закрыта, пометить.

## 6. Inventory

```
Inventory Value at Cost = Units on hand × Landed Cost (метод COGS)
Days of Supply = (Available + Inbound) / Средние дневные продажи (последние 30 дней)
Sell-through = Units Sold / (Opening Units + Received Units)
Inventory Turnover = COGS / Средний запас по себестоимости
Stockout Risk: Days of Supply < lead time поставщика + буфер (по умолчанию 14 дней)
Excess: Days of Supply > 180 (по умолчанию), Dead Stock: 0 продаж за 90 дней при остатке > 0
```
Сверка Ledger:
```
Closing = Opening + Receipts + Customer Returns − Customer Shipments − Removals − Disposals ± Adjustments(Lost/Found/Damaged/Transfers)
```

## 7. Unit Economics

Обозначения: `P` — цена товара для покупателя (с VAT, если применимо); `S` — доставка/gift-wrap, оплаченные покупателем (с VAT; 0 для FBA/бесплатной доставки); `v` — ставка VAT (0, если без VAT, напр. US, или если VAT удержан Amazon как Facilitator — тогда VAT всё равно вычитается из цены, т. к. продавец его не получает); `r` — ставка Referral Fee; `d` — надбавка Digital Services Tax на комиссии Amazon в Marketplace; `a` — рекламная доля от цены (Ad Spend / Sales, по SKU); `m` — целевая маржа от net-выручки; `F` — затраты на единицу:

```
F = Landed Cost + FBA fee·(1+d) | (fbm_shipping_cost + fbm_packaging) + Storage per unit
    + Return rate × Return cost per return + Other variable per unit
Return cost per return ≈ Refund Admin Fee + Return processing + (1 − sellable share) × Landed Cost
```

**Важно (подтверждено реальными транзакциями):** Referral Fee считается от **полной суммы, оплаченной покупателем — товар + доставка + gift wrap, с VAT**, и к ней добавляется DST-надбавка: `Referral = r · (P + S) · (1 + d)`.

Округление как у Amazon: сначала Referral округляется до цента, затем применяется DST и снова округляется (UK: 0,15·34,98 = 5,247 → 5,25 → ·1,02 = 5,355 → **5,36**). Для сверки с транзакциями использовать этот порядок; без него расхождение в 0,01 — не находка.

DST-надбавка `d` (проверять актуальность в Seller Central): UK 2%, IT 3%, FR 3%, ES 3%; DE, NL, PL, SE, BE, US — 0. Применяется к комиссиям Amazon (Referral, FBA и др.).

Расчёты:
```
k                = 1/(1+v) − r·(1+d)               # доля net-выручки, остающаяся после Referral
Net Revenue/ед.  = (P + S) / (1 + v)
Referral Fee     = max(r·(P+S), min referral fee) · (1+d)
Ad Cost          = a · P
Unit Profit      = (P + S)·k − a·P − F
Unit Margin      = Unit Profit / Net Revenue
ROI              = Unit Profit / Landed Cost × 100%
Break-even Price = (F − S·k) / (k − a)
Target Price     = (F − S·(k − m/(1+v))) / (k − a − m/(1+v))
Pre-ad Margin    = ((P + S)·k − F) / P             # от цены товара с VAT, сопоставимо с ACoS
Break-even ACoS  = Pre-ad Margin
Target ACoS      = ((P + S)·(k − m/(1+v)) − F) / P
```
При `S = 0`, `d = 0` формулы сводятся к `F/(1/(1+v) − r − a)` и `F/((1−m)/(1+v) − r − a)`. Для FBM доставка `S` — фиксированная (не растёт с ценой товара).
- Знаменатель ≤ 0 → цена недостижима в этой модели — так и написать.
- После расчёта проверить минимальную Referral Fee и пересечение порогов тарифов (ступенчатая Referral Fee по цене, FBA-тир по размеру/цене, Low-Price FBA). Если пороги затронуты — численное решение (бисекция по P с точными функциями комиссий).
- Статусы SKU: `Loss` (Unit Profit < 0), `Below Target` (Margin < m), `On Target`, `Ads Over Limit` (Actual ACoS > Break-even ACoS).

## 8. What-if

Базой служит текущий период (или последние 30 дней) по SKU. Все сценарии — через одну модель SKU, без двойного учёта.

- **Price Change** `Δp%`: `P' = P × (1 + Δp)`; Units' = Units × (1 + e × Δp) (по умолчанию e = 0 — допущение «объём неизменен», вывести явно); пересчитать Referral/FBA с учётом порогов.
- **Advertising** (Δ в п.п.): режим A — `Spend' = ACoS' × Attributed Sales`; режим B — `Attributed Sales' = Spend / ACoS'`, изменение органики только по допущению пользователя.
- **Sales Growth** `g%`: Units' = Units × (1+g); переменные затраты пропорционально; реклама — по допущению (по умолчанию TACoS неизменен); Cash Need = (Units'/день × (DoS цель + lead time) − текущий запас) × Landed Cost.
- **Supplier Cost** `−c%`: Purchase Cost' = Purchase Cost × (1 − c); остальные компоненты Landed Cost неизменны.
- **Combined:** применить последовательно к одной модели: цена → объём → себестоимость → реклама.
- Вывод: Current / Scenario / Delta по Revenue, Expenses, Contribution Profit, Net Profit (если доступен), Margin, Cash Need. Ограничить объём остатками + поставками.

## 9. Контрольные примеры

| # | Вход | Ожидаемо |
|---|---|---|
| U1 | P = 29,99; v = 19%; r = 15%; a = 10%; F = 12,00; m = 15% | P_net 25,20; Referral 4,50; Ads 3,00; Unit Profit **5,70**; Break-even **20,33**; Target **25,85**; Break-even ACoS **29,0%**; Target ACoS **16,4%** |
| U2 | То же, v = 0 (US) | Break-even = 12/0,75 = **16,00**; Target = 12/0,60 = **20,00** |
| U3 | Реальный заказ IT (FBM): P = 63,55; S = 10,00; v = 22%; r = 15%; d = 3% | Referral = 0,15 · 73,55 · 1,03 = **11,36** (совпадает с `Amazon fees` в транзакции); Net Revenue = 52,09 + 8,20 = **60,29** |
| U4 | Реальный заказ UK (FBM): P = 27,99; S = 6,99; v = 20%; r = 15%; d = 2% | Referral = 0,15 · 34,98 · 1,02 = **5,36** (совпадает); Net Revenue = 23,32 + 5,83 = **29,15** |
| S1 | Seller repayment +39 и Subscription −39 | P&L: Subscription −39 (уровень аккаунта); Cash Flow: отток 39 с карты; доход 39 — **нет** |
| A1 | ACoS 30% → −3 п.п., режим A, Attributed Sales 10 000 | Spend 3 000 → 2 700, экономия **300** |
| A2 | ACoS 30% → −3%, режим A | ACoS 29,1%, Spend 2 910, экономия **90** — это другой сценарий |
| C1 | Payout 8 000, Net Revenue 12 000 | Revenue = 12 000; мост Revenue → Payout объясняет 4 000 |
