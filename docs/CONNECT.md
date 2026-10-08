# Подключение агента amazon-creative-studio

Файлы лежат в `dist/`: архив `amazon-creative-studio.zip` или отдельные файлы в `dist/amazon-creative-studio/`.

## Claude Code
После слияния ветки в `main`:
```
/plugin marketplace add business2business17-ui/Agents
/plugin install amazon-creative-studio@business2business17-agents
```

## Claude.ai
Projects → Create project → в Instructions вставить весь `system-prompt.md`. XLSX и фото прикладывать в чат проекта.

## ChatGPT (Custom GPT)
Create GPT → Instructions: `instructions-short.md` (лимит 8000 символов) → Knowledge: все файлы из `knowledge/references/`, `knowledge/scripts/*.py`, `knowledge/assets/*` → включить Code Interpreter → Save (Only me).

## Gemini
Gem manager → New Gem → Instructions: `system-prompt.md` (если не помещается, `instructions-short.md` + файлы `references/*.md` как знания). Скрипты в Gemini запускаются не везде, агент проверяет вручную.

## Codex
`system-prompt.md` положить в корень рабочего репозитория как `AGENTS.md`, рядом скопировать папку `knowledge/`.

## Проверка
Написать: «Сделай план карусели для товара: шампунь Brand X 250 мл, рынок DE» и приложить фото. Правильная реакция: один план с допущениями и просьба ответить `ok`, без россыпи вопросов.
