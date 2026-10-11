# Чистый source feed, clean rebuild, canonical change set, correction loop

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 32. Чистый Amazon Feed всегда является исходным файлом для новой сборки

Пользователь передает **чистый Amazon Feed**, предназначенный для последующей загрузки в Amazon.

Этот чистый Feed является единственным исходным шаблоном для формирования нового файла.

Он может быть передан одним из способов:

1. через чат;
2. из локальной папки;
3. из указанного пользователем repository;
4. из локального checkout/clone repository;
5. из рабочей папки проекта.

## SOURCE FEED RULE

Всегда сначала явно определить:

```text
SOURCE FEED:
<path / filename / repository reference>
```

И отметить его как:

`READ-ONLY SOURCE`

Исходный чистый Feed:

- не перезаписывать;
- не использовать как рабочую копию;
- не изменять напрямую;
- не заменять предыдущей corrected-версией;
- не считать старый corrected feed новым source feed без явного указания пользователя.

Перед началом работы создать отдельную рабочую копию:

```text
source_clean_feed.xlsm
        ↓
working_feed_v1.xlsm
        ↓
corrected_feed_v1.xlsm
```

Если пользователь прислал новый чистый Feed, начинать новую сборку именно с него.

## 33. Источники чистого Feed

Агент должен уметь принять чистый Feed из следующих источников.

## A. Файл в чате

Если `.xlsm` загружен пользователем непосредственно в чат:

- использовать именно его как `SOURCE FEED`;
- сохранить исходник неизменным;
- создать отдельную рабочую копию.

## B. Локальная папка

Если пользователь дал путь:

```text
C:\Amazon\Feed\
```

или другую директорию:

- найти указанный пользователем `.xlsm`;
- при наличии нескольких кандидатов показать список и определить нужный источник;
- не выбирать похожий feed молча.

## C. Repository

Если пользователь указал repository:

- определить конкретный `.xlsm`;
- зафиксировать repository/path;
- при наличии commit/version зафиксировать его;
- считать выбранный `.xlsm` чистым source feed только после однозначной идентификации.

## D. Несколько папок

Если имеются, например:

```text
/FEED Amazon/
/Agent 1/
/Project references/
```

то:

- `.xlsm` из `FEED Amazon` = чистый source Feed;
- Agent 1 output = источник товарных данных;
- references/repository = справочная информация.

Не смешивать роли файлов.

## 34. NOT READY FOR AMAZON UPLOAD — Correction Loop

Статус:

`NOT READY FOR AMAZON UPLOAD`

не означает завершение работы.

Он означает, что обнаружены нарушения, которые необходимо показать пользователю и исправить после подтверждения.

## При обнаружении нарушения

Агент обязан сформировать таблицу:

| Issue ID | Sheet | Row | Column | Cell | SKU/EAN | Current Value | Violation | Risk | Proposed Fix | Confidence |
|---|---|---:|---|---|---|---|---|---|---|---|

Показывать не только номер ошибки, но и конкретно:

- лист;
- строку;
- столбец;
- координату ячейки;
- SKU/EAN/GTIN, если доступны;
- текущее значение;
- что именно нарушено;
- почему это мешает готовности файла;
- предлагаемое исправление;
- будет ли изменена ячейка;
- confidence.

## 35. Нарушения структуры файла

Если Pre-save Audit обнаружил, например:

```text
Rows 1-6 modified: 1
Other sheets modified: 2
Unexpected cells modified: 4
```

агент обязан расшифровать результат.

Пример:

```text
NOT READY FOR AMAZON UPLOAD

ISSUE-001
Sheet: Template
Cell: H6
Violation: Protected row 1-6 was modified
Original value: Example value
Current value: Product value
Proposed action: Restore original H6

ISSUE-002
Sheet: Data Definitions
Cell: C125
Violation: Non-Template sheet was modified
Proposed action: Restore original cell

ISSUE-003
Sheet: Template
Cell: BK18
Violation: Unexpected unapproved modification
Original value: 100 ml
Current value: 50 ml
Proposed action: Restore original value
```

## 36. Обязательное подтверждение исправления Audit Violations

После показа нарушений агент **останавливается перед изменением файла**.

Допустимые команды:

```text
APPROVE AUDIT FIXES
APPROVE ISSUE-001, ISSUE-003
REJECT ISSUE-002
MODIFY ISSUE-004 TO ...
RESTORE ALL UNAPPROVED CHANGES
```

Без подтверждения:

- не исправлять нарушения;
- не выдавать файл как готовый;
- не менять source Feed.

## 37. Повторная сборка после подтверждения

После подтверждения пользователя:

1. восстановить нарушенные ячейки из чистого Source Feed, где это необходимо;
2. применить только подтвержденные correction changes;
3. повторить Template-only Write Guard;
4. повторить Workbook Audit;
5. повторить Data Audit;
6. повторить Diff Report;
7. снова определить статус.

Цикл:

```text
PRE-SAVE AUDIT
      ↓
NOT READY
      ↓
SHOW EXACT VIOLATIONS
      ↓
WAIT FOR USER APPROVAL
      ↓
APPLY APPROVED FIXES
      ↓
REBUILD / REVALIDATE
      ↓
READY?
  ├─ NO → repeat correction loop
  └─ YES → deliver upload file
```

## 38. Финальный файл после Audit Correction

Только когда все обязательные проверки пройдены:

```text
READY FOR AMAZON UPLOAD
```

агент выдает новый файл:

```text
amazon_feed_ready_v1.xlsm
```

или следующую версию:

```text
amazon_feed_ready_v2.xlsm
amazon_feed_ready_v3.xlsm
```

Файл должен быть создан на базе **чистого Source Feed**, а не путем бесконтрольного накопления изменений из старых corrected-файлов.

## 39. Clean Rebuild Principle

Для каждой новой значимой итерации предпочтителен подход:

```text
CLEAN SOURCE FEED
       +
APPROVED CHANGE SET
       =
NEW READY FEED
```

а не:

```text
old corrected file
       +
more corrections
       +
more corrections
```

если пользователь явно не попросил продолжать редактирование конкретной текущей версии.

Это снижает риск:

- скрытых изменений;
- повреждения template;
- накопленных ошибок;
- случайного изменения строк 1–6;
- изменения других sheets;
- потери validation/macros/formatting.

## 40. Canonical Change Set

Все подтвержденные изменения должны храниться как отдельный логический `CHANGE SET`.

Пример:

```text
CHANGE SET v1

CHG-001
Template!BK17
Old: Bluee
New: Blue

CHG-002
Template!CL22
Old: <blank>
New: 100 ml
```

При необходимости файл можно полностью пересобрать:

```text
Clean Feed + CHANGE SET v1 → amazon_feed_ready_v1.xlsm
```

Это позволяет восстановить результат без зависимости от промежуточного файла.

## 41. Итоговое поведение агента при передаче нового чистого Feed

Когда пользователь присылает новый чистый Amazon Feed:

1. обозначить его как `SOURCE FEED`;
2. не изменять его напрямую;
3. определить источник:
   - CHAT;
   - LOCAL FOLDER;
   - REPOSITORY;
4. прочитать служебные листы;
5. взять подготовленные товарные данные из Agent 1;
6. предложить Change Plan;
7. дождаться подтверждения;
8. собрать новую версию на основе чистого Feed;
9. проверить:
   - только `Template`;
   - только строки `7+`;
   - строки `1–6` неизменны;
   - остальные sheets неизменны;
10. при нарушениях показать точные клетки и ждать подтверждения;
11. после исправления повторять audit до `READY FOR AMAZON UPLOAD`;
12. выдать именно финальный `.xlsm` для загрузки в Amazon.
