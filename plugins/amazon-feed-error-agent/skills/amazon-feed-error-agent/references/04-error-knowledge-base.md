# База знаний по ошибкам Amazon

> Source: original agent specification, sections preserved verbatim. Where this file conflicts with `SKILL.md` section "Precedence and errata", `SKILL.md` wins.

## 16. AMAZON FEED ERROR KNOWLEDGE BASE

## Важное правило

Этот раздел является методичкой, а не заменой анализа конкретного Error Message.

Один и тот же error code может иметь несколько подтипов.

Всегда учитывай:

`Error Code + Error Message + Attribute + Marketplace + Template Version`

## 5461 — New ASIN creation restricted for brand

**Тип:** BRAND_APPROVAL / BLOCKING

**Причина:**
Продавец не авторизован создавать новый ASIN для указанного бренда.

**Диагностика:**
1. Проверить, существует ли уже ASIN.
2. Проверить точное написание бренда.
3. Проверить Brand Registry / selling application.
4. Убедиться, что действительно требуется создание нового ASIN.

**Решение:**
- если ASIN уже существует — присоединить offer к существующему ASIN;
- если нужен новый ASIN — подать application;
- использовать brand name точно в подтвержденном Amazon виде.

**Автоматическое исправление:** НЕТ.

**Источник:** Amazon Listings Error Code Guide / Seller Central.

## 5665 — Brand name not approved

**Тип:** BRAND_APPROVAL / BLOCKING

**Причина:**
Amazon не разрешил использовать указанный brand name для создания listing.

**Диагностика:**
- проверить spelling;
- spaces;
- capitalization;
- brand approval;
- изображения упаковки/товара;
- соответствие бренда фактической маркировке.

**Решение:**
Запросить approval на brand name или использовать уже подтвержденное точное написание.

**Автоматическое исправление:** НЕТ.

## 8026 — Not authorized for category/product line

**Тип:** CATEGORY_APPROVAL / BLOCKING

**Причина:**
Seller не имеет разрешения листить товары в категории или product line.

**Решение:**
Запросить категорийное approval в Seller Central.

**Feed correction:** Обычно не решается простой заменой ячейки.

**Автоматическое исправление:** НЕТ.

## 8058 — Missing or invalid required field

**Тип:** MISSING_REQUIRED / INVALID_VALUE

**Причина:**
Для указанного поля отсутствует обязательное значение или передано недопустимое значение.

**Диагностика:**
1. Найти Affected Field.
2. Найти соответствующую колонку Template.
3. Проверить `Data Definitions`.
4. Проверить `Valid Values`.
5. Проверить dropdown/data validation.

**Решение:**
Заполнить обязательное поле допустимым значением из текущего Amazon template.

**Автоматическое исправление:**
Только если значение однозначно следует из шаблона и не относится к protected fields.

## 8541 — Single matching error

**Тип:** CATALOG_CONFLICT / ASIN_CONFLICT / BLOCKING

**Причина:**
GTIN/Product ID совпадает с существующим ASIN, но один или несколько переданных атрибутов конфликтуют с каталогом Amazon.

Типовые поля:

- brand
- title
- color
- size
- package quantity
- model/part number

**Диагностика:**
Сравнить:

`Merchant Value` vs `Amazon Value`

и подтвердить, что физический товар действительно соответствует найденному ASIN.

**Решение:**
- если ASIN правильный — использовать корректные catalog-compatible значения;
- если товар другой — проверить EAN/UPC/GTIN;
- если Amazon catalog неверен — не подменять правду ради прохождения feed, а инициировать catalog correction/support.

**Автоматическое исправление:** НЕТ для brand/GTIN/идентификационных конфликтов.

## 8542 — Multiple matching error

**Тип:** ASIN_CONFLICT / CATALOG_CONFLICT / BLOCKING

**Причина:**
Product ID связан с несколькими потенциальными ASIN, а переданные атрибуты не позволяют Amazon однозначно выбрать правильный.

**Решение:**
1. Проверить Product ID.
2. Проверить attributes в error message.
3. Подтвердить правильный ASIN.
4. При необходимости привести данные к корректному catalog match.
5. Если каталог Amazon неверен — эскалировать.

**Автоматическое исправление:** НЕТ без подтверждения правильного ASIN.

## 8560 — Invalid data / Missing required fields / Product ID does not match ASIN

**Тип:** MULTI-CAUSE ERROR

**Особенность:**
8560 нельзя трактовать по одному только коду.

Возможные причины:

1. invalid product ID;
2. неверная длина/формат UPC/EAN/ISBN;
3. missing required attributes;
4. неверный item/product type;
5. Product ID не соответствует существующему ASIN;
6. для создания нового ASIN не хватает обязательных полей.

**Диагностика:**
Обязательно разбирать полный Error Message.

**Решение:**
- проверить EAN/UPC/GTIN;
- проверить required attributes;
- проверить Data Definitions;
- проверить product type;
- определить: match existing ASIN или create new ASIN.

**Автоматическое исправление:** Только для однозначных непредохраняемых полей.

## 8572 — GTIN does not match product

**Тип:** INVALID_GTIN / BLOCKING

**Причина:**
UPC/EAN/ISBN/JAN не соответствует товару по данным Amazon/GS1.

**Диагностика:**
- проверить GTIN;
- проверить brand;
- проверить manufacturer;
- проверить GS1 owner;
- проверить, не используется ли чужой barcode;
- проверить правильность товара.

**Решение:**
Использовать корректный GS1 GTIN или предоставить Amazon подтверждающую документацию.

**Автоматическое исправление:** СТРОГО НЕТ.

## 8573 — Potential matching products found

**Тип:** ASIN_MATCH / BLOCKING

**Причина:**
Amazon считает, что создаваемый товар может уже существовать в каталоге.

**Решение:**
1. Найти существующий ASIN.
2. Проверить точное совпадение.
3. Если товар существует — использовать existing listing.
4. Если товара действительно нет — обратиться в Amazon согласно тексту ошибки.

**Автоматическое исправление:** НЕТ.

## 99001 — Missing columns or invalid values

**Тип:** TEMPLATE_STRUCTURE / INVALID_VALUE

**Причина:**
В input отсутствуют требуемые столбцы или значения имеют неправильный формат/тип.

**Диагностика:**
- проверить структуру файла;
- проверить обязательные columns;
- проверить Data Definitions;
- проверить форматы значений;
- проверить, что не была нарушена структура Amazon template.

**Решение:**
Восстановить требуемые колонки/значения и пересоздать submission без изменения структуры template.

## 4400 — Product requires review

**Тип:** APPROVAL / RESTRICTION

**Причина:**
Amazon требует review/approval для листинга данного товара.

**Решение:**
Подать соответствующий request/application через Seller Support/Seller Central.

**Feed-only fix:** Обычно отсутствует.

## 90202 / 6024 — Restricted item or brand

**Тип:** RESTRICTION / BLOCKING

**Причина:**
Товар или бренд ограничен для текущего seller account / marketplace.

**Решение:**
Проверить eligibility и запросить approval.

**Автоматическое исправление:** НЕТ.

## 17. Типовые ошибки без фиксированного кода

Не ограничивайся числовыми error codes.

Создавай и применяй методики также для:

## Invalid Enum

Проверить:

- Valid Values;
- dropdown;
- marketplace;
- exact spelling;
- case sensitivity.

## Missing Required Attribute

Проверить:

- Data Definitions;
- conditional requirements;
- product type;
- dependent attributes.

## Invalid Image URL

Проверить URL, доступность и требования Amazon.

## Parent/Child Variation Conflict

Проверить:

- parentage;
- parent_sku;
- relationship_type;
- variation_theme;
- consistency child values.

## Invalid Unit

Проверить value + unit как единую пару.

## Catalog Value Conflict

Не принимать Amazon value автоматически без подтверждения физического товара.

## Duplicate SKU / Identifier

Проверить, является ли это:
- повторной строкой;
- повторным offer;
- неверным GTIN;
- попыткой создания второго ASIN.
