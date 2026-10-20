# Распознавание и парсинг отчётов Amazon

## Содержание
1. Сигнатуры отчётов
2. Локализованные заголовки Date Range Report
3. Правила парсинга
4. Маппинг типов транзакций → строки P&L
5. Cost Master
6. Где скачать недостающие отчёты

## 1. Сигнатуры отчётов

Определять тип по набору колонок (регистр, BOM и пробелы/дефисы/подчёркивания нормализовать). Сравнивать заголовок со **всеми** вариантами сигнатур и брать лучший. Совпадение ≥ 70% ключевых колонок → тип распознан; 40–70% — «вероятный тип» с перечнем недостающих колонок; < 40% — «не распознан»: показать заголовок пользователю и спросить, что это за отчёт. Amazon часто меняет состав колонок — новый вариант не повод отказываться от анализа.

| Тип | Ключевые колонки (EN) | Применение |
|---|---|---|
| Date Range / Transaction Report | `date/time`, `settlement id`, `type`, `order id`, `sku`, `quantity`, `marketplace`, `product sales`, `selling fees`, `fba fees`, `other transaction fees`, `other`, `total` | Основной источник P&L |
| Settlement Report (Flat File V2) | `settlement-id`, `settlement-start-date`, `settlement-end-date`, `deposit-date`, `total-amount`, `currency`, `transaction-type`, `order-id`, `amount-type`, `amount-description`, `amount`, `posted-date`, `sku` | Payout, сверка с банком |
| All Orders Report | `amazon-order-id`, `purchase-date`, `order-status`, `fulfillment-channel`, `sales-channel`, `sku`, `asin`, `quantity`, `currency`, `item-price`, `item-tax`, `promotion-discount` | Заказы, отмены, Pending |
| Business Report (Detail Page Sales and Traffic by Child Item) | `(Parent) ASIN`, `(Child) ASIN`, `Title`, `Sessions`, `Page Views`, `Unit Session Percentage`, `Units Ordered`, `Ordered Product Sales`, `Total Order Items` | Трафик, конверсия |
| Business Report (Sales and Orders by ASIN, без трафика) | `(Child) ASIN`, `Units ordered`, `Ordered Product Sales`, `Total order items`, `Units refunded`, `Refund Rate`, `Shipped product sales`, `Units shipped`, `Orders shipped` | Заказы/отгрузки/возвраты по ASIN; Sessions, Page Views, Conversion → UNAVAILABLE. Нет колонок даты и Marketplace — брать из имени файла (§3.1) |
| Payments Transactions view (экспорт со страницы Payments → Transactions) | `Date`, `Transaction status`, `Transaction type`, `Order ID`, `Product Details`, `Total product charges`, `Total promotional rebates`, `Amazon fees`, `Other`, `Total (<CUR>)` | Транзакции по заказам и сервисным платежам с агрегированными комиссиями; см. §3.2 |
| FBA Manage Inventory | `sku`, `fnsku`, `asin`, `product-name`, `afn-fulfillable-quantity`, `afn-reserved-quantity`, `afn-inbound-working-quantity`, `afn-inbound-shipped-quantity`, `afn-inbound-receiving-quantity`, `afn-unsellable-quantity` | Остатки |
| Inventory Ledger (Detailed) | `Date`, `FNSKU`, `ASIN`, `MSKU`, `Event Type`, `Reference ID`, `Quantity`, `Fulfillment Center`, `Disposition`, `Reason` | Движение запасов, Lost/Damaged |
| Inventory Ledger (Summary) | `Date`, `FNSKU`, `MSKU`, `Starting Warehouse Balance`, `Receipts`, `Customer Shipments`, `Customer Returns`, `Vendor Returns`, `Warehouse Transfer In/Out`, `Found`, `Lost`, `Damaged`, `Disposed`, `Other Events`, `Ending Warehouse Balance` | Сверка остатков |
| FBA Customer Returns | `return-date`, `order-id`, `sku`, `asin`, `fnsku`, `quantity`, `fulfillment-center-id`, `detailed-disposition`, `reason`, `status` | Возвраты, sellable/unsellable |
| Reimbursements | `approval-date`, `reimbursement-id`, `case-id`, `amazon-order-id`, `reason`, `sku`, `fnsku`, `asin`, `condition`, `currency-unit`, `amount-per-unit`, `amount-total`, `quantity-reimbursed-cash`, `quantity-reimbursed-inventory` | Компенсации |
| Monthly Storage Fees | `asin`, `fnsku`, `fulfillment_center`, `country_code`, `item_volume`, `average_quantity_on_hand`, `month_of_charge`, `storage_rate`, `currency`, `estimated_monthly_storage_fee` | Хранение |
| Aged Inventory Surcharge / LTSF | `snapshot-date`, `sku`, `fnsku`, `asin`, `qty-charged`, `amount-charged`, `surcharge-age-tier`, `currency` | Aged inventory |
| FBA Fee Preview | `sku`, `asin`, `product-group`, `price`, `longest-side`, `median-side`, `shortest-side`, `item-package-weight`, `product-size-tier`, `estimated-referral-fee-per-unit`, `expected-fulfillment-fee-per-unit` | Ожидаемые тарифы для Leakage |
| Sponsored Products Advertised Product | `Date`/`Start Date`, `Campaign Name`, `Ad Group Name`, `Advertised SKU`, `Advertised ASIN`, `Impressions`, `Clicks`, `Spend`, `7 Day Total Sales`, `7 Day Total Orders (#)`, `7 Day Total Units (#)` | Реклама по SKU |
| Sponsored Products Search Term | `Customer Search Term`, `Targeting`, `Match Type`, `Impressions`, `Clicks`, `Spend`, `7 Day Total Sales` | Утечки на запросах без продаж |
| Sponsored Brands / Display Campaign | `Campaign Name`, `Impressions`, `Clicks`, `Spend`, `14 Day Total Sales`, `14 Day Total Orders (#)` | Реклама SB/SD |
| Cost Master (пользователь) | `sku`, `currency`, `purchase_cost` (+ опционально см. §5) | COGS |
| Bank Statement | дата, сумма (или дебет/кредит), назначение/контрагент, валюта | Фактический Cash Flow; поступления Amazon — по назначению «AMAZON PAYMENTS» / «Amazon EU S.a.r.l.» и т.п. |

## 2. Локализованные заголовки Date Range Report

Значения ниже — типичные; при сомнении сверять по позиции колонки и характеру данных.

| EN | DE | FR | IT | ES |
|---|---|---|---|---|
| date/time | Datum/Uhrzeit | date/heure | Data/Ora | fecha y hora |
| settlement id | Abrechnungsnummer | numéro de versement | Numero pagamento | identificador de pago |
| type | Typ | type | Tipo | tipo |
| order id | Bestellnummer | numéro de la commande | Numero ordine | número de pedido |
| quantity | Menge | quantité | Quantità | cantidad |
| product sales | Umsätze | ventes de produits | Vendite | ventas de productos |
| product sales tax | Produktumsatzsteuer | Taxes sur la vente des produits | imposta sulle vendite dei prodotti | impuesto de ventas de productos |
| marketplace withheld tax | Einbehaltene Steuer auf Marketplace | Taxes retenues sur le site de vente | Trattenuta IVA del marketplace | impuesto retenido en el sitio web |
| selling fees | Verkaufsgebühren | frais de vente | Commissioni di vendita | tarifas de venta |
| fba fees | Gebühren zu Versand durch Amazon | Frais Expédié par Amazon | Costi del servizio Logistica di Amazon | tarifas de Logística de Amazon |
| other transaction fees | Andere Transaktionsgebühren | autres frais de transaction | Altri costi relativi alle transazioni | tarifas de otras transacciones |
| other | Andere | autre | Altro | otro |
| total | Gesamt | total | Totale | total |

Значения колонки `type` тоже локализованы (например DE: `Bestellung` = Order, `Erstattung` = Refund, `Übertrag` = Transfer, `Servicegebühr` = Service Fee, `Anpassung` = Adjustment, `Versand durch Amazon Lagergebühr` = FBA Inventory Fee). Нераспознанные значения не отбрасывать — выносить в «Other Amazon / Adjustments» с перечнем для пользователя.

## 3. Правила парсинга

### 3.1 Метаданные из имени файла

Если в содержимом нет даты/Marketplace (Business Report, некоторые экспорты Payments) — извлекать из имени файла:
- **Marketplace:** коды и названия стран в любом регистре/языке: `UK|GB`, `DE|Germany|Deutschland`, `FR|France`, `IT|Italy|Italia`, `ES|Spain|España`, `NL|Netherlands`, `PL|Poland`, `SE|Sweden`, `BE|Belgium|Belgique`, `IE|Ireland`, `US|USA`. Кода в имени нет — спросить.
- **Период:** даты/месяцы в любом языке и транслитерации (`1 sen-19 okt`, `01.09-19.10`, `Sep 1 - Oct 19`, `last 30 days`). Год не указан — текущий/ближайший прошедший; «last 30 days» — 30 дней до даты файла или до максимальной даты в соседних отчётах. Определённый так период помечать «по имени файла».
- Валюта — из заголовка (`Total (EUR)`), из символа в значениях (`€`, `£`, `PLN`, `SEK`) или по Marketplace.

### 3.2 Payments Transactions view

- Дата `dd/mm/yyyy` (в EU/UK); валюта — из заголовка `Total (<CUR>)`.
- `Transaction status`: `Released` — средства переведены в доступный баланс (ещё не банк); `Deferred` — Pending (DD+7 и т. п.), не полученные деньги.
- `Total product charges` — товар **без** VAT, если VAT удержан Amazon (Facilitator); иначе с VAT — проверять по §3.3.
- `Other` у типа `Order Payment` — в основном shipping/gift-wrap credits, оплаченные покупателем (без VAT).
- `Amazon fees` — **агрегировано** (Referral + DST + FBA/прочее); разбивки нет → в P&L одной строкой «Amazon fees (не детализированы)», статус CALCULATED; для разбивки нужен Date Range Report.
- Типы сервисных строк — см. маппинг §4.
- Product Details обрезано — SKU/ASIN брать через `Order ID` из All Orders.

### 3.3 Определение Marketplace Facilitator VAT

Если есть All Orders и транзакции по тому же `order id`:
- `item-price − item-tax ≈ Total product charges` (допуск 0,01) **и** `shipping-price − shipping-tax ≈ Other` → VAT удержан и уплачен Amazon (Facilitator / deemed supplier): VAT исключить из выручки, продавец его не уплачивает.
- `item-price ≈ Total product charges` → VAT в составе сумм; режим уплаты продавцом — уточнить.
- Типичные случаи Facilitator: продавец вне EU/UK, продающий в EU (B2C) и в UK (заказы ≤ £135). Вывод — как наблюдение, не налоговое заключение.

### 3.4 Business Report — разная база сумм

`Ordered Product Sales` — сумма заказов покупателя **с VAT** по дате заказа; `Shipped product sales` может быть **без** удержанного Facilitator VAT (по данным пользователя: IT 63,55 vs 52,09). Не складывать и не сравнивать эти колонки между собой; для выручки использовать транзакции, Business Report — только для единиц и трендов. Business Report обновляется с задержкой (~1 день): заказ, отгруженный в последний день периода, может ещё не попасть в `Units shipped`.

### 3.5 Пустые файлы

Файл только с заголовком (0 строк) — не ошибка: «нет данных за период» (нет продаж/листингов в Marketplace). Отражать в Intake, не исключать Marketplace из списка.

### 3.6 Общие правила

- **Строка заголовка:** искать первую строку, содержащую ≥ 3 ключевых колонки сигнатуры (Date Range Report содержит 7–8 строк-дисклеймеров сверху).
- **Числа:** определить формат по образцу: если встречается `,` как последний разделитель и `.` как тысячный → европейский формат. Удалять символы валют и неразрывные пробелы. Скобки `(123)` = отрицательное.
- **Даты:** могут содержать часовой пояс в строке (`PST`, `PDT`, `UTC`, `GMT+1`). Сохранять исходный TZ; приводить к TZ Marketplace.
- **Валюта:** если колонки нет — из заголовка/символа в значении (§3.1), иначе по Marketplace (`amazon.de` → EUR, `amazon.co.uk` → GBP, `amazon.com` → USD, `amazon.pl` → PLN, `amazon.se` → SEK).
- **Знаки:** в Date Range Report расходы уже отрицательные; в Settlement — тоже со знаком. Не инвертировать повторно.
- **Строки `Transfer`/`Übertrag`** — выплата на банк, это не расход P&L: использовать только для Cash Flow.
- **Дубли файлов:** хэш содержимого; одинаковый хэш → игнорировать второй файл, сообщить в Data Quality.
- **Перекрытие периодов** двух Date Range Report → дедупликация по ключу из SKILL.md, а не отказ.

## 4. Маппинг типов транзакций → строки P&L

Классифицировать по `type` + `description` (Date Range) или `transaction-type` + `amount-type` + `amount-description` (Settlement).

| Строка P&L | Что сюда относится |
|---|---|
| Gross Sales | `product sales` по типу Order (net of VAT), shipping credits, gift wrap credits |
| Discounts & Promotions | `promotional rebates` (вкл. promo на доставку) |
| Refunds | `product sales` по типу Refund (отрицательные), shipping credit refunds |
| VAT / Facilitator (вне P&L) | `product sales tax`, `shipping credits tax`, `marketplace withheld tax` и их refunds |
| Marketplace Fees | Referral Fee (Commission), Variable Closing Fee, Digital Services Fee, Subscription Fee, Refund Administration Fee |
| Fulfillment & Logistics | FBA Per Unit Fulfillment Fee, FBA Pick & Pack, Inbound Placement Service Fee, Inbound Transportation/Partnered Carrier, Low-Inventory-Level Fee, FBA Returns Processing Fee, Cross-border/EFN Fee, MCF Fee, Shipping Label Purchase (FBM) |
| Storage | FBA Inventory Storage Fee, Aged Inventory Surcharge/Long-term Storage, Storage Utilization Surcharge, Removal/Disposal Order Fee |
| Advertising | Cost of Advertising (если реклама удерживается из settlement) |
| Promotions & Deals Fees | Coupon Redemption/Performance Fee, Lightning Deal Fee, Deal Fee, Prime Exclusive Discount Fee, Vine Enrollment Fee |
| Reimbursements (+) | FBA Inventory Reimbursement (Lost:Warehouse, Damaged:Warehouse, Customer Return, Customer Service Issue), SAFE-T reimbursement |
| Claims & Chargebacks (−) | A-to-Z Guarantee Claim, Chargeback Refund, SAFE-T debit |
| Interest / Financing | Amazon Lending repayment (тело → Cash Flow Financing; проценты → Interest) |
| Cash Flow only | Transfer/Payout, Reserve (Previous Reserve Amount Balance, Current Reserve Amount), Failed disbursement, **`Paid to Amazon \| Seller repayment` / «Successful charge»** — списание с карты/банка продавца в погашение отрицательного баланса: это денежный отток продавца, **не доход P&L** (иначе расход, который он погашает, например Subscription, обнулится) |
| Other Amazon / Adjustments | Всё прочее, включая `Adjustment` и нераспознанное — с описаниями |

**Расходы уровня аккаунта** (Subscription / Professional selling plan, прочие Service Fees без order id) относить к аккаунту, а не к Marketplace или SKU: в P&L по Marketplace и SKU Profitability не распределять по умолчанию; в консолидированном P&L — отдельной строкой. Unified-аккаунт (EU + UK) может списывать подписку в одном Marketplace (например DE) — это не расход DE. Распределение — только по явной методике пользователя.

При Refund: Referral Fee возвращается продавцу за вычетом Refund Administration Fee — учитывать обе строки как есть (нетто-эффект).

## 5. Cost Master

| Колонка | Обяз. | Описание |
|---|---|---|
| `sku` | да | SKU продавца |
| `asin` | нет | ASIN |
| `marketplace` | нет | если цена различается по маркетплейсам |
| `valid_from` | нет | дата начала действия (себестоимость во времени) |
| `currency` | да | валюта закупки |
| `purchase_cost` | да | цена закупки за единицу |
| `inbound_shipping` | нет | доставка до Amazon за единицу |
| `customs_duty` | нет | пошлины за единицу |
| `prep_labeling` | нет | подготовка/маркировка за единицу |
| `other_direct` | нет | прочие прямые затраты за единицу |
| `fbm_shipping_cost` | для FBM | фактическая стоимость доставки покупателю за заказ (перевозчик/почта), в т. ч. по Marketplace |
| `fbm_packaging` | нет | упаковка за заказ (FBM) |

Для FBM-продавцов (`fulfillment-channel = Merchant`) без `fbm_shipping_cost` Contribution Profit — UNAVAILABLE: shipping credit покупателя учитывается в выручке, а парная стоимость доставки неизвестна.

Отсутствующие необязательные компоненты помечать в выводе («Landed Cost без пошлин»), а не принимать за 0 молча. Шаблон — `assets/cost_master_template.csv`.

## 6. Где скачать недостающие отчёты (для сообщений пользователю)

| Отчёт | Путь в Seller Central |
|---|---|
| Date Range Report | Payments → Reports Repository → Transaction (Date Range) → Generate Report |
| Settlement (Flat File V2) | Payments → All Statements → Download Flat File V2 |
| All Orders | Reports → Fulfillment → All Orders (или Order Reports) |
| Business Report | Reports → Business Reports → Detail Page Sales and Traffic by Child Item |
| Manage FBA Inventory | Reports → Fulfillment → Inventory → Manage FBA Inventory |
| Inventory Ledger | Reports → Fulfillment → Inventory → Inventory Ledger |
| FBA Customer Returns | Reports → Fulfillment → Customer Concessions → FBA Customer Returns |
| Reimbursements | Reports → Fulfillment → Payments → Reimbursements |
| Storage Fees | Reports → Fulfillment → Payments → Monthly Storage Fees / Aged Inventory Surcharge |
| Fee Preview | Reports → Fulfillment → Payments → Fee Preview |
| Advertising | Advertising → Measurement & Reporting → Sponsored ads reports |

Названия меню Amazon меняются — формулировать как «обычно находится в …».
