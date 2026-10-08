# Amazon-агенты (Product Intelligence, Feed Compiler, Feed Error Agent)

Три агента из `Amazon_Agents_Universal_v3.zip`. Дизайн (верстка, ТЗ, визуальный контент) - отдельный агент `amazon-creative-studio`, живёт в своей ветке/PR и с этими агентами не пересекается.

| Агент | Плагин | Задача |
|---|---|---|
| Agent 1 | `amazon-product-intelligence` | Сбор ТТХ, сопоставления, тексты и SEO, claims, цены, запечатанный пакет для Feed. |
| Agent 2 | `amazon-feed-compiler` | Заполнение Feed Amazon: инспекция шаблона, маппинг, dry run, запись только в Template с 7-й строки, аудит, манифест. |
| Error Agent | `amazon-feed-error-agent` | Исправление ошибок уже загруженного Feed: Processing Report, причины, Change Plan, правки только после подтверждения, QA, повторный анализ. |

Цепочка: **Agent 1 -> Agent 2 -> загрузка в Amazon -> Error Agent -> исправленный feed -> загрузка -> Error Agent ...** Все три делят папку `amazon-project/` и файл памяти `PROJECT.md`.

## Как работают
- Один чекпоинт на пакет вместо россыпи вопросов; вопросы только по блокерам, сгруппированно, с рекомендуемым ответом. Режимы `AUTOPILOT` / `SMART` / `GUIDED` (у Agent 2 ещё `SIMULATION_MODE`).
- Скрипты запускает сам агент: цены (точный Decimal, политика v3), маржа и лесенка скидок (`margin_calc.py`), GMV / ACOS / TACOS / ROAS (`performance_calc.py`), GTIN, проверка контента, запечатанный handoff, безопасная запись в xlsm, guard "изменились только утверждённые ячейки", разбор Processing Report.
- SEO: источник - выгрузки Cerebro/Magnet (CSV/XLSX) или Helium 10 MCP (`get_keywords_by_asin` = Cerebro, `get_keywords_by_keyword` = Magnet и др., карта инструментов в `references/12-seo-sources-cerebro-helium10-mcp.md`). `seo_import.py` нормализует данные, делает отчёт очистки, тиры 1-4, ловит выгрузку не того маркетплейса и устаревшие данные. SEO - только спрос, не доказательство свойств товара.
- Решения пользователя (ступени 2-4-6 / 2-4 спрашиваются каждый раз, B2B min = цена самой глубокой ступени, B2B max привязан к Sale Price, база продаж с НДС/без) помечены `USER_DECISION` и не выдаются за правило политики.
- Честные статусы: `READY_FOR_AMAZON_UPLOAD` только после полного аудита, иначе `NOT_READY` с точными строками и ячейками.

## Подключение

**Claude Code** (после слияния ветки в `main`):
```
/plugin marketplace add business2business17-ui/Agents
/plugin install amazon-product-intelligence@business2business17-agents
/plugin install amazon-feed-compiler@business2business17-agents
/plugin install amazon-feed-error-agent@business2business17-agents
```
До слияния: `git clone -b claude/amazon-agents <репозиторий>` и `/plugin marketplace add ./Agents`. Нужны `pip install openpyxl lxml`.

**Другие ИИ:** файлы в `dist/<агент>/` (`system-prompt.md` либо `instructions-short.md` + `knowledge/`) и `dist/<агент>.zip`.
- Claude.ai: Project -> Instructions = `system-prompt.md`.
- ChatGPT: Custom GPT -> Instructions = `instructions-short.md` (<= 8000 символов), Knowledge = `knowledge/*`, включить Code Interpreter.
- Gemini: Gem -> Instructions = `system-prompt.md` (или short + файлы знаний). Скрипты там запускаются не везде.
- Codex: `system-prompt.md` -> `AGENTS.md` в корне рабочей папки, рядом `knowledge/`.
Каждый агент подключается отдельным проектом / GPT / Gem.

## Структура и сборка
```
plugins/<agent>/{.claude-plugin/plugin.json, agents/<agent>.md, skills/<agent>/{SKILL.md,references,scripts,assets}}
shared/amazon/          общий код и политика (источник истины)
tools/sync_shared.py    shared/ -> плагины (--check)
tools/build_portable.py сборка dist/ (--check)
tests/test_amazon_tools.py
```
После правок: `python3 tools/sync_shared.py && python3 tools/build_portable.py && python3 -m unittest discover -s tests`.

## Что не проверялось
Реальные шаблоны и Processing Report Amazon; лимиты контента (заголовок 75 символов, backend 249 байт) и комиссии взяты из исходных файлов и ваших данных, живые страницы Amazon не сверялись. Первый реальный feed лучше прогнать через `SIMULATION_MODE` у Agent 2.
