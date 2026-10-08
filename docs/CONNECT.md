# Подключение агентов

В репозитории четыре агента (плагина): `amazon-creative-studio`, `amazon-product-intelligence`, `amazon-feed-compiler`, `amazon-feed-error-agent`.
Готовые файлы: `dist/<агент>/` или архив `dist/<агент>.zip`. Ниже `<агент>` - имя нужного агента; для каждого агента шаги одинаковые, создавайте отдельный проект/GPT/Gem на каждого.

## Claude Code
После слияния ветки в `main`:
```
/plugin marketplace add business2business17-ui/Agents
/plugin install <агент>@business2business17-agents
```
Без слияния: `git clone -b claude/loving-johnson-ztavub https://github.com/business2business17-ui/Agents.git`, затем `/plugin marketplace add ./Agents`.
Работайте в папке проекта (там появится `amazon-project/` или `creative-studio/`). Для скриптов: `pip install Pillow openpyxl lxml`, для видео нужен `ffmpeg`.

## Claude.ai
Projects → Create project → Instructions: весь `dist/<агент>/system-prompt.md`. Файлы (xlsm, XLSX, фото) прикладывайте в чат проекта. Скрипты Claude.ai запускает, если включено выполнение кода; иначе агент делает проверки вручную.

## ChatGPT (Custom GPT)
Create GPT → Instructions: `instructions-short.md` (лимит 8000 символов) → Knowledge: все файлы из `knowledge/references/`, `knowledge/scripts/*.py`, `knowledge/assets/*` → включить Code Interpreter → Save (Only me).

## Gemini
Gem manager → New Gem → Instructions: `system-prompt.md` (если не помещается: `instructions-short.md` + файлы `references/*.md` как знания). Скрипты в Gemini запускаются не везде, тогда проверки делаются вручную, а запись в xlsm лучше выполнять через Claude Code или Codex.

## Codex
`system-prompt.md` положить в корень рабочего репозитория как `AGENTS.md`, рядом скопировать папку `knowledge/` (скрипты запускаются, проверки автоматические). Если подключаете несколько агентов, держите каждого в своей папке и своём `AGENTS.md`.

## Проверка
- Design: «Сделай план карусели для товара: шампунь Brand X 250 мл, рынок DE» + фото.
- Agent 1: приложите XLSX с товарами и напишите «рынок DE, цена продажи в колонке Price».
- Agent 2: приложите пустой шаблон Amazon (.xlsm) и пакет Agent 1; для первого раза скажите «режим SIMULATION».
- Error Agent: приложите загруженный в Amazon .xlsm с Processing Report.
Правильная реакция: один сводный план/чекпоинт с допущениями и просьбой `ok`, а не десяток вопросов.
