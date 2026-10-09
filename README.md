# Agents

Агент **Design** (`amazon-creative-studio`), упакованный как автономный агент: подключается плагином в Claude Code или загружается в любой другой ИИ (ChatGPT, Gemini, Claude.ai, Codex, Cursor).

Агенты Amazon (сбор ТТХ и подготовка данных, заполнение Feed, исправление ошибок загруженного Feed) живут в отдельной ветке и PR: `claude/amz-agents-feed-products`, см. `docs/AMAZON_AGENTS.md` после слияния.

## Design

Карусель (MAIN + 2-7), A+, Brand Story, Store, реклама, видео, 3D: план, копирайт, локализация, ТЗ дизайнеру, промпты для ИИ-генераторов, production XLSX, preflight. Реальный товар не перерисовывается. Вход для Claude Code локально: папка с картинками, названными по GTIN/EAN/UPC, + XLSX (строка = товар: ТТХ и, если есть, преимущества; если нет, агент составляет их из ТТХ и согласует в чекпоинте) — `scripts/match_inputs.py` сопоставляет файлы со строками.

## Как работает агент (минимум ручной работы)

- **Один чекпоинт вместо россыпи гейтов.** Агент сам читает файлы, классифицирует, составляет план и присылает его одним сообщением. Ответ: `ok` или правки по номерам.
- **Вопросы только по блокерам**, одним сообщением, с уже подставленным рекомендуемым ответом.
- **Режимы:** `AUTOPILOT` («делай сам»), `SMART` (по умолчанию), `GUIDED` (каждый этап).
- **Память проекта** (`creative-studio/PROJECT.md`): бренд, рынки, решения, термины.
- **Скрипты запускает сам агент:** проверка изображений/видео (`validate_asset.py`), сборка production XLSX (`build_workbook.py`), сопоставление файлов с товарами по GTIN (`match_inputs.py`).
- **Честные статусы:** `READY FOR AMAZON CREATIVE UPLOAD` только после проверок, иначе `NOT READY…` с точными причинами.

## Подключение

Подробно по каждой платформе: [`docs/CONNECT.md`](docs/CONNECT.md).

**Claude Code** (после слияния в `main`):
```
/plugin marketplace add business2business17-ui/Agents
/plugin install amazon-creative-studio@business2business17-agents
```
**Другие ИИ:** `dist/amazon-creative-studio/` и `dist/amazon-creative-studio.zip`: `system-prompt.md` (всё внутри) или `instructions-short.md` (<= 8000 символов, для Custom GPT) + `knowledge/`.

## Структура

```
.claude-plugin/marketplace.json
plugins/amazon-creative-studio/{.claude-plugin/plugin.json, agents/, skills/amazon-creative-studio/{SKILL.md, references/, scripts/, assets/}}
dist/amazon-creative-studio/       собирается: python3 tools/build_portable.py (--check для CI)
tests/test_design_tools.py
```

После правок: `python3 tools/build_portable.py && python3 -m unittest discover -s tests`.

## Ограничения

Размеры и лимиты Amazon (`references/amazon-specs.md`) перенесены из исходного пакета и не сверялись с живыми страницами Amazon (нужен логин Seller Central); продакшн-критичные значения агент обязан проверять по актуальному источнику.
