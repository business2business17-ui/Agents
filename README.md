# Agents

Четыре автономных агента для работы с Amazon. Подключаются плагинами в Claude Code (локально в терминале) или загружаются в ChatGPT, Gemini, Claude.ai, Codex, Cursor.

| Агент | Что делает |
|---|---|
| `amazon-product-intelligence` | ТТХ, сопоставление, тексты, SEO (Cerebro / Helium 10 MCP), цены и маржа, пакет для Feed |
| `amazon-feed-compiler` | Заполняет Feed Amazon |
| `amazon-feed-error-agent` | Исправляет ошибки загруженного Feed |
| `amazon-creative-studio` (Design) | Вёрстка дизайна, ТЗ, визуальный контент, чтение картинок |

Подробно кто за что отвечает: [`docs/AGENTS_OVERVIEW.md`](docs/AGENTS_OVERVIEW.md). Amazon-агенты: [`docs/AMAZON_AGENTS.md`](docs/AMAZON_AGENTS.md). Локальная установка в терминал: [`docs/LOCAL_INSTALL.md`](docs/LOCAL_INSTALL.md) (`install.sh` / `install.ps1`).

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
/plugin install amazon-product-intelligence@business2business17-agents
/plugin install amazon-feed-compiler@business2business17-agents
/plugin install amazon-feed-error-agent@business2business17-agents
```
**Другие ИИ:** `dist/<агент>/` и `dist/<агент>.zip`: `system-prompt.md` (всё внутри) или `instructions-short.md` (<= 8000 символов, для Custom GPT) + `knowledge/`.

## Структура

```
.claude-plugin/marketplace.json
plugins/amazon-creative-studio/{.claude-plugin/plugin.json, agents/, skills/amazon-creative-studio/{SKILL.md, references/, scripts/, assets/}}
dist/amazon-creative-studio/       собирается: python3 tools/build_portable.py (--check для CI)
tests/test_design_tools.py
```

После правок: `python3 tools/sync_shared.py && python3 tools/build_portable.py && python3 -m unittest discover -s tests` (то же самое проверяет CI: `.github/workflows/ci.yml`).

Запись фида одной командой: `shared/amazon/feed_pipeline.py` (dry run → патч → write guard → вердикт `PASS_TO_FULL_AUDIT` / `NOT_READY`; при провале файл не создаётся).

## Ограничения

Размеры и лимиты Amazon (`references/amazon-specs.md`) перенесены из исходного пакета и не сверялись с живыми страницами Amazon (нужен логин Seller Central); продакшн-критичные значения агент обязан проверять по актуальному источнику.
