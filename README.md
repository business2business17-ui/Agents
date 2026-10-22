# Agents

Четыре автономных агента (по одной ветке на агента: `AMZ-DESIGN`, `SEO-Listings`, `PPC`, `Feeds`; в `main` все четыре) для работы с Amazon. Подключаются плагинами в Claude Code (локально в терминале) или загружаются в ChatGPT, Gemini, Claude.ai, Codex, Cursor.

| Агент (плагин) | Ветка | Что делает |
|---|---|---|
| `amazon-creative-studio` (Design) | `AMZ-DESIGN` | Дизайн и всё, что с ним связано: вёрстка, ТЗ, визуальный контент, чтение картинок |
| `amazon-seo-listings` (SEO, Listings) | `SEO-Listings` | ТТХ, сопоставление, тексты листингов, SEO (Cerebro / Helium 10 MCP), цены и маржа, пакет для Feeds |
| `amazon-ppc` (PPC) | `PPC` | Реклама: кампании, search term отчёты, harvest и минус-слова, ставки / бюджеты, ACOS / TACOS / ROAS |
| `amazon-feeds` (Feeds) | `Feeds` | Заполнение Feed, ошибки Feed, корректировки (два режима одного агента) |
| `amazon-analytic` (Analytic) | `claude/upbeat-brown-mvulwz` | Market Intelligence: выгрузки Xray/Cerebro, метрики ниши, юнит-экономика, cash-flow, решение GO/TEST/HOLD, портфель SKU, отчёт HTML/PDF |

Подробно кто за что отвечает: [`docs/AGENTS_OVERVIEW.md`](docs/AGENTS_OVERVIEW.md). Amazon-агенты: [`docs/AMAZON_AGENTS.md`](docs/AMAZON_AGENTS.md). Локальная установка в терминал: [`docs/LOCAL_INSTALL.md`](docs/LOCAL_INSTALL.md) (`install.sh` / `install.ps1`).

## Правило веток

Вся работа по агенту живёт в его ветке: **всё, что связано с дизайном (карусели, A+, Brand Story, ТЗ, картинки, рендеры, production-пакеты по товарам), всегда идёт в `AMZ-DESIGN`**; SEO и листинги в `SEO-Listings`; реклама в `PPC`; Feed (заполнение, ошибки, корректировки) в `Feeds`. Ветки `claude/...` временные: после проверки их содержимое переносится в ветку агента.

## Обязательные правила заполнения Feed Amazon

Действуют для агента `amazon-feeds` (режимы FILL и ERRORS):

- **Brand** — при заполнении Feed бренд дополнительно проставляется на **все SKU**.
- **Tax code**:
  - **US** — `A_GEN_TAX`
  - **EU** — `A_GEN_Standard`

## Design

Карусель (MAIN + 2-7), A+, Brand Story, Store, реклама, видео, 3D: план, копирайт, локализация, ТЗ дизайнеру, промпты для ИИ-генераторов, production XLSX, preflight. Реальный товар не перерисовывается. Вход для Claude Code локально: папка с картинками, названными по GTIN/EAN/UPC, + XLSX (строка = товар: ТТХ и, если есть, преимущества; если нет, агент составляет их из ТТХ и согласует в чекпоинте) — `scripts/match_inputs.py` сопоставляет файлы со строками.

## Как работает агент (минимум ручной работы)

- **Один чекпоинт вместо россыпи гейтов.** Агент сам читает файлы, классифицирует, составляет план и присылает его одним сообщением. Ответ: `ok` или правки по номерам.
- **Вопросы только по блокерам**, одним сообщением, с уже подставленным рекомендуемым ответом.
- **Режимы:** `AUTOPILOT` («делай сам»), `SMART` (по умолчанию), `GUIDED` (каждый этап).
- **Память проекта** (`creative-studio/PROJECT.md`): бренд, рынки, решения, термины.
- **Читает картинки** (свои фото, референсы конкурентов, мудборды, скриншоты): `image_probe.py` + визуальный разбор, `references/image-reading.md`.
- **Спрашивает категорию, тип товара, страну и язык**; свежие требования ищет в интернете (`references/live-research.md`).
- **Скрипты запускает сам агент:** проверка изображений/видео (`validate_asset.py`), сборка production XLSX (`build_workbook.py`), сопоставление файлов с товарами по GTIN (`match_inputs.py`).
- **Честные статусы:** `READY FOR AMAZON CREATIVE UPLOAD` только после проверок, иначе `NOT READY…` с точными причинами.

## Подключение

Подробно по каждой платформе: [`docs/CONNECT.md`](docs/CONNECT.md).

**Claude Code** (после слияния в `main`):
```
/plugin marketplace add business2business17-ui/Agents
/plugin install amazon-creative-studio@business2business17-agents
/plugin install amazon-seo-listings@business2business17-agents
/plugin install amazon-ppc@business2business17-agents
/plugin install amazon-feeds@business2business17-agents
/plugin install amazon-analytic@business2business17-agents
```
**Другие ИИ:** `dist/<агент>/` и `dist/<агент>.zip`: `system-prompt.md` (всё внутри) или `instructions-short.md` (<= 8000 символов, для Custom GPT) + `knowledge/`.

## Структура

```
.claude-plugin/marketplace.json
plugins/amazon-creative-studio/   Design            (ветка AMZ-DESIGN)
plugins/amazon-seo-listings/      SEO, Listings     (ветка SEO-Listings)
plugins/amazon-ppc/               PPC               (ветка PPC)
plugins/amazon-feeds/             Feeds: скиллы amazon-feeds (роутер), amazon-feed-compiler (FILL), amazon-feed-error-agent (ERRORS)  (ветка Feeds)
   у каждого: {.claude-plugin/plugin.json, agents/, skills/<агент>/{SKILL.md, references/, scripts/, assets/}, licenses/}
shared/amazon/                    общий код; tools/sync_shared.py раскладывает по плагинам
dist/<агент>/                     собирается: python3 tools/build_portable.py (--check для CI)
tests/
```

После правок: `python3 tools/sync_shared.py && python3 tools/build_portable.py && python3 -m unittest discover -s tests` (то же самое проверяет CI: `.github/workflows/ci.yml`).

Запись фида одной командой: `shared/amazon/feed_pipeline.py` (dry run → патч → write guard → вердикт `PASS_TO_FULL_AUDIT` / `NOT_READY`; при провале файл не создаётся).

## Ограничения

Размеры и лимиты Amazon (`references/amazon-specs.md`) перенесены из исходного пакета и не сверялись с живыми страницами Amazon (нужен логин Seller Central); продакшн-критичные значения агент обязан проверять по актуальному источнику.
