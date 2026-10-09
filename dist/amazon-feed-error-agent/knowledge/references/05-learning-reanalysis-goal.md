# Самообучение, повторный анализ, цель

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 18. Самообучаемая методичка

Если найден новый error code или новый вариант Error Message:

1. Создай временную запись:
   `UNVERIFIED_CASE`.
2. Исследуй официальные Amazon источники.
3. Сформируй root cause.
4. Предложи correction.
5. Получи подтверждение пользователя.
6. Примени correction.
7. После новой загрузки проверь результат.
8. Только если проблема действительно устранена, добавь кейс в Knowledge Base как:
   `VERIFIED_BY_SUCCESSFUL_REUPLOAD`.

Для новой записи сохраняй:

```text
Error Code
Error Message Pattern
Marketplace
Template/Product Type
Root Cause
Affected Attribute
Successful Fix
Failed Fixes
Source
Confidence
Verified Date
Verification Result
```

Не считать решение подтвержденным только потому, что оно найдено на стороннем сайте.

## 19. Повторный анализ после загрузки

После получения нового Processing Report:

Сравни предыдущий и новый результат.

Покажи:

```text
Previous errors:
24

Resolved:
19

Remaining:
3

New:
2

Warnings:
5 → 2
```

Для каждой старой ошибки:

- `RESOLVED`
- `REJECTED_AGAIN`
- `CHANGED_ERROR`
- `ESCALATION_REQUIRED`

Новые ошибки проходят полный цикл с начала.

## 20. Финальная цель

Цель агента — не просто сделать XLSM без подсветки ошибок.

Цель:

1. понять точную причину Amazon rejection;
2. предложить доказуемое исправление;
3. наглядно показать пользователю BEFORE/AFTER;
4. получить подтверждение;
5. изменить только согласованные значения;
6. сохранить структуру Amazon XLSM;
7. создать audit trail;
8. проверить результат после повторной загрузки;
9. накапливать подтвержденную методичку решений.
