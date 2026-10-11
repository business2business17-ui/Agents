# Входные файлы, рабочий цикл, запрет скрытых исправлений

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 1. Входные файлы

Основной файл — Amazon Feed в формате `.xlsm`.

Типовая структура может включать:

- `Processing Summary`
- `Feed Processing Summary`
- `Template`
- `Data Definitions`
- `Valid Values`
- `Instructions`
- иные служебные листы Amazon

Названия могут отличаться в зависимости от marketplace, языка, категории и версии шаблона.

## Feed Processing Summary

Ищи таблицу, аналогичную:

- `Errors and Warnings per Error Code`
- `Error code`
- `Category of error`
- `Store`
- `Error message`
- `Affected field`
- `Impacted column`
- `Number of errors`

Название блока может отличаться в разных странах.

## Template

Это лист с данными, отправленными в Amazon.

Типовая визуальная семантика:

- зеленый / `SUCCESS` — строка или значение успешно обработано;
- желтый / `SUCCESS (OTHER ERROR)` — предупреждение или некритичная проблема;
- оранжевый — критическая ошибка;
- `Number of attributes with errors` — количество проблемных атрибутов.

**Цвет никогда не является единственным источником истины.**
Всегда сопоставляй цвет с Processing Summary, Error Message, Submission Status, Affected Field / Impacted Column и фактическими данными строки.

## 2. Обязательный рабочий цикл

Используй состояния:

`INTAKE → INSPECT → MAP ERRORS → CLASSIFY → RESEARCH → ROOT CAUSE → PROPOSE → WAIT FOR APPROVAL → PATCH → VALIDATE → DELIVER → WAIT FOR AMAZON RESULT → RE-ANALYZE`

## Этап 1 — INTAKE

1. Прими `.xlsm`.
2. Не меняй файл.
3. Определи:
   - marketplace;
   - страну;
   - язык;
   - категорию;
   - тип шаблона;
   - версию шаблона, если доступна;
   - предполагаемый тип операции.
4. Уточни у пользователя:
   - `PARTIAL UPDATE`
   - или `FULL UPDATE`,
   если режим не был явно указан.

## Этап 2 — INSPECT

Изучи:

- все листы;
- hidden sheets;
- hidden columns;
- hidden rows;
- merged cells;
- formulas;
- data validation;
- dropdown lists;
- named ranges;
- protected cells;
- macros/VBA;
- conditional formatting.

Ничего не изменяй.

## Этап 3 — MAP ERRORS

Свяжи каждую ошибку с:

- Marketplace
- Error Code
- Error Message
- Severity
- SKU
- EAN / UPC / GTIN
- ASIN, если есть
- Template row
- Template cell
- Column
- Attribute
- Original value
- Submission status

Создай уникальный `Error Fingerprint`:

`Marketplace + SKU + Error Code + Attribute + Original Value`

## Этап 4 — CLASSIFY

Присвой уровень:

- `BLOCKING`
- `ERROR`
- `WARNING`
- `INFO`

Присвой Root Cause:

- `INVALID_VALUE`
- `INVALID_ENUM`
- `MISSING_REQUIRED`
- `FORMAT_ERROR`
- `DATA_TYPE_ERROR`
- `INVALID_GTIN`
- `IMAGE_ERROR`
- `URL_ERROR`
- `CATALOG_CONFLICT`
- `ASIN_CONFLICT`
- `VARIATION_ERROR`
- `PARENT_CHILD_ERROR`
- `DEPENDENCY_ERROR`
- `UNIT_ERROR`
- `LOCALIZATION_ERROR`
- `MARKETPLACE_RESTRICTION`
- `BRAND_APPROVAL`
- `CATEGORY_APPROVAL`
- `AMAZON_INTERNAL_ERROR`
- `UNKNOWN`

## Этап 5 — RESEARCH

Используй источники в таком порядке:

1. текущий `Feed Processing Summary`;
2. `Template`;
3. `Data Definitions`;
4. `Valid Values`;
5. `Instructions`;
6. официальная документация Amazon Seller Central;
7. Amazon Seller University;
8. Amazon developer documentation;
9. официальные ответы Amazon moderators;
10. сторонние источники только как дополнительное подтверждение.

Для каждого найденного решения сохраняй:

- source title;
- source type;
- marketplace applicability;
- краткий вывод;
- confidence.

Если информация конфликтует с правилами конкретного XLSM, приоритет имеет **актуальный шаблон Amazon для данного marketplace**.

## 3. Никаких скрытых исправлений

## RULE 1 — NO SILENT CORRECTIONS

Никогда не меняй Feed до подтверждения пользователя.

Сначала сформируй Change Plan.

Минимальная таблица:

| Change ID | SKU/EAN | Sheet | Cell | Attribute | Current Value | Error | Proposed Value | Reason | Confidence | Action |
|---|---|---|---|---|---|---|---|---|---|---|

## RULE 2 — MINIMAL CHANGE

Меняй минимально необходимое количество ячеек.

Не исправляй успешно загруженные значения просто для "улучшения".

## RULE 3 — PRESERVE AMAZON TEMPLATE

Не изменяй без необходимости:

- структуру workbook;
- названия листов;
- порядок колонок;
- macros;
- VBA;
- formulas;
- data validation;
- dropdowns;
- named ranges;
- hidden state;
- formatting;
- conditional formatting;
- freeze panes;
- protection.
