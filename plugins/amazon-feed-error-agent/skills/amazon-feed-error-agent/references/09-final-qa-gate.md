# Final QA gate, definition of READY

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 42. Final QA Gate — обязательная проверка перед выдачей файла

После формирования конечного `.xlsm` агент обязан провести **полную финальную проверку**.

Файл нельзя выдавать пользователю как готовый сразу после внесения изменений.

Перед статусом:

`READY FOR AMAZON UPLOAD`

должны быть успешно пройдены два независимых уровня проверки:

1. `TECHNICAL INTEGRITY CHECK`
2. `DATA CORRECTNESS CHECK`

## 43. Technical Integrity Check

Проверить техническую целостность workbook.

Обязательные проверки:

- файл открывается без ошибок;
- формат остается `.xlsm`;
- macros/VBA сохранены;
- workbook structure сохранена;
- количество sheets не изменилось;
- имена sheets не изменились;
- порядок sheets не изменился без необходимости;
- изменен только `Template`;
- rows `1–6` полностью идентичны Source Feed;
- изменения только в rows `7+`;
- formulas сохранены;
- data validation сохранена;
- dropdown lists сохранены;
- named ranges сохранены;
- conditional formatting сохранено;
- hidden rows/columns/sheets сохранены;
- merged cells сохранены;
- protection settings сохранены;
- column widths сохранены;
- row heights сохранены;
- cell formats сохранены;
- hyperlinks сохранены;
- image/reference URLs не повреждены;
- workbook relationships не повреждены;
- отсутствуют неожиданные изменения.

Результат:

```text
TECHNICAL INTEGRITY CHECK

Workbook opens: PASS
XLSM format preserved: PASS
Macros/VBA preserved: PASS
Sheets preserved: PASS
Only Template modified: PASS
Rows 1-6 unchanged: PASS
Formulas preserved: PASS
Data validation preserved: PASS
Named ranges preserved: PASS
Formatting preserved: PASS
Unexpected changes: 0

RESULT: PASS
```

При любом `FAIL`:

`NOT READY FOR AMAZON UPLOAD`

## 44. Data Correctness Check

После технической проверки агент обязан проверить **содержание всех измененных данных**.

Проверять каждую измененную строку и каждую измененную ячейку.

## Обязательная проверка каждой измененной ячейки

Для каждой changed cell проверить:

- соответствует ли изменение подтвержденному `Change ID`;
- совпадает ли новое значение с approved value;
- правильный ли SKU;
- правильный ли EAN/UPC/GTIN;
- правильная ли строка товара;
- правильный ли attribute;
- правильный ли datatype;
- правильный ли format;
- соответствует ли значение `Valid Values`;
- соответствует ли dropdown;
- соблюдены ли min/max ограничения;
- правильная ли единица измерения;
- корректна ли decimal notation;
- корректен ли URL;
- не потерялись ли leading zeros;
- не превратилось ли число в scientific notation;
- не произошло ли нежелательное Excel auto-conversion;
- не появилась ли дата вместо кода/номера;
- не изменился ли SKU/EAN из-за форматирования;
- не появились ли лишние пробелы;
- нет ли hidden characters;
- нет ли случайных переносов строк;
- нет ли служебного текста агента.

## 45. Identifier Integrity Check

Особенно строго проверять:

- SKU
- EAN
- UPC
- GTIN
- ASIN
- ISBN
- Parent SKU
- Child SKU

Проверить:

1. значение не изменилось без отдельного approval;
2. количество цифр сохранено;
3. leading zeros не потеряны;
4. Excel не преобразовал значение в exponent/scientific notation;
5. текстовый идентификатор не стал числом;
6. идентификатор соответствует правильному товару;
7. не произошло смещение идентификатора на соседнюю строку.

При любом сомнении:

`NOT READY FOR AMAZON UPLOAD`

## 46. Row-Level Final Validation

Для каждой измененной строки сформировать проверку:

```text
ROW VALIDATION

Row: 17
SKU: ABC-001
EAN: 4000000000001

Approved changes:
3

Applied correctly:
3

Unexpected changes:
0

Required dependencies:
PASS

Dropdown values:
PASS

Identifiers:
PASS

URLs:
PASS

Result:
PASS
```

Если строка содержит unresolved issue:

`ROW STATUS: FAIL`

и весь файл:

`NOT READY FOR AMAZON UPLOAD`

## 47. Cross-Field Final Validation

После проверки отдельных cells проверить взаимосвязанные атрибуты.

Примеры:

- `unit_count` ↔ `unit_count_type`;
- `item_weight` ↔ `item_weight_unit`;
- `package_quantity` ↔ `number_of_items`;
- `parent_sku` ↔ `parentage` ↔ `variation_theme`;
- `size_name` ↔ `size_map`;
- `color_name` ↔ `color_map`;
- `external_product_id` ↔ `external_product_id_type`;
- price ↔ currency;
- dimension value ↔ dimension unit.

Правильная отдельная ячейка не считается достаточной, если зависимые поля противоречат друг другу.

## 48. Source-to-Output Reconciliation

Сравнить:

1. Clean Source Feed;
2. Approved Change Set;
3. Final Output Feed.

Правило:

```text
FINAL OUTPUT =
CLEAN SOURCE FEED
+
APPROVED CHANGE SET
```

Все отличия Final Output от Clean Source Feed должны быть объяснены конкретным approved `Change ID`.

Если найдена хотя бы одна разница без `Change ID`:

```text
UNAUTHORIZED DIFF FOUND
NOT READY FOR AMAZON UPLOAD
```

## 49. Agent 1 Reconciliation

Если использовался файл Agent 1, дополнительно проверить:

- SKU mapping;
- EAN mapping;
- product identity;
- quantity/value mapping;
- target column;
- target row;
- units;
- titles/brands;
- URLs;
- marketplace applicability.

Не считать значение корректным только потому, что оно присутствовало в Agent 1.

Каждое значение должно быть совместимо с текущим Amazon template.

## 50. Error Resolution Validation

Если файл создается для исправления предыдущего Amazon Processing Report:

для каждой исправляемой ошибки проверить:

```text
Original Amazon Error:
...

Affected field:
...

Original value:
...

Approved fix:
...

Final Feed value:
...

Expected result:
Error condition removed
```

Если correction не соответствует root cause исходной Amazon error:

не считать изменение завершенным.

## 51. Final Diff Report

Перед выдачей создать финальный Diff Report.

Минимально показать:

```text
FINAL DIFF

Source:
clean_feed.xlsm

Output:
amazon_feed_ready_v1.xlsm

Modified sheets:
Template

Modified rows:
17, 22, 41

Modified cells:
BK17
CL22
DF41

Approved modifications:
3

Applied modifications:
3

Unauthorized modifications:
0

Rows 1-6 changes:
0

Other sheet changes:
0
```

## 52. Final QA Summary

Перед выдачей файла показать пользователю краткий итог:

```text
FINAL QA SUMMARY

Technical Integrity: PASS
Data Correctness: PASS
Identifier Integrity: PASS
Row Validation: PASS
Cross-field Validation: PASS
Source Reconciliation: PASS
Approved Changes Applied: 100%
Unauthorized Changes: 0
Rows 1-6 Modified: 0
Other Sheets Modified: 0
Unresolved Critical Errors: 0
```

Только после этого:

`READY FOR AMAZON UPLOAD`

## 53. Final Failure Loop

Если любой финальный тест дает `FAIL`:

1. поставить статус:

`NOT READY FOR AMAZON UPLOAD`

2. показать пользователю точные проблемы:

| Issue ID | Sheet | Row | Column | Cell | SKU/EAN | Current Value | Expected Value | Problem | Proposed Fix |
|---|---|---:|---|---|---|---|---|---|---|

3. не исправлять без подтверждения;
4. дождаться approval;
5. применить только approved fixes;
6. снова выполнить **весь Final QA Gate с начала**;
7. повторять цикл до полного `PASS`.

Не разрешается пропускать неуспешный тест ради выдачи файла.

## 54. Definition of READY

Файл считается действительно готовым только если одновременно выполнено:

```text
TECHNICAL INTEGRITY = PASS
DATA CORRECTNESS = PASS
IDENTIFIER INTEGRITY = PASS
ROW VALIDATION = PASS
CROSS-FIELD VALIDATION = PASS
SOURCE RECONCILIATION = PASS
UNAUTHORIZED DIFFS = 0
ROWS 1-6 CHANGES = 0
NON-TEMPLATE CHANGES = 0
UNRESOLVED BLOCKING ERRORS = 0
```

Только тогда статус:

`READY FOR AMAZON UPLOAD`

Во всех остальных случаях:

`NOT READY FOR AMAZON UPLOAD`
