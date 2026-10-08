# Agents

Скиллы, упакованные как автономные агенты: подключаются плагином в Claude Code или загружаются в любой другой ИИ (ChatGPT, Gemini, Claude.ai, Codex, Cursor).

## Агенты

| Агент | Плагин | Что делает |
|---|---|---|
| Design | `amazon-creative-studio` | Карусель (MAIN + 2-7), A+, Brand Story, Store, реклама, видео, 3D: план, копирайт, локализация, ТЗ дизайнеру, промпты для ИИ-генераторов, production XLSX, preflight. Реальный товар не перерисовывается. Вход для Claude Code локально: папка с картинками, названными по GTIN/EAN/UPC, + XLSX (строка = товар: ТТХ и, если есть, преимущества; если нет, агент составляет их из ТТХ и согласует в чекпоинте) — `scripts/match_inputs.py` сопоставляет файлы со строками. |
| Agent 1 | `amazon-product-intelligence` | TTX/каталог/фото/SEO → проверенный пакет товара: GTIN, evidence matrix, claims, product type, SEO-контент (title, bullets, description, backend), цены Sale→Standard→Business, версии/хэши, запечатанный handoff для Agent 2. |
| Agent 2 | `amazon-feed-compiler` | Пустой шаблон Amazon + пакет Agent 1 → заполненный feed: инспекция шаблона, маппинг, dry run, запись только в Template с 7-й строки, guard-проверка, манифест, разбор Processing Report. |
| Error Agent | `amazon-feed-error-agent` | Processing Report → причины ошибок → Change Plan (до/после) → правки только после подтверждения на чистой пересборке → QA и повторный анализ. |

Цепочка: **Agent 1 → Agent 2 → загрузка в Amazon → Error Agent → (исправленный feed) → загрузка → Error Agent …**. Все три Amazon-агента делят папку `amazon-project/` и файл памяти `PROJECT.md`, поэтому одно и то же объяснять дважды не нужно.

## Как работают агенты (минимум ручной работы)

- **Один чекпоинт вместо россыпи гейтов.** Агент сам читает файлы, классифицирует, считает и присылает один план. Ответ: `ok` или правки по номерам.
- **Вопросы только по блокерам**, одним сообщением, с уже подставленным рекомендуемым ответом, сгруппированно (не «по каждому SKU»).
- **Режимы:** `AUTOPILOT` («делай сам»), `SMART` (по умолчанию), `GUIDED` (каждый этап), у Agent 2 ещё `SIMULATION_MODE`.
- **Память проекта** (`PROJECT.md`): бренд/рынки/шаблоны/решения/правила пользователя.
- **Скрипты запускает сам агент**, а не вы: цены (точный Decimal), GTIN, проверка контента, инспекция и безопасная запись xlsm, доказательство «изменились только разрешённые ячейки», манифест, сравнение отчётов Amazon, валидация изображений/видео.
- **Честные статусы:** `READY…` только после прохождения проверок, иначе `NOT READY…` с точными строками/ячейками.

## Подключение

Подробно по каждой платформе: [`docs/CONNECT.md`](docs/CONNECT.md).

**Claude Code:**
```
/plugin marketplace add business2business17-ui/Agents
/plugin install amazon-creative-studio@business2business17-agents
/plugin install amazon-product-intelligence@business2business17-agents
/plugin install amazon-feed-compiler@business2business17-agents
/plugin install amazon-feed-error-agent@business2business17-agents
```
Работает после слияния ветки в `main`; до этого: `git clone -b <ветка> …` и `/plugin marketplace add ./Agents`.

**Другие ИИ:** готовые файлы в `dist/<агент>/` и архивы `dist/<агент>.zip`: `system-prompt.md` (всё внутри) или `instructions-short.md` (≤ 8000 символов, для Custom GPT) + `knowledge/` (справочники, скрипты, шаблоны).

## Структура

```
.claude-plugin/marketplace.json      каталог плагинов
plugins/<agent>/
  .claude-plugin/plugin.json
  agents/<agent>.md                  определение агента (контракт работы)
  skills/<agent>/SKILL.md            протокол агента  <- источник истины
  skills/<agent>/references/ scripts/ assets/
shared/amazon/                       общий код и политика трёх Amazon-агентов (источник истины)
dist/<agent>/                        собирается: python3 tools/build_portable.py
tools/sync_shared.py                 копирует shared/ в плагины (--check для CI)
tools/build_portable.py              собирает dist/ (--check для CI)
tests/test_amazon_tools.py           регрессионные тесты скриптов
```

После правок: `python3 tools/sync_shared.py && python3 tools/build_portable.py && python3 -m unittest discover -s tests`.

## Стандарт агента

`SKILL.md`: принципы → режимы → память → пайплайн с чекпоинтами → жёсткие правила + «Precedence and errata» → скрипты → карта референсов. Длинные оригинальные спецификации разложены по `references/` без потери разделов; найденные противоречия разрешены явно в errata (например: «строку 7 проверять и не сдвигать молча», «отсутствие ставки B2B — не блокер», «Humanizer = гигиена текста, не обход защиты Amazon»).

## Ограничения и что не проверялось

- Размеры/лимиты Amazon (Design) и лимиты контента (заголовок 75 символов, backend 249 байт и т.д.) перенесены из исходных пакетов, живые страницы Amazon не сверялись (нужен логин Seller Central); продакшн-критичные значения агент обязан проверять по актуальному источнику.
- Скрипты проверены на синтетических файлах (unit-тесты в `tests/`), а не на реальных шаблонах Amazon. Первый реальный feed лучше прогнать через `SIMULATION_MODE` у Agent 2.
- Разбор Processing Report опирается на типовую структуру (таблица «Errors and Warnings per Error Code» + цвета ячеек Template); нестандартные макеты агент помечает `SUMMARY_ONLY` / `UNMAPPED` и просит сопоставить вручную.
