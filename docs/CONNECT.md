# Подключение агента Design (amazon-creative-studio)

Файлы: `dist/amazon-creative-studio/` или архив `dist/amazon-creative-studio.zip`.

## Claude Code
После слияния ветки в `main`:
```
/plugin marketplace add business2business17-ui/Agents
/plugin install amazon-creative-studio@business2business17-agents
```
Без слияния: `git clone -b AMZ-DESIGN https://github.com/business2business17-ui/Agents.git`, затем `/plugin marketplace add ./Agents`.
Работайте в папке проекта (там появится `creative-studio/`). Для скриптов: `pip install Pillow openpyxl`, для видео нужен `ffmpeg`.

## Claude.ai
Projects -> Create project -> Instructions: весь `system-prompt.md`. Файлы (XLSX, фото) прикладывайте в чат проекта. Скрипты запускаются, если включено выполнение кода; иначе агент проверяет вручную.

## ChatGPT (Custom GPT)
Create GPT -> Instructions: `instructions-short.md` (лимит 8000 символов) -> Knowledge: все файлы из `knowledge/references/`, `knowledge/scripts/*.py`, `knowledge/assets/*` -> включить Code Interpreter -> Save (Only me).

## Gemini
Gem manager -> New Gem -> Instructions: `system-prompt.md` (если не помещается: `instructions-short.md` + файлы `references/*.md` как знания). Скрипты в Gemini запускаются не везде, проверки тогда делаются вручную.

## Codex
`system-prompt.md` положить в корень рабочего репозитория как `AGENTS.md`, рядом скопировать папку `knowledge/`.

## Проверка
«Сделай план карусели для товара: шампунь Brand X 250 мл, рынок DE» + фото. Правильная реакция: один сводный план с допущениями и просьбой `ok`, а не десяток вопросов.

## Остальные агенты (SEO-Listings, PPC, Feeds)

Файлы: `dist/amazon-seo-listings/`, `dist/amazon-ppc/`, `dist/amazon-feeds/` и одноимённые `.zip`. Подключение к Claude.ai, ChatGPT, Gemini и Codex такое же, как выше (`system-prompt.md` или `instructions-short.md` + `knowledge/`).

- **Feeds** — один агент с двумя режимами. В `knowledge/` файлы лежат по скиллам: `knowledge/amazon-feed-compiler/...` (FILL) и `knowledge/amazon-feed-error-agent/...` (ERRORS). `instructions-short.md` содержит роутер режима; протоколы `amazon-feed-compiler/SKILL.md` и `amazon-feed-error-agent/SKILL.md` загрузите как знания и откройте нужный в начале задачи.
- **PPC** — в `dist/` только основной протокол и его references / scripts (`ppc_search_terms.py`, `performance_calc.py`). 24 дополнительных скилла (zerlinpi, nospicyplease, nexscope, Marketplace Ad Pros) работают в Claude Code как плагин и в `dist/` не включаются.
