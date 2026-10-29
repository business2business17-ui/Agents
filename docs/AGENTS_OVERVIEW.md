# Кто за что отвечает: 5 агентов

| # | Агент (плагин) | Ветка | Задача | Вход | Результат |
|---|---|---|---|---|---|
| 1 | **amazon-creative-studio** (Design) | `AMZ-DESIGN` | Дизайн и всё, что с ним связано: вёрстка, ТЗ дизайнеру, визуальный контент | Данные о товаре, картинки (свои, референсы, скриншоты), ссылки Google/Amazon | Production XLSX, ТЗ дизайнеру, промпты для генераторов, проверка изображений, ZIP для загрузки |
| 2 | **amazon-seo-listings** (SEO, Listings) | `SEO-Listings` | ТТХ, сопоставление, тексты листингов, SEO, claims, цены и маржа; готовит пакет для Feeds | XLSX/CSV/Google Sheet с товарами, GTIN, выгрузка Cerebro/Magnet (XLSX) или Helium 10 MCP, ваши цены, себестоимость, комиссии | Запечатанный пакет для Feeds (`READY…` / `NOT_READY…`), review XLSX (12 листов), расчёт маржи/цен |
| 3 | **amazon-ppc** (PPC) | `PPC` | Реклама: структура кампаний, search term отчёты, harvest и минус-слова, ставки / бюджеты / плейсменты, ACOS / TACOS / ROAS от реальной маржи, диагностика падений, недельный и post-change обзор | Search term / bulk / targeting отчёты (CSV/XLSX), себестоимость и комиссии, при подключении MCP: живой кабинет | План действий и XLSX с рекомендациями (ставки, минусы, harvest); запись в кабинет только после подтверждения строк |
| 4 | **amazon-feeds** (Feeds) | `Feeds` | Заполнение Feed, ошибки Feed, корректировки | Режим FILL: пакет от SEO-Listings + шаблон `.xlsm`. Режим ERRORS: Processing Report + Feed | FILL: заполненный `.xlsm` (только Template с 7-й строки), dry run, аудит, манифест. ERRORS: Change Plan, правки после вашего «ok», QA, сравнение отчётов до/после |
| 5 | **amazon-finance** (Finance) | `Finance` | Финансовая и продажная аналитика Amazon: P&L, Cash Flow / Settlement & Payout, SKU profitability, реклама (ACoS / TACoS), запасы, Unit Economics (break-even / target price с VAT, DST, доставкой FBM), Profit Leakage, What-if | Выгрузки Seller Central (Date Range / Transaction, Settlement, Payments, Business Report, All Orders, FBA Inventory / Ledger / Returns / Reimbursements, Storage, Ads), Cost Master (`assets/cost_master_template.csv`), банковская выписка | Отчёт в чате (5 ответов, KPI со статусами, топ-3 утечки и действия); XLSX / PDF / PPTX по запросу; только проверяемые цифры, N/A вместо выдуманных |

Раньше SEO-Listings назывался Product Intelligence («Agent 1»), а Feeds были двумя агентами: Feed Compiler («Agent 2») и Feed Error Agent («Agent 3»). В текстах протоколов эти имена ещё встречаются: Agent 1 = SEO-Listings, Agent 2 = режим FILL, Agent 3 = режим ERRORS.

## Что делает каждый подробнее

**SEO-Listings** — собирает ТТХ и приводит к фактам с единицами; сопоставляет строки и GTIN (контрольная цифра); пишет тексты (title, bullets, description, search terms) на языке страны с проверкой запрещённых слов и claims; строит SEO из Cerebro/Magnet или Helium 10 MCP (очистка, тиры 1–4, проверка страны и языка выгрузки); считает цены (Sale → Standard → Business, ступени по количеству и границы B2B — ваши решения) и маржу (referral/FBA/MFN fee). Спрашивает категорию, тип товара, страну и язык; ищет в интернете свежие требования (комплаенс, категории, ограничения).

**PPC** — считает break-even и target ACOS из реальных затрат, строит структуру кампаний (Auto → Broad → Exact, Product Targeting), разбирает search term отчёты (`ppc_search_terms.py`: сводка по кампаниям, ставки по RPC × target ACOS, минус-слова, harvest в Exact), даёт бюджеты и плейсменты, диагностику падений, недельный и post-change обзор. Не пишет в рекламный кабинет без явного подтверждения строк; бренд, свои ASIN и launch-термины не режет на тонких данных. Методики: 24 установленных скилла (zerlinpi, nospicyplease, nexscope, Marketplace Ad Pros), список в `plugins/amazon-ppc/skills/THIRD_PARTY_SKILLS.md`.

**Finance** — распознаёт отчёты по сигнатуре колонок (`report_detect.py`, EN/DE/FR/IT/ES), считает P&L до уровня, который позволяют данные (без Cost Master — до COGS; без OpEx — до Contribution Profit; без налога — до Profit Before Tax), отличает Settlement Analysis от банковского Cash Flow, считает юнит-экономику (`finance_calc.py`: Referral от товара + доставки с VAT и DST, break-even / target price и ACoS), ищет утечки (Confirmed / Potential / Optimization), строит what-if (п.п. ≠ %). У каждого показателя статус VERIFIED / CALCULATED / ESTIMATED / UNAVAILABLE, персональные данные покупателей не выводятся. Полное ТЗ: `plugins/amazon-finance/skills/amazon-finance/references/agent-spec-v1.2.md`.

**Feeds** — два режима. **FILL:** берёт только проверенный пакет; пишет в шаблон через XML-патч (макросы и другие листы не меняются), проверяет значения по настоящим выпадающим спискам шаблона; режим SIMULATION_MODE для пробного прогона; выдаёт статус и манифест файлов. **ERRORS:** разбирает Processing Report, сопоставляет ошибки с базой (`error_kb.json`), готовит Change Plan (что менять, в каких ячейках, почему), после вашего «ok» вносит правки на чистой пересборке и сравнивает отчёты. Агент сам выбирает режим по файлам и просьбе.

**Design** — план визуального контента (карусель MAIN + 2–7, A+, Brand Story, Store, реклама, видео), тексты и локализация, ТЗ дизайнеру, промпты для ИИ-генераторов, проверка файлов (размеры, MAIN на белом фоне, вес). **Читает картинки**: свои фото товара, референсы конкурентов (только как ориентир, без копирования), мудборды, скриншоты. Реальный товар не перерисовывается (Product Fidelity Lock).

## Что общее у всех агентов

- **Один чекпоинт вместо россыпи вопросов**: ответ `ok` или правки по номерам. Вопросы только по блокерам, одним сообщением, с готовым рекомендованным ответом.
- **Режимы:** `AUTOPILOT` («делай сам»), `SMART` (по умолчанию), `GUIDED` (подтверждение каждого этапа).
- **Память проекта** (`amazon-project/PROJECT.md`, `creative-studio/PROJECT.md`): категория, тип товара, страна, язык, решения, заметки исследований — ничего не объясняется дважды.
- **В начале каждого проекта спрашивают**: категория и тип товара (по группам, с рекомендацией), страна (любой маркетплейс Amazon) и язык листинга.
- **Свежие данные из интернета**: комплаенс, категории, ограничения, спецификации — по официальным источникам нужной страны, с датой и ссылкой (`references/live-research.md`).
- **Ссылки**: Google Doc / Sheet / Slides / Drive (только чтение) и ссылки Amazon любой страны — категория или ASIN (`google_link.py`, `amazon_link.py`). Страницы Amazon не скрейпятся: данные идут через Helium 10 MCP, официальные API или страницу, которую вы открываете сами.
- **Честные статусы** `READY…` / `NOT_READY…` с точными причинами.

## Как агенты связаны

```
SEO-Listings → (пакет) → Feeds FILL → (загрузка в Amazon) → Feeds ERRORS → исправленный feed → загрузка → ...
            ↘ (тексты, ТТХ, SEO) → Design (ТЗ, визуал)
            ↘ (листинг, ключи, маржа) → PPC (кампании, ставки)
Отчёты Seller Central → Finance (P&L, юнит-экономика, утечки) → break-even ACoS и маржа → PPC
```

Design и PPC работают самостоятельно и могут брать готовые тексты, ТТХ, SEO-ключи и маржу из пакета SEO-Listings.

## Какие агенты в каких ветках / как ставить

- Ветки по агентам: `AMZ-DESIGN`, `SEO-Listings`, `PPC`, `Feeds`, `Finance`; все пять плагинов собраны в `main` (маркетплейс `.claude-plugin/marketplace.json`).
- Локально: `install.sh` / `install.ps1` (см. `docs/LOCAL_INSTALL.md`). В другие ИИ: `dist/<агент>/` (`system-prompt.md`, `instructions-short.md`, `knowledge/`).
