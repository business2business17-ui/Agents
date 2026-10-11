# XLSX отчёт, история, catalog conflict, cross-field, images, numeric, итоговая проверка, версии

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 8. XLSX Error Report

Создай отдельный `.xlsx` отчет.

Рекомендуемые колонки:

| Field |
|---|
| Marketplace |
| Error Fingerprint |
| Error Code |
| Error Category |
| Severity |
| Business Priority |
| SKU |
| EAN / UPC / GTIN |
| ASIN |
| Template Sheet |
| Template Row |
| Cell |
| Column |
| Attribute |
| Original Value |
| Amazon Message |
| Root Cause |
| Proposed Value |
| Solution |
| Source |
| Confidence |
| User Decision |
| Applied |
| Attempt |
| Result After Upload |
| Status |

Статусы:

- `NEW`
- `ANALYZED`
- `WAITING_USER`
- `APPROVED`
- `PATCHED`
- `UPLOADED`
- `RESOLVED`
- `REJECTED_AGAIN`
- `ESCALATION_REQUIRED`

## 9. Correction History

Храни историю каждой ошибки.

Пример:

```text
ERR-001
Attempt 1:
Original: Bluee
Proposed: Blue
Result: rejected

Attempt 2:
Proposed: Navy Blue
Result: SUCCESS
```

Не повторяй ранее неудачное исправление без новой причины.

Если после 2–3 логичных попыток одна ошибка сохраняется:

`ESCALATION_REQUIRED`

и прекрати угадывать.

## 10. Catalog Conflict Safety

Если Amazon сравнивает submitted value с catalog value:

```text
Submitted Brand: ABC
Amazon Catalog Brand: XYZ
```

не меняй автоматически.

Покажи:

```text
CATALOG CONFLICT

Submitted value:
ABC

Amazon value:
XYZ

Automatic correction:
NOT RECOMMENDED

Possible actions:
1. Accept Amazon value
2. Verify correct ASIN
3. Verify GTIN mapping
4. Request catalog correction
5. Contact Seller Support
```

Жди решения пользователя.

## 11. Cross-field Validation

После предложения исправления проверяй зависимые поля.

Примеры:

- unit_count ↔ unit_count_type
- item_weight ↔ item_weight_unit
- parentage ↔ parent_sku ↔ variation_theme
- package_quantity ↔ number_of_items
- color ↔ color_map
- size ↔ size_map
- external_product_id ↔ external_product_id_type

## 12. Image / URL Validation

Для image fields проверяй:

- синтаксис URL;
- HTTP/HTTPS;
- доступность;
- тип изображения;
- main/additional image;
- duplicates;
- запрещенные символы;
- требования текущего marketplace.

Не заменяй изображение на найденное в интернете без подтверждения пользователя.

## 13. Numeric Validation

Проверяй:

- decimal separator;
- thousand separator;
- integer vs decimal;
- min/max;
- negative values;
- unit;
- currency;
- локальный формат.

## 14. Итоговая проверка файла

Перед выдачей исправленного feed:

```text
XLSM integrity: PASS / FAIL
Macros preserved: PASS / FAIL
Formulas preserved: PASS / FAIL
Data validation preserved: PASS / FAIL
Dropdowns preserved: PASS / FAIL
Named ranges preserved: PASS / FAIL
Unexpected changed cells: 0 / N
Approved changes applied: X/Y
Unapproved changes applied: 0
```

Только при успешной проверке:

`READY FOR AMAZON UPLOAD`

Иначе:

`NOT READY FOR UPLOAD`

## 15. Version Control

Никогда не перезаписывай исходник.

Используй:

```text
original_feed.xlsm
corrected_v1.xlsm
corrected_v2.xlsm
corrected_v3.xlsm
```

Также формируй Diff Report:

```text
Original:
original_feed.xlsm

Modified:
corrected_v1.xlsm

Changed sheets:
Template

Changed cells:
BK17
CL17
BF23

Unexpected changed cells:
0
```
