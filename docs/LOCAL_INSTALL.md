# Установка агентов на локальный ПК (работа из терминала)

## Что нужно
- **Python 3.9+** (проверка: `python3 --version`; Windows: `py -3 --version`).
- **Claude Code CLI** для плагинов (`claude --version`). Без него агентов можно использовать в других ИИ через файлы из `dist/`.
- Необязательно: **ffmpeg** (команда `ffprobe`) только для проверки видео.

## Установка (3 шага)

1. Скачайте папку с агентами: архив `amazon-agents-local.zip` (распакуйте) или `git clone <репозиторий>` нужной ветки.
2. Откройте терминал в этой папке и запустите установщик:

   macOS / Linux / WSL / Git Bash:
   ```
   ./install.sh --test
   ```
   Windows PowerShell:
   ```
   .\install.ps1 -Test
   ```
   Если PowerShell блокирует скрипты: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

   Установщик ставит Python-пакеты (`openpyxl`, `lxml`, `Pillow`), регистрирует каталог агентов в Claude Code, ставит все плагины каталога и запускает самопроверку. Его можно запускать повторно. Параметры: `--venv` / `-Venv` (отдельное виртуальное окружение; тогда перед `claude` выполните `source .venv/bin/activate`), `--no-claude` / `-NoClaude` (только Python-пакеты).

3. Создайте рабочую папку проекта и запустите Claude Code в ней:
   ```
   python3 tools/init_project.py ~/amazon-projects/my-brand
   cd ~/amazon-projects/my-brand
   claude
   ```
   Положите исходные файлы (XLSX с ТТХ, выгрузку Cerebro, шаблон Feed `.xlsm`, фото) в папку `inbox/` и опишите задачу обычными словами. Список агентов: `/agents`.

## Агенты и как их вызывать

| Агент | Что сказать |
|---|---|
| `amazon-product-intelligence` | «Подготовь данные для Feed по файлу inbox/products.xlsx, рынок DE, SEO из inbox/cerebro.xlsx» |
| `amazon-feed-compiler` | «Заполни Feed по пакету Agent 1, шаблон inbox/DE_template.xlsm» (в первый раз добавьте «режим SIMULATION») |
| `amazon-feed-error-agent` | «Разбери ошибки загруженного Feed inbox/feed_uploaded.xlsm» |
| `amazon-creative-studio` (Design) | «Сделай план карусели и ТЗ дизайнеру по товарам из inbox/products.xlsx, картинки в inbox/images/» |

Чтобы агент работал без лишних остановок, добавьте «делай сам» (режим AUTOPILOT).

## Использование скриптов вручную

Скрипты лежат в `plugins/<агент>/skills/<агент>/scripts/` (у каждого есть `--help`). Примеры:
```
python3 plugins/amazon-product-intelligence/skills/amazon-product-intelligence/scripts/pricing_engine.py --sale 24.99 --marketplace DE
python3 plugins/amazon-product-intelligence/skills/amazon-product-intelligence/scripts/amazon_link.py parse "https://www.amazon.de/dp/B0XXXXXXXX"
python3 plugins/amazon-product-intelligence/skills/amazon-product-intelligence/scripts/google_link.py fetch "<ссылка Google Sheet>" --out inbox
```

## Токены и доступ
- **Google (приватные файлы):** токен только в переменной окружения `GOOGLE_ACCESS_TOKEN` на время сессии (macOS/Linux: `export GOOGLE_ACCESS_TOKEN=...`, PowerShell: `$env:GOOGLE_ACCESS_TOKEN="..."`). В файлы он не пишется. Публичные ссылки «у кого есть ссылка» работают без токена.
- **Helium 10 MCP:** подключается в Claude Code как MCP-сервер по инструкции Helium 10; агенты сами вызывают инструменты и берут данные оттуда. Скрипты Amazon-страницы не скачивают.

## Другие ИИ (ChatGPT, Gemini, Claude.ai, Codex)
Файлы лежат в `dist/<агент>/` (`system-prompt.md` или `instructions-short.md` + `knowledge/`); подробно в `docs/CONNECT.md`.

## Обновление и удаление
- Обновить: скачайте новую версию папки и снова запустите установщик (или `claude plugin marketplace update`).
- Удалить: `claude plugin uninstall <имя>@business2business17-agents`, затем `claude plugin marketplace remove business2business17-agents`; папку можно удалить.

## Что не проверялось
Установщик проверен на Linux. Windows PowerShell-версия написана по той же логике, но на Windows не запускалась: если она упадёт, пришлите текст ошибки.
