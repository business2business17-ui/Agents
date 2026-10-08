# Agents

Скиллы, упакованные как автономные агенты: подключаются плагином в Claude Code или загружаются в любой другой ИИ.

## Агенты

| Агент | Статус | Что делает |
|---|---|---|
| `amazon-creative-studio` (Design) | v2.0 готов | Карусель (MAIN + 2-7), A+, Brand Story, Store, реклама, видео, 3D: план, копирайт, локализация, ТЗ дизайнеру, промпты для ИИ-генераторов, production XLSX, preflight. Реальный товар не перерисовывается. |
| Amazon Product Intelligence (Agent 1) | в очереди | из `Amazon_Agents_Universal_v3.zip` |
| Amazon Feed Compiler (Agent 2) | в очереди | из `Amazon_Agents_Universal_v3.zip` |
| Amazon Feed Error Agent | в очереди | из `Amazon_Agents_Universal_v3.zip` |

## Как работает агент (минимум ручной работы)

- **Один чекпоинт вместо пяти гейтов.** Агент сам читает XLSX/файлы, классифицирует каждую строку, предлагает копирайт и раскладку и присылает один план. Ответ: `ok` или `3: ..., 8: ...`.
- **Вопросы только по блокерам**, одним сообщением, с уже подставленным рекомендуемым ответом.
- **Режимы:** `AUTOPILOT` («делай сам»), `SMART` (по умолчанию), `GUIDED` (подтверждение каждого этапа).
- **Память проекта** `creative-studio/PROJECT.md`: бренд, рынки, решения, термины. Объяснять второй раз не нужно.
- **Скрипты, которые агент запускает сам:** `validate_asset.py` (проверка изображений/видео), `build_workbook.py` (production XLSX).
- Итог всегда со статусом `READY FOR AMAZON CREATIVE UPLOAD` / `READY AFTER USER-APPROVED CROP/EXPORT` / `NOT READY ...` и одним `NEXT:`.

## Подключение

**Claude Code (плагин):**
```
/plugin marketplace add business2business17-ui/Agents
/plugin install amazon-creative-studio@business2business17-agents
```
Появятся агент `amazon-creative-studio` и одноимённый скилл.

**Любой другой ИИ** (готовые файлы в `dist/amazon-creative-studio/`, архив `dist/amazon-creative-studio.zip`):

| Платформа | Что взять |
|---|---|
| Claude Projects, Gemini Gem, Cursor rules, Codex `AGENTS.md`, любой API (system prompt) | `system-prompt.md` (автономный, все референсы внутри) |
| ChatGPT Custom GPT (лимит Instructions 8000 симв.) | `instructions-short.md` + файлы из `knowledge/` в Knowledge |
| Среда с выполнением кода | дополнительно `knowledge/scripts/` |

Без доступа к файлам агент выводит обновлённый блок памяти проекта в конце ответа.

## Структура

```
.claude-plugin/marketplace.json      каталог плагинов
plugins/<agent>/
  .claude-plugin/plugin.json
  agents/<agent>.md                  определение агента (контракт работы)
  skills/<agent>/SKILL.md            протокол + references/ scripts/ assets/   <- источник истины
dist/<agent>/                        собирается: python3 tools/build_portable.py
tools/build_portable.py              --check для проверки актуальности dist
```

После правок в `plugins/` запускайте `python3 tools/build_portable.py`.

## Стандарт для следующих агентов

Каждый скилл доводится до одного формата: протокол автономной работы в `SKILL.md` (принципы, режимы, пайплайн, чекпоинты, жёсткие правила, итоговые статусы), знания в `references/`, детерминированные проверки в `scripts/`, память проекта, один агент-файл. Метки достоверности правил (`REQUIRED` / `RECOMMENDED` / `PRESET` / `VERIFY_IN_UI`) вместо выдуманных значений.

## Что изменено в Design v2.0 относительно Design.zip

- В `SKILL.md` добавлен протокол агента: принципы, режимы, память, чекпоинты C1/C3 (5 гейтов объединены в один пакетный чекпоинт).
- Реально созданы скрипты `validate_asset.py` и `build_workbook.py` (в исходном скилле на них были ссылки, но файлов не было).
- Добавлены референсы `qa-preflight`, `project-memory`, шаблон чекпоинта `creative-plan`; убраны заглушки `api_reference.md` и `assets/README.md`.
- Убрана пометка «Verified» в `amazon-specs.md`: значения перенесены из исходного пакета и не перепроверялись по живым страницам Amazon (нужен логин Seller Central); для критичных размеров агент обязан сверяться с актуальным источником.
