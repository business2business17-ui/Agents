# Подключение агента Design (amazon-creative-studio)

Файлы: `dist/amazon-creative-studio/` или архив `dist/amazon-creative-studio.zip`.

## Claude Code
После слияния ветки в `main`:
```
/plugin marketplace add business2business17-ui/Agents
/plugin install amazon-creative-studio@business2business17-agents
```
Без слияния: `git clone -b claude/loving-johnson-ztavub https://github.com/business2business17-ui/Agents.git`, затем `/plugin marketplace add ./Agents`.
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
