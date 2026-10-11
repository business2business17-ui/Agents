# Approval gate, защищённые поля, Partial/Full Update

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 4. Approval Gate

Перед редактированием покажи пользователю:

## Summary

- Errors found
- Blocking errors
- Warnings
- Proposed changes
- HIGH confidence
- MEDIUM confidence
- LOW confidence
- Requires user input
- Protected-field changes
- Catalog conflicts

## Before / After

Для каждой предлагаемой правки:

```text
Change ID: CHG-001
SKU: ...
Cell: Template!BK17
Attribute: color_name

BEFORE:
Bluee

AFTER:
Blue

Amazon Error:
8058 / invalid value

Reason:
Value does not match a valid enum in the current template.

Source:
Valid Values + Amazon documentation

Confidence:
HIGH
```

Жди явного подтверждения.

Допустимые команды пользователя:

- `APPROVE ALL`
- `APPROVE CHG-001, CHG-004`
- `REJECT CHG-003`
- `MODIFY CHG-005 TO <value>`
- `ROLLBACK CHG-010`
- `PARTIAL UPDATE`
- `FULL UPDATE`
- `RECHECK`

Без подтверждения файл не редактировать.

## 5. Защищенные поля

Никогда не меняй автоматически без отдельного подтверждения:

- SKU
- EAN
- UPC
- GTIN
- ISBN
- ASIN
- Brand
- Manufacturer
- Product Type
- Parent SKU
- Child SKU
- Variation Theme
- Country of Origin
- Battery / dangerous goods fields
- Package Quantity
- Unit Count

Не придумывай идентификаторы.

Не заменяй EAN/UPC/GTIN на идентификатор похожего товара.

## 6. Partial Update

Если выбран `PARTIAL UPDATE`:

- исправляй только ошибочные ячейки;
- добавляй только обязательные dependent fields;
- не меняй прочие заполненные поля;
- не очищай ячейки без понимания семантики Amazon.

Различай:

- leave unchanged
- blank
- empty
- delete
- null
- not applicable

Пустая ячейка не всегда означает удаление значения.

## 7. Full Update

Если выбран `FULL UPDATE`:

1. Проверь всю строку.
2. Проверь обязательные и зависимые поля.
3. Покажи `FULL UPDATE RISK REVIEW`.
4. Предупреди, какие существующие значения могут быть перезаписаны.
5. Применяй изменения только после подтверждения.
