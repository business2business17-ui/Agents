# Формат результатов

## Содержание
1. Краткий ответ в чате
2. Полный отчёт (разделы)
3. Profit Leakage Report
4. Reconciliation Exceptions
5. XLSX
6. Графики
7. PDF / PPTX

## 1. Краткий ответ в чате (по умолчанию)

Язык — язык пользователя; термины Amazon — на английском.

```
**Период:** 01.09–30.09.2026 · **Marketplace:** DE, FR · **Валюта:** EUR (FR/DE в EUR, курс не требовался)
**Источники:** Date Range Report (DE, FR), Business Report, Cost Master · **Нет:** банковской выписки, Ads-отчётов
(Если периоды источников различаются — таблица «Источник | Marketplace | Период | Как определён (содержимое / имя файла) | Строк».)

### 5 ответов
1. Продано: 1 240 ед. / 1 105 заказов — VERIFIED
2. Заработано: Contribution Profit 8 420 € (18,3%) — CALCULATED; Net Profit — N/A (нет OpEx/налога)
3. Куда ушли деньги: COGS 41%, Amazon fees 27%, Ads 9% … — CALCULATED
4. Деньги: Payout 31 200 €, в Reserve 2 100 € — Settlement Analysis (не банковский Cash Flow)
5. Действия: см. ниже

### KPI
| KPI | Значение | Δ к пред. периоду | Статус |
|---|---|---|---|

(На малой выборке — абсолютные значения, вместо % и Δ: «недостаточно данных (n = X)».)

### Топ-3 утечки
| Категория | SKU | Сумма | Статус | Уверенность |

### Топ-3 действия
1. **Факт** → **доказательство** → **причина/гипотеза** → **эффект ≈ X €/мес.** → **действие**

### Ограничения
- Нет Ads-отчёта → реклама только из Settlement, без ACoS по SKU. Нужно: Sponsored Products Advertised Product Report за тот же период.

Сформировать XLSX / PDF / PPTX?
```

## 2. Полный отчёт (разделы)

1. Executive Summary — 5 ответов, убыточные SKU (кол-во), Confirmed Loss, Potential Leakage, Δ прибыли выбранного сценария (с пометкой «Сценарий»).
2. Financial Dashboard — KPI + Δ + статус.
3. Sales Performance.
4. Profit & Loss.
5. Cash Flow (или Settlement & Payout Analysis).
6. Product Profitability.
7. Advertising.
8. Inventory.
9. Unit Economics.
10. Profit Leakage Detection.
11. What-if Simulator.
12. Risks & Opportunities.
13. Action Plan.
14. Data Quality & Reconciliation.
15. Методология и допущения.

Раздел без данных: «Ограничение: … Нужно: <отчёт> (<путь в Seller Central>) — даст: …».

## 3. Profit Leakage Report

| Marketplace | SKU/ASIN или Transaction ID | Категория | Expected | Actual | Difference | Period | Evidence (файл: строки) | Confidence | Risk | Recommendation | Status |

- Status: `Confirmed Loss` / `Potential Leakage` / `Optimization Opportunity`.
- Итоги — три отдельные суммы; пересечения удалены (одна транзакция — одна находка).
- Формулировки: «проверить / запросить в Seller Support с доказательствами», не «Amazon должен».

Типовые проверки:
| Категория | Правило |
|---|---|
| FBA fee | Actual fee/ед. > Expected из Fee Preview или из истории SKU при неизменном тарифе |
| Referral | Ставка ≠ ставке категории SKU |
| Lost/Damaged | Ledger Lost/Damaged без Found/Reimbursement за 30+ дней |
| Refund без возврата | Refund есть, в Returns нет поступления после окна возврата |
| Return unsellable | Disposition `CARRIER_DAMAGED`/`WAREHOUSE_DAMAGED` без компенсации |
| Ads | Search terms/targets: клики ≥ 2 × (1 / CVR SKU) без заказа; кампании с ACoS > Break-even ACoS |
| Storage | Aged surcharge, DoS > 180, Low-Inventory-Level Fee |
| Promo | Купон/сделка: прирост Contribution < стоимость промо |
| Adjustments | Отрицательные корректировки без описания/связи с заказом |

## 4. Reconciliation Exceptions

| ID | Проверка | Источник A | Источник B | Сумма A | Сумма B | Разница | Период | Причина / гипотеза | Статус (Open / Explained / Resolved) |

## 5. XLSX

Листы: `Executive Dashboard`, `Sales Data`, `P&L`, `Cash Flow`, `SKU Profitability`, `Advertising`, `Inventory`, `Unit Economics`, `Profit Leakage`, `What-if Simulator`, `Charts`, `Data Quality`, `Methodology`, `Transactions` (нормализованные, без PII), `History` (для накопления при следующем запуске).

- Производные показатели — формулами Excel со ссылками на `Transactions`/входные ячейки, не вставленными значениями.
- `What-if Simulator`: входные ячейки (цена %, ACoS п.п., рост %, закупка %, эластичность) выделены цветом, с валидацией данных; результаты — формулами.
- Автофильтр и закреплённая строка заголовка на табличных листах; форматы валют и %.
- Колонка `Status` (VERIFIED/CALCULATED/ESTIMATED/UNAVAILABLE) у KPI.
- Колонки `source_file`, `source_row` в `Transactions`.

## 6. Графики

Только факт или явно помеченный сценарий. У каждого: название, период, валюта, подписи осей, легенда, единицы.

Цвета: синий — продажи/выручка; зелёный — благоприятные изменения/прибыль; красный — потери/отрицательные; оранжевый — риски; серый — нейтральные. Сценарий/прогноз — пунктир или штриховка с подписью.

Набор: Revenue & Net/Contribution Profit Trend; P&L Waterfall (Gross Sales → Contribution/Net); Amazon Fee Breakdown; Cash Flow / Cash Balance; Top/Bottom 10 SKU by Profit; Margin by SKU; ACoS vs Break-even ACoS by SKU; Returns by reason; Inventory DoS distribution; What-if Current vs Scenario; Profit Sensitivity by Price.

## 7. PDF / PPTX

- PDF — управленческий отчёт: разделы §2 с графиками и выводами; методология в конце.
- PPTX — 8–12 слайдов: заголовок, 5 ответов, KPI, P&L waterfall, Cash, SKU top/bottom, реклама, утечки, сценарий, Action Plan, ограничения данных.
- Создавать только по запросу; использовать доступные скиллы `pdf` / `pptx`.
